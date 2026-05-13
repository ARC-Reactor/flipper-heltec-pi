# Flipper Zero + Heltec LoRa 32 × 2 + Raspberry Pi 4

A long-range wireless mesh system combining a portable field tool, two LoRa radio nodes, and a Linux hub — with optional AI assistant and Meshtastic support.

---

## System Architecture

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
| Heltec LoRa 32 #1 | Base gateway — always on at base station | USB serial → Pi |
| Heltec LoRa 32 #2 | Field node — portable, carried with the Flipper | LoRa → Heltec #1, UART → Flipper |
| Raspberry Pi 4 | Central hub — MQTT broker, dashboard, data logger | USB → Heltec #1 |

---

## Repository Structure

```
.
├── README.md
├── firmware/                       ← Arduino sketches for both Heltec boards
│   ├── README.md                       ← LoRa config, flashing instructions
│   ├── heltec_gateway/             ← Heltec #1: gateway (base station)
│   │   ├── README.md
│   │   └── heltec_gateway.ino
│   └── heltec_field/               ← Heltec #2: field node (portable)
│       ├── README.md
│       └── heltec_field.ino
├── pi/                             ← Raspberry Pi scripts
│   ├── README.md                       ← Usage guide and topic reference
│   ├── serial_reader.py                ← Console monitor (debug / quick check)
│   ├── mqtt_bridge.py                  ← Full MQTT bridge (production)
│   └── requirements.txt
├── ham_radio/                      ← Optional AI assistant tools
│   ├── README.md                       ← Setup and usage guide
│   ├── ham_radio_assistant.html        ← Browser voice assistant (no install)
│   ├── ham_radio_pipeline.py           ← Python CLI: audio capture + Claude AI
│   └── requirements.txt
└── docs/
    ├── wiring.md                   ← GPIO / UART wiring diagrams
    └── meshtastic.md               ← Alternative: Meshtastic firmware setup
```

---

## Quick Start

### 1. Flash the Heltec boards

Install the [Heltec ESP32 library](https://github.com/HelTecAutomation/Heltec_ESP32) in Arduino IDE, then:

- Flash `firmware/heltec_gateway/heltec_gateway.ino` to **Heltec #1** (base station)
- Flash `firmware/heltec_field/heltec_field.ino` to **Heltec #2** (field node)

See [`firmware/README.md`](firmware/README.md) for the full parameter table and flashing steps.

### 2. Wire Flipper Zero to Heltec #2

See [`docs/wiring.md`](docs/wiring.md) for the full pinout and power warnings.

### 3. Set up the Raspberry Pi

```bash
sudo apt update && sudo apt install -y mosquitto mosquitto-clients python3-pip
pip3 install -r pi/requirements.txt
sudo systemctl enable --now mosquitto
```

### 4. Run the Pi scripts

```bash
python3 pi/serial_reader.py   # print received packets to console (debug)
python3 pi/mqtt_bridge.py     # bridge LoRa ↔ MQTT (production)
```

See [`pi/README.md`](pi/README.md) for MQTT topic reference and sending commands.

---

## Optional: Ham Radio AI Assistant

A voice-activated Claude AI assistant for your shack. Works standalone — no LoRa hardware needed.

- **Browser app** — open `ham_radio/ham_radio_assistant.html` in Chrome/Edge, no install
- **Python pipeline** — tap radio audio directly with local Whisper STT + Claude

See [`ham_radio/README.md`](ham_radio/README.md).

---

## Optional: Meshtastic

Both Heltec boards are officially supported Meshtastic hardware. Meshtastic replaces the custom firmware with encrypted mesh networking, GPS position sharing, and the ZeroMesh Flipper app.

See [`docs/meshtastic.md`](docs/meshtastic.md).

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
