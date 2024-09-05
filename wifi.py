import dbus
import time
import re
import pandas as pd
import uuid
import requests
import ipaddress
import json
import os

def get_network_manager():
    bus = dbus.SystemBus()
    proxy = bus.get_object("org.freedesktop.NetworkManager",
                           "/org/freedesktop/NetworkManager")
    return dbus.Interface(proxy, "org.freedesktop.NetworkManager")

def get_active_wifi_device():
    nm = get_network_manager()
    devices = nm.GetDevices()
    for device in devices:
        dev_proxy = dbus.SystemBus().get_object(
            "org.freedesktop.NetworkManager", device)
        dev_properties = dbus.Interface(
            dev_proxy, "org.freedesktop.DBus.Properties")
        device_type = dev_properties.Get(
            "org.freedesktop.NetworkManager.Device", "DeviceType")
        if device_type == 2:  # 2 indicates a Wi-Fi device
            return device, dev_proxy, dev_properties
    return None, None, None


def scan_wifi_networks(device_proxy):
    wireless_interface = dbus.Interface(
        device_proxy, "org.freedesktop.NetworkManager.Device.Wireless")
    wireless_interface.RequestScan({})

    print("Scanning Wi-Fi networks...")
    time.sleep(5)  # Wait for the scan to complete

    aps = wireless_interface.GetAccessPoints()

    wifi_list = pd.DataFrame(
        columns=["BSSID", "SSID", "Strength", "Frequency", "MaxBitrate", "SecurityFlags"])
    wifi_list.set_index("BSSID", inplace=True)
    for ap in aps:
        ap_proxy = dbus.SystemBus().get_object("org.freedesktop.NetworkManager", ap)
        ap_properties = dbus.Interface(
            ap_proxy, "org.freedesktop.DBus.Properties")

        ssid = ap_properties.Get(
            "org.freedesktop.NetworkManager.AccessPoint", "Ssid")
        ssid_str = "".join(chr(x) for x in ssid)

        bssid = ap_properties.Get(
            "org.freedesktop.NetworkManager.AccessPoint", "HwAddress")
        strength = ap_properties.Get(
            "org.freedesktop.NetworkManager.AccessPoint", "Strength")
        frequency = ap_properties.Get(
            "org.freedesktop.NetworkManager.AccessPoint", "Frequency")
        max_bitrate = ap_properties.Get(
            "org.freedesktop.NetworkManager.AccessPoint", "MaxBitrate")
        security_flags = ap_properties.Get(
            "org.freedesktop.NetworkManager.AccessPoint", "Flags")

        wifi_list.loc[bssid] = [ssid_str, strength,
                                frequency, max_bitrate, security_flags]
        wifi_list = wifi_list.sort_values(by="Strength", ascending=False)

    return wifi_list


def getTasmotaHotspots(wifi_list):
    tasmota_list = wifi_list[wifi_list["SSID"].str.contains(
        "tasmota", flags=re.IGNORECASE)]
    return tasmota_list


def connect_to_wifi(device_proxy, wifi):
    nm = get_network_manager()

    # Create the connection settings dictionary
    connection_settings = {
        "connection": {
            "id": f"{wifi['SSID']}_connection",
            "type": "802-11-wireless",
            "uuid": str(uuid.uuid4()),
            "autoconnect": True,
        },
        "802-11-wireless": {
            "ssid": dbus.ByteArray(wifi['SSID'].encode('utf8')),
            "mode": "infrastructure",
            "security": "none",
        },
        "ipv4": {"method": "auto"},
        "ipv6": {"method": "ignore"},
    }

    # Add and activate the connection
    try:
        nm.AddAndActivateConnection(connection_settings, device_proxy, "/")
        dev_properties = dbus.Interface(
            device_proxy, "org.freedesktop.DBus.Properties")
        loop = 0
        print(f"Connecting to {wifi['SSID']}...")
        while True:
            state = dev_properties.Get(
                "org.freedesktop.NetworkManager.Device", "State")
            if state == 100:
                break
            time.sleep(1)
            loop += 1
            print(".", end="", flush=True)
            if loop > 60:
                print(f"Failed to connect!")
                return False
        print(f"Connected!")
        return True
    except dbus.DBusException as e:
        print(f"Failed to connect: {e}")
        return False


def disconnect_from_wifi(device_proxy):
    nm = get_network_manager()

    # Get the list of active connections
    active_connections = nm.GetDevices()

    for device in active_connections:
        dev_proxy = dbus.SystemBus().get_object(
            "org.freedesktop.NetworkManager", device)
        dev_properties = dbus.Interface(
            dev_proxy, "org.freedesktop.DBus.Properties")

        # Check if the device is a Wi-Fi interface
        device_type = dev_properties.Get(
            "org.freedesktop.NetworkManager.Device", "DeviceType")
        if device_type == 2:  # 2 indicates a Wi-Fi device
            device_state = dev_properties.Get(
                "org.freedesktop.NetworkManager.Device", "State")
            if device_state == 100:  # 100 indicates the device is connected
                active_connection = dev_properties.Get(
                    "org.freedesktop.NetworkManager.Device", "ActiveConnection")

                if active_connection != "/":
                    nm_proxy = dbus.SystemBus().get_object("org.freedesktop.NetworkManager",
                                                           "/org/freedesktop/NetworkManager")
                    nm_interface = dbus.Interface(
                        nm_proxy, "org.freedesktop.NetworkManager")

                    # Deactivate the active connection
                    nm_interface.DeactivateConnection(active_connection)
                    print("Disconnected from Wi-Fi.")
                    return


def get_wifi_router_ip():
    nm = get_network_manager()
    devices = nm.GetDevices()
    for device in devices:
        dev_proxy = dbus.SystemBus().get_object(
            "org.freedesktop.NetworkManager", device)
        dev_properties = dbus.Interface(
            dev_proxy, "org.freedesktop.DBus.Properties")

        # Check if the device is a Wi-Fi interface
        device_type = dev_properties.Get(
            "org.freedesktop.NetworkManager.Device", "DeviceType")
        if device_type == 2:  # 2 indicates a Wi-Fi device
            device_state = dev_properties.Get(
                "org.freedesktop.NetworkManager.Device", "State")
            if device_state == 100:  # 100 indicates the device is connected
                ip4_config_path = dev_properties.Get(
                    "org.freedesktop.NetworkManager.Device", "Ip4Config")

                if ip4_config_path != "/":
                    ip4_config_proxy = dbus.SystemBus().get_object(
                        "org.freedesktop.NetworkManager", ip4_config_path)
                    ip4_config_properties = dbus.Interface(
                        ip4_config_proxy, "org.freedesktop.DBus.Properties")

                    # Get the Gateway IP
                    gateway = ip4_config_properties.Get(
                        "org.freedesktop.NetworkManager.IP4Config", "Gateway")
                    gateway = ipaddress.IPv4Address(gateway)

                    if gateway:
                        return gateway

    return None


def get_local_wifi_ip():
    nm = get_network_manager()
    devices = nm.GetDevices()
    for device in devices:
        dev_proxy = dbus.SystemBus().get_object(
            "org.freedesktop.NetworkManager", device)
        dev_properties = dbus.Interface(
            dev_proxy, "org.freedesktop.DBus.Properties")

        # Check if the device is a Wi-Fi interface
        device_type = dev_properties.Get(
            "org.freedesktop.NetworkManager.Device", "DeviceType")
        if device_type == 2:  # 2 indicates a Wi-Fi device
            device_state = dev_properties.Get(
                "org.freedesktop.NetworkManager.Device", "State")
            if device_state == 100:  # 100 indicates the device is connected
                ip4_config_path = dev_properties.Get(
                    "org.freedesktop.NetworkManager.Device", "Ip4Config")

                if ip4_config_path != "/":
                    ip4_config_proxy = dbus.SystemBus().get_object(
                        "org.freedesktop.NetworkManager", ip4_config_path)
                    ip4_config_properties = dbus.Interface(
                        ip4_config_proxy, "org.freedesktop.DBus.Properties")

                    addresses = ip4_config_properties.Get(
                        "org.freedesktop.NetworkManager.IP4Config", "Addresses")

                    if addresses:
                        # The IP address is in the first tuple, first item
                        ip_address = addresses[0][0]
                        # Format the IP address correctly
                        formatted_ip = ipaddress.IPv4Address(
                            ip_address).reverse_pointer.replace(".in-addr.arpa", "")
                        return formatted_ip

    return None


def send_command_to_tasmota(ip, command):
    command_prefix = f"http://{ip}/cm?cmnd="
    url = command_prefix + command
    response = requests.get(url)
    return response

if __name__ == "__main__":
    # Check if the script is run with sudo
    if os.geteuid() != 0:
        print("This script must be run as root or with sudo.")
        exit(1)

    # Get the active Wi-Fi device
    device_path, device_proxy, device_properties = get_active_wifi_device()
    if not device_proxy:
        print("No Wi-Fi device found.")
        exit()

    # Scan Wi-Fi networks and find Tasmota devices
    wifi_list = scan_wifi_networks(device_proxy)
    print(wifi_list)
    tasmota_list = getTasmotaHotspots(wifi_list)

    # Connect to Tasmota hotspots and send commands
    for endpoint in tasmota_list.index:
        if connect_to_wifi(device_proxy, tasmota_list.loc[endpoint]):
            gateway_ip = get_wifi_router_ip()
            localhost_ip = get_local_wifi_ip()
            print(f"Gateway IP: {gateway_ip}")
            print(f"Local IP: {localhost_ip}")

            #Send commands to Tasmota device
            command = f"Status 2"
            response = send_command_to_tasmota(gateway_ip, command)
            formatted_json = json.dumps(response.json(), indent=4)
            print(formatted_json)

            command = f"OtaUrl http://{localhost_ip}:5000/tasmota-minimal.bin.gz"
            response = send_command_to_tasmota(gateway_ip, command)
            formatted_json = json.dumps(response.json(), indent=4)
            print(formatted_json)

            command = f"Upgrade 1"
            response = send_command_to_tasmota(gateway_ip, command)
            formatted_json = json.dumps(response.json(), indent=4)
            print(formatted_json)

            print("Waiting for the device to reboot...")
            time.sleep(30)
            wifi_list = scan_wifi_networks(device_proxy)

            if connect_to_wifi(device_proxy, tasmota_list.loc[endpoint]):
                command = f"OtaUrl http://{localhost_ip}:5000/powsw10.bin"
                response = send_command_to_tasmota(gateway_ip, command)
                formatted_json = json.dumps(response.json(), indent=4)
                print(formatted_json)

                command = f"Upgrade 1"
                response = send_command_to_tasmota(gateway_ip, command)
                formatted_json = json.dumps(response.json(), indent=4)
                print(formatted_json)

                print("Waiting for the device to reboot...")
                time.sleep(30)
                # Disconnect from Wi-Fi
                disconnect_from_wifi(device_proxy)
