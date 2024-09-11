# tasmotaAutoCommander
Python project to automate the configuration of tasmota devices via the WifiManager. Currently only one project for auto reflashing tasmota devices to esphome.

## tasmota2esphome.py
With this script you can migrate tasmota devices from the tasmota wifi manager (so not connected to a local wifi hotspot) to esphome.
This saves you a lot of time as the script automatically:

- connects to wifi given a defined prefix, e.g. "tasmota-"
- flashes tasmota-minimal.bin.gz to make room for the esp binary
- flashes any esphome.bin
- connects to the esphome wifi manager and auto configures to the desired wifi hotspot.
- Home assistant now automatically detects the device and you can adopt the device (if a esphome image is used with "dashboard_import" config)

### Usage

- First run ```ota_server.py```:

```bash
python3 ota_server.py -i 192.168.4.2
```
- Configure the ```credentials.py``` from the ```credentials_exmaple.py```
- Then run ```tasmota2esphome.py```

```bash
sudo python3 tasmota2esphome.py
```