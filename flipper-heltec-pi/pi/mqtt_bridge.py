"""
mqtt_bridge.py
Raspberry Pi — reads packets from Heltec #1 over USB serial
and publishes them to a local MQTT broker (Mosquitto).

Topics published:
    lora/rx        — incoming LoRa packets from the field
    lora/status    — gateway status messages

Topics subscribed:
    lora/tx        — messages to broadcast out over LoRa

Usage:
    python3 mqtt_bridge.py
    python3 mqtt_bridge.py --port /dev/ttyUSB0 --broker localhost
"""

import serial
import json
import argparse
import time
import threading
from datetime import datetime
import paho.mqtt.client as mqtt


def parse_args():
    parser = argparse.ArgumentParser(description="LoRa ↔ MQTT bridge")
    parser.add_argument("--port",   default="/dev/ttyUSB0", help="Serial port")
    parser.add_argument("--baud",   type=int, default=115200)
    parser.add_argument("--broker", default="localhost",    help="MQTT broker address")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--topic-rx", default="lora/rx")
    parser.add_argument("--topic-tx", default="lora/tx")
    parser.add_argument("--topic-status", default="lora/status")
    return parser.parse_args()


def timestamp():
    return datetime.now().strftime("%H:%M:%S")


def main():
    args = parse_args()

    # ── Serial ────────────────────────────────────────────────────────────────
    print(f"Opening serial port {args.port}...")
    try:
        ser = serial.Serial(args.port, args.baud, timeout=1)
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        return
    time.sleep(2)

    # ── MQTT ──────────────────────────────────────────────────────────────────
    client = mqtt.Client(client_id="lora-bridge")

    def on_connect(c, userdata, flags, rc):
        if rc == 0:
            print(f"[{timestamp()}] MQTT connected to {args.broker}")
            c.subscribe(args.topic_tx)
            print(f"[{timestamp()}] Subscribed to {args.topic_tx}")
        else:
            print(f"[{timestamp()}] MQTT connection failed (rc={rc})")

    def on_message(c, userdata, msg):
        """Forward MQTT lora/tx messages out over LoRa via serial."""
        payload = msg.payload.decode("utf-8").strip()
        print(f"[{timestamp()}] MQTT→LoRa: {payload}")
        ser.write((payload + "\n").encode("utf-8"))

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.broker, args.mqtt_port, keepalive=60)
    client.loop_start()

    # ── Serial read loop ──────────────────────────────────────────────────────
    print(f"Bridging {args.port} ↔ MQTT ({args.broker})...\n")
    try:
        while True:
            raw = ser.readline().decode("utf-8", errors="replace").strip()
            if not raw:
                continue

            try:
                packet = json.loads(raw)
                ptype  = packet.get("type", "")
                status = packet.get("status", "")

                if ptype == "rx":
                    # Enrich with timestamp before publishing
                    packet["ts"] = datetime.utcnow().isoformat() + "Z"
                    client.publish(args.topic_rx, json.dumps(packet))
                    print(
                        f"[{timestamp()}] RX → MQTT | "
                        f"RSSI: {packet.get('rssi')} | "
                        f"{packet.get('payload', '')}"
                    )
                elif status:
                    client.publish(args.topic_status, json.dumps(packet))
                    print(f"[{timestamp()}] STATUS: {status}")

            except json.JSONDecodeError:
                print(f"[{timestamp()}] DEBUG: {raw}")

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        client.loop_stop()
        client.disconnect()
        ser.close()


if __name__ == "__main__":
    main()
