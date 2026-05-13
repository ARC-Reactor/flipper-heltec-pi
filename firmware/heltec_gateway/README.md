# heltec_gateway — Base Station Firmware

This sketch runs on **Heltec #1**, the board that stays at the base and connects to the Raspberry Pi via USB-C.

## What it does

- Listens for LoRa packets from the field node (Heltec #2)
- Forwards each received packet to the Pi as a JSON line over USB serial
- Listens for commands from the Pi over serial and broadcasts them over LoRa

```
Raspberry Pi
    │ USB serial (115200 baud)
    ▼
Heltec #1 (this firmware)
    │ LoRa RF (915 MHz, SF7, BW 125 kHz)
    ▼
Heltec #2 (field node)
```

## Serial output to Pi

```json
{"type": "rx", "payload": "...", "rssi": -87, "snr": 6.5}
{"status": "gateway_ready"}
{"type": "tx", "payload": "..."}
```

The Pi scripts (`serial_reader.py` and `mqtt_bridge.py`) parse these lines directly.

## Serial input from Pi

Any plain string terminated with `\n` is forwarded over LoRa to the field node verbatim. The gateway echoes `{"type":"tx","payload":"..."}` back to the Pi as confirmation.

## OLED display

The built-in 128×64 display shows:

```
Gateway [RX: 12]
RSSI: -87 dBm
last payload text
```

## LoRa config

See [`../README.md`](../README.md) for the full parameter table. To change settings, edit the `#define` block at the top of the sketch and re-flash both boards.
