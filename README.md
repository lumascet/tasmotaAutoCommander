# TasmotaAutoCommander

A Python project to automate the configuration of Tasmota devices via the WifiManager. Currently, it includes a script for auto-reflashing Tasmota devices to ESPHome.

## `tasmota2esphome.py`

This script allows you to migrate Tasmota devices from the Tasmota Wifi Manager (when not connected to a local wifi network) to ESPHome. It saves time by automating the following steps:

- Connects to the Tasmota device's WiFi given a defined prefix (e.g., "tasmota-").
- Flashes `tasmota-minimal.bin.gz` to create space for the ESPHome binary.
- Flashes any `esphome.bin` firmware.
- Connects to the ESPHome Wifi Manager and automatically configures it to the desired wifi network.
- Home Assistant will automatically detect the device, allowing you to adopt it (if an ESPHome image with the "dashboard_import" configuration is used).

### Usage

1. Create a Folder ```fw``` and copy tasmota minimal and your target ESPHome binary

    ```bash
    wget http://ota.tasmota.com/tasmota/release/tasmota-minimal.bin.gz -P ./fw/
    ```

2. Run `ota_server.py`

    ```bash
    python3 ota_server.py -i 192.168.4.2
    ```

3. Create `credentials.py` based on `credentials_example.py`

4. Run `tasmota2esphome.py` as root

    ```bash
    sudo python3 tasmota2esphome.py
    ```

## Credits

- `ota_server.py` - Firmware server for Tasmota OTA upgrade  
  Copyright (C) 2019 Gennaro Tortone
