# Raspberry Pi Scripts

Two Python scripts for reading LoRa data from Heltec #1 (the gateway board) over USB serial.

## Install

```bash
pip3 install -r requirements.txt
```

---

## `serial_reader.py` — Console Monitor

Reads JSON packets from the gateway and prints them to the terminal. The simplest way to verify the LoRa link is working before setting up MQTT.

```bash
python3 serial_reader.py
python3 serial_reader.py --port /dev/ttyUSB1 --baud 115200
```

**Sample output:**

```
[14:32:07] RX  | RSSI: -87 dBm | SNR: 6.5 dB | Payload: hello from field
[14:32:10] TX  | Payload: ack
[14:32:10] STATUS: gateway_ready
[14:32:11] DEBUG: non-JSON line from board
```

To transmit a message over LoRa from Python, call `send_command(ser, "your message")` after opening the serial port.

---

## `mqtt_bridge.py` — MQTT Bridge

Publishes received LoRa packets to a local Mosquitto broker and subscribes to an outbound topic. Use this for Node-RED dashboards, Home Assistant, or any MQTT consumer.

```bash
python3 mqtt_bridge.py
python3 mqtt_bridge.py --port /dev/ttyUSB0 --broker localhost
```

### MQTT topics

| Topic | Direction | Payload |
|---|---|---|
| `lora/rx` | published | Incoming LoRa packets — JSON with added `ts` timestamp |
| `lora/status` | published | Gateway startup / status messages |
| `lora/tx` | subscribed | Any string to broadcast out over LoRa |

### Example: send a message over LoRa via MQTT

```bash
mosquitto_pub -t lora/tx -m "ping field node"
```

### Start Mosquitto automatically on boot

```bash
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

---

## Finding the serial port

```bash
ls /dev/ttyUSB*
# or
dmesg | grep ttyUSB
```

The Heltec's onboard CP2102 chip usually appears as `/dev/ttyUSB0`. If another USB serial device is already connected it may be `/dev/ttyUSB1`.

---

## Choosing between the two scripts

| | `serial_reader.py` | `mqtt_bridge.py` |
|---|---|---|
| Use case | Debug / quick check | Production / dashboard |
| Dependencies | pyserial only | pyserial + paho-mqtt + Mosquitto |
| Persists data | No | Via MQTT consumers |
| Sends commands | Yes (`send_command`) | Yes (publish to `lora/tx`) |
