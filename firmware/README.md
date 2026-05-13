# Firmware

Two Arduino sketches for the Heltec WiFi LoRa 32 V3 boards.

| Sketch | Target board | Role |
|---|---|---|
| [`heltec_gateway/`](heltec_gateway/) | Heltec #1 | Base station — relays between LoRa and the Raspberry Pi over USB serial |
| [`heltec_field/`](heltec_field/) | Heltec #2 | Portable field node — relays between the Flipper Zero (UART) and the gateway (LoRa) |

---

## Prerequisites

- [Arduino IDE](https://www.arduino.cc/en/software) 2.x or [PlatformIO](https://platformio.org/)
- [Heltec ESP32 Arduino library](https://github.com/HelTecAutomation/Heltec_ESP32) — install via Arduino Library Manager or the Heltec board manager URL

## Flashing

1. Open `heltec_gateway/heltec_gateway.ino` in Arduino IDE
2. Select board: **Heltec WiFi LoRa 32(V3)** under *Heltec ESP32 Series Dev-boards*
3. Select the correct serial port
4. Upload — this board stays wired to the Pi

Repeat with `heltec_field/heltec_field.ino` for the portable Heltec #2.

---

## Shared LoRa Configuration

Both sketches must use identical RF settings to communicate. The `#define` block at the top of each sketch controls these. Change a value in **both files** and re-flash both boards.

| Parameter | Value | Notes |
|---|---|---|
| Frequency | 915 MHz | US ISM band — change to `868E6` for EU |
| Bandwidth | 125 kHz | |
| Spreading factor | SF7 | Fast, shorter range. SF10–SF12 trades speed for ~5–15 km range |
| Coding rate | 4/5 | |
| Sync word | `0xAB` | Private network identifier — change to avoid cross-talk with other LoRa devices |
| TX power | 14 dBm | Legal limit for unlicensed ISM use. Licensed hams may increase |
| CRC | enabled | Detects corrupted packets |

---

## Packet Format

JSON is used for all serial and LoRa messages so every layer can parse them easily.

```
Gateway → Pi (serial)
  {"type": "rx", "payload": "...", "rssi": -87, "snr": 6.5}   ← incoming LoRa packet
  {"status": "gateway_ready"}                                  ← startup heartbeat

Pi → Gateway (serial) → Field (LoRa)
  any string — forwarded verbatim

Field → Flipper (UART)
  {"type": "rx", "payload": "...", "rssi": -87}

Flipper → Field (UART) → Gateway (LoRa) → Pi (serial)
  any string — forwarded verbatim
```

---

## Alternative: Meshtastic

Both Heltec V3 boards are officially supported Meshtastic hardware. Meshtastic replaces these sketches with encrypted mesh networking, GPS position sharing, and Flipper Zero integration via the ZeroMesh app. See [`../docs/meshtastic.md`](../docs/meshtastic.md).
