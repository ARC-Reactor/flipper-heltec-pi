# Meshtastic Setup Guide

Both Heltec LoRa 32 boards are officially supported Meshtastic hardware. This guide replaces the custom Arduino firmware with Meshtastic for encrypted mesh messaging, GPS position sharing, and Flipper Zero integration via ZeroMesh.

---

## Flash Meshtastic Firmware

### Option A — Web Flasher (recommended)

1. Go to [flasher.meshtastic.org](https://flasher.meshtastic.org)
2. Connect Heltec via USB-C
3. Select **Heltec LoRa 32 V3** (or V2 if applicable) from the device dropdown
4. Click **Flash** and wait for completion
5. Repeat for the second Heltec

### Option B — CLI

```bash
pip install meshtastic esptool
esptool.py --port /dev/ttyUSB0 erase_flash
# then flash via web flasher or meshtastic CLI
```

---

## Configure Each Node

Connect to the node via the [Meshtastic web client](https://client.meshtastic.org) over USB or WiFi, or use the Python CLI:

```bash
pip install meshtastic
meshtastic --port /dev/ttyUSB0 --info
```

### Key settings to configure

```bash
# Set region (required before the radio will transmit)
meshtastic --port /dev/ttyUSB0 --set lora.region EU_868   # Europe
meshtastic --port /dev/ttyUSB0 --set lora.region US       # USA

# Set a channel name/password (both nodes must match)
meshtastic --port /dev/ttyUSB0 --ch-set name "mynet"
meshtastic --port /dev/ttyUSB0 --ch-set psk random

# Set node role
# Heltec #1 (base, always on): ROUTER or ROUTER_CLIENT
meshtastic --port /dev/ttyUSB0 --set device.role ROUTER_CLIENT

# Heltec #2 (field, portable): CLIENT
meshtastic --port /dev/ttyUSB1 --set device.role CLIENT
```

---

## Raspberry Pi — meshtasticd (Linux native node)

The Pi can participate in the mesh as a node using `meshtasticd`:

```bash
pip install meshtastic
# Connect Heltec #1 via USB, then:
meshtasticd --port /dev/ttyUSB0
```

Or use the Python API to read all mesh traffic and publish to MQTT:

```python
import meshtastic
import meshtastic.serial_interface

def on_receive(packet, interface):
    print(f"From: {packet['from']} | Message: {packet.get('decoded', {}).get('text', '')}")

iface = meshtastic.serial_interface.SerialInterface("/dev/ttyUSB0")
meshtastic.mesh_pb2  # subscribe
iface.localNode.setOwner("pi-base")

from pubsub import pub
pub.subscribe(on_receive, "meshtastic.receive")

import time
while True:
    time.sleep(1)
```

### Meshtastic MQTT bridge

Meshtastic has a built-in MQTT uplink. Enable it to forward all mesh traffic to your local Mosquitto broker:

```bash
meshtastic --port /dev/ttyUSB0 --set mqtt.enabled true
meshtastic --port /dev/ttyUSB0 --set mqtt.address localhost
meshtastic --port /dev/ttyUSB0 --set mqtt.root meshtastic
```

Messages will appear on topics like `meshtastic/2/json/LongFast/!<node_id>`.

---

## Flipper Zero — ZeroMesh App

ZeroMesh connects the Flipper to Heltec #2 (running Meshtastic) over UART.

### Requirements

- Flipper Zero running **Momentum** or **Unleashed** custom firmware (for community app support)
- Heltec #2 flashed with Meshtastic
- Heltec serial mode set to `PROTO`:

```bash
meshtastic --port /dev/ttyUSB0 --set serial.mode PROTO
meshtastic --port /dev/ttyUSB0 --set serial.baud BAUD_115200
meshtastic --port /dev/ttyUSB0 --set serial.enabled true
```

### Install ZeroMesh

1. Clone [github.com/SAMS0N1TE/ZeroMesh](https://github.com/SAMS0N1TE/ZeroMesh)
2. Copy the `zeromesh` folder into `applications_user/` in your Flipper firmware source
3. Build and flash, or install via the Flipper app catalog if available

### Wire Flipper to Heltec #2

See [`wiring.md`](wiring.md) — same UART pinout (Pin 13 TX, Pin 14 RX, GND).

### ZeroMesh features

- View mesh node roster with SNR and RSSI per node
- Send broadcast messages to the entire mesh
- Send direct private messages to specific nodes
- View telemetry: battery %, voltage
- Settings and message history stored on SD card

---

## Architecture with Meshtastic

```
[Flipper Zero]
  ZeroMesh app
      │ UART (PROTO mode)
      ▼
[Heltec #2]                    [Other mesh nodes]
  Meshtastic CLIENT  ◄──LoRa──► (phones, other Heltecs, etc.)
      │ LoRa RF
      ▼
[Heltec #1]
  Meshtastic ROUTER_CLIENT
      │ USB serial
      ▼
[Raspberry Pi 4]
  meshtasticd / Python API
      │
      ▼
  Mosquitto MQTT ──► Node-RED dashboard
```
