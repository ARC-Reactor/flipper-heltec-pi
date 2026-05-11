# Flipper Zero + Heltec LoRa 32 × 2 + Raspberry Pi 4

A long-range wireless mesh system combining a portable field tool, two LoRa radio nodes, and a Linux hub — with optional Meshtastic support.

---

## System Overview

```
[Flipper Zero] ──UART──► [Heltec #2 (field node)]
                                  │
                              LoRa RF
                           (~5 km range)
                                  │
                         [Heltec #1 (gateway)] ──USB serial──► [Raspberry Pi 4]
                                                                       │
                                                               MQTT / Node-RED
```

---

## Device Roles

| Device | Role | Connection |
|---|---|---|
| Flipper Zero | Portable field tool — NFC, IR, Sub-GHz, scripting | UART → Heltec #2 |
| Heltec LoRa 32 #1 | Dedicated base gateway | USB serial → Pi |
| Heltec LoRa 32 #2 | Remote field node + sensor carrier | LoRa RF → Heltec #1, UART → Flipper |
| Raspberry Pi 4 | Central hub — MQTT broker, dashboard, data logger | USB → Heltec #1 |

---

## Repository Structure

```
.
├── README.md
├── docs/
│   ├── wiring.md           # GPIO and UART wiring diagrams
│   └── meshtastic.md       # Meshtastic firmware setup guide
├── firmware/
│   ├── heltec_gateway/     # Arduino sketch for Heltec #1 (custom firmware)
│   │   └── heltec_gateway.ino
│   └── heltec_field/       # Arduino sketch for Heltec #2 (custom firmware)
│       └── heltec_field.ino
└── pi/
    ├── serial_reader.py    # Reads LoRa packets from Heltec #1 over USB serial
    ├── mqtt_bridge.py      # Publishes packets to local MQTT broker
    └── requirements.txt
```

> **Note:** If you prefer Meshtastic over custom firmware, see [`docs/meshtastic.md`](docs/meshtastic.md). The `firmware/` sketches are for a fully custom setup.

---

## Quick Start

### 1. Raspberry Pi — install dependencies

```bash
sudo apt update && sudo apt install -y mosquitto mosquitto-clients python3-pip
pip3 install -r pi/requirements.txt
```

Start Mosquitto on boot:
```bash
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### 2. Flash Heltec boards

Open the sketches in Arduino IDE (or PlatformIO). Install the [Heltec ESP32 library](https://github.com/HelTecAutomation/Heltec_ESP32) first.

- Flash `firmware/heltec_gateway/` to Heltec #1 (the one that stays wired to the Pi)
- Flash `firmware/heltec_field/` to Heltec #2 (the portable field node)

Both boards must use the same frequency (`LORA_FREQUENCY`) and sync word (`LORA_SYNC_WORD`).

### 3. Wire Flipper Zero to Heltec #2

See [`docs/wiring.md`](docs/wiring.md) for the full pinout.

### 4. Run the Pi scripts

```bash
python3 pi/serial_reader.py   # reads packets, prints to console
python3 pi/mqtt_bridge.py     # reads packets, publishes to MQTT
```

---

## Optional: Meshtastic

Both Heltec boards are officially supported Meshtastic hardware. See [`docs/meshtastic.md`](docs/meshtastic.md) to replace the custom firmware with Meshtastic for encrypted mesh messaging, GPS sharing, and the ZeroMesh Flipper app.

---

## Hardware

- [Flipper Zero](https://flipperzero.one/)
- [Heltec WiFi LoRa 32 V3](https://heltec.org/project/wifi-lora-32-v3/) × 2
- Raspberry Pi 4 (any RAM variant)
- Jumper wires for UART connection (Flipper ↔ Heltec #2)
- USB-C cable for each Heltec

---

## License

MIT
