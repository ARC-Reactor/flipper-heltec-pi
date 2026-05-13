# heltec_field — Field Node Firmware

This sketch runs on **Heltec #2**, the portable board that rides with the Flipper Zero in the field.

## What it does

- Bridges the Flipper Zero (UART) and the base gateway (LoRa)
- Forwards any message received from the Flipper over LoRa to the gateway
- Forwards any LoRa packet received from the gateway back to the Flipper over UART

```
Flipper Zero
    │ UART (115200 baud, GPIO 5 RX / GPIO 6 TX)
    ▼
Heltec #2 (this firmware)
    │ LoRa RF (915 MHz, SF7, BW 125 kHz)
    ▼
Heltec #1 (gateway) → Raspberry Pi
```

## UART wiring (Flipper ↔ Heltec #2)

| Flipper Zero | Heltec GPIO | Direction |
|---|---|---|
| Pin 13 (TX) | GPIO 5 (RX1) | Flipper → Heltec |
| Pin 14 (RX) | GPIO 6 (TX1) | Heltec → Flipper |
| Pin 8 (GND) | GND | Common ground |

Full pinout and power warnings: [`../../docs/wiring.md`](../../docs/wiring.md)

## Messages sent to Flipper (UART)

```json
{"type": "rx", "payload": "...", "rssi": -87}
{"status": "field_ready"}
```

## Messages received from Flipper (UART)

Any string terminated with `\n` — forwarded over LoRa to the gateway verbatim.

## OLED display

The built-in 128×64 display shows:

```
Field node
TX: 5  RX: 3
last status text
```

## LoRa config

See [`../README.md`](../README.md) for the full parameter table. Both boards must match.
