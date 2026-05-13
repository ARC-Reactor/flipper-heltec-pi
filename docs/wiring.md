# Wiring Guide

## Flipper Zero ↔ Heltec LoRa 32 #2 (UART)

Connect with jumper wires. Use 3.3V logic — both devices are 3.3V, so no level shifter needed.

| Flipper Zero Pin | Heltec LoRa 32 Pin | Notes |
|---|---|---|
| Pin 13 (TX) | RX (GPIO 5) | Flipper transmits → Heltec receives |
| Pin 14 (RX) | TX (GPIO 6) | Heltec transmits → Flipper receives |
| Pin 8 (GND) | GND | Common ground — required |
| Pin 1 (5V) | — | **Do not connect.** Power each device independently |

> ⚠️ **Power warning:** Never connect the Flipper 5V pin to the Heltec when either device is also powered via USB. Back-feeding will damage both devices. Use one power source at a time.

### Flipper GPIO header layout (top edge, left to right)

```
[ 5V ][ GND ][ 3.3V ][ A7 ][ A6 ][ A4 ][ B3 ][ B2 ][ C3 ][ C1 ][ C0 ]
  1     8      9      10    11    12    13    14    15    16    17
```

Pins 13 (TX) and 14 (RX) are the UART pins used by ZeroMesh and custom serial apps.

---

## Heltec LoRa 32 #1 ↔ Raspberry Pi 4 (USB Serial)

Connect with a USB-C cable. The Heltec's onboard CP2102 chip handles USB-to-serial conversion. No additional wiring needed.

The Pi will see the device as `/dev/ttyUSB0` (or `/dev/ttyUSB1` if another USB serial device is connected first). Confirm with:

```bash
ls /dev/ttyUSB*
# or
dmesg | grep ttyUSB
```

Default baud rate: **115200**

---

## Heltec LoRa 32 — Antenna

Always attach the LoRa antenna **before** powering on. Transmitting without an antenna can damage the SX1262 RF frontend.

- Connect the LoRa antenna to the U.FL/IPEX connector labelled `LoRa`
- The onboard spring antenna handles 2.4 GHz WiFi/BLE — no external antenna needed for those

---

## Optional: External sensors on Heltec #2

The field node can carry sensors on its GPIO pins. Common additions:

| Sensor | Interface | Heltec Pins |
|---|---|---|
| DHT22 (temp/humidity) | Single-wire | GPIO 48 |
| BME280 (temp/pressure) | I2C | SDA→GPIO 41, SCL→GPIO 42 |
| GPS module (GT-U7 etc.) | UART | TX→GPIO 47, RX→GPIO 48 |
| PIR motion sensor | Digital in | Any free GPIO |

> See the [Meshtastic GPS guide](https://meshtastic.org/docs/hardware/devices/heltec-automation/lora32/peripherals/) for adding GPS with power management via MOSFET.
