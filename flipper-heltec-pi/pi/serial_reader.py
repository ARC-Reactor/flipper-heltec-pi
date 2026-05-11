"""
serial_reader.py
Raspberry Pi — reads JSON packets from Heltec #1 (gateway) over USB serial.
Prints to console. See mqtt_bridge.py to publish to MQTT instead.

Usage:
    python3 serial_reader.py
    python3 serial_reader.py --port /dev/ttyUSB1 --baud 115200
"""

import serial
import json
import argparse
import time
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser(description="Read LoRa packets from Heltec gateway")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial port (default: /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    return parser.parse_args()


def send_command(ser, command: str):
    """Send a command to the gateway to broadcast over LoRa."""
    line = command.strip() + "\n"
    ser.write(line.encode("utf-8"))
    print(f"[{timestamp()}] SENT: {command}")


def timestamp():
    return datetime.now().strftime("%H:%M:%S")


def main():
    args = parse_args()

    print(f"Connecting to {args.port} at {args.baud} baud...")
    try:
        ser = serial.Serial(args.port, args.baud, timeout=1)
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        print("Check that the Heltec is connected and the port is correct.")
        print("List available ports: ls /dev/ttyUSB*")
        return

    print(f"Connected. Listening for packets...\n")
    time.sleep(2)  # wait for device to settle

    try:
        while True:
            raw = ser.readline().decode("utf-8", errors="replace").strip()
            if not raw:
                continue

            try:
                packet = json.loads(raw)
                ptype = packet.get("type", "unknown")

                if ptype == "rx":
                    print(
                        f"[{timestamp()}] RX | "
                        f"RSSI: {packet.get('rssi', '?')} dBm | "
                        f"SNR: {packet.get('snr', '?')} dB | "
                        f"Payload: {packet.get('payload', '')}"
                    )
                elif ptype == "tx":
                    print(f"[{timestamp()}] TX | Payload: {packet.get('payload', '')}")
                elif packet.get("status"):
                    print(f"[{timestamp()}] STATUS: {packet['status']}")
                else:
                    print(f"[{timestamp()}] RAW: {raw}")

            except json.JSONDecodeError:
                # Non-JSON debug output from the board
                print(f"[{timestamp()}] DEBUG: {raw}")

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
