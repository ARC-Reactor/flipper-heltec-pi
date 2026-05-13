#!/usr/bin/env bash
# flash.sh — Compile and upload firmware to a Heltec WiFi LoRa 32 V3
#
# Usage:
#   ./flash.sh gateway [PORT]   — flash heltec_gateway to Heltec #1
#   ./flash.sh field   [PORT]   — flash heltec_field   to Heltec #2
#   ./flash.sh erase   [PORT]   — erase flash (use before Meshtastic)
#
# PORT defaults to /dev/ttyUSB0 for gateway, /dev/ttyUSB1 for field.
# Override: ./flash.sh gateway /dev/ttyACM0

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELTEC_FQBN="Heltec_ESP32_Dev-Boards:esp32:WIFI_LoRa_32_V3"
ARDUINO_CLI="${HOME}/.local/bin/arduino-cli"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()   { echo -e "${GREEN}[ OK ]${NC}  $*"; }
die()  { echo -e "${RED}[ERR ]${NC}  $*" >&2; exit 1; }

usage() {
  cat <<EOF
Usage: $(basename "$0") <target> [port]

Targets:
  gateway [PORT]   Compile + upload heltec_gateway  (default port: /dev/ttyUSB0)
  field   [PORT]   Compile + upload heltec_field    (default port: /dev/ttyUSB1)
  erase   [PORT]   Erase entire flash via esptool   (default port: /dev/ttyUSB0)
                   Use before flashing Meshtastic firmware.

Examples:
  ./flash.sh gateway
  ./flash.sh field /dev/ttyACM0
  ./flash.sh erase /dev/ttyUSB0
EOF
}

# ── Resolve arduino-cli ───────────────────────────────────────────────────────
if command -v arduino-cli &>/dev/null; then
  ARDUINO_CLI_CMD="arduino-cli"
elif [[ -x "$ARDUINO_CLI" ]]; then
  ARDUINO_CLI_CMD="$ARDUINO_CLI"
  export PATH="$HOME/.local/bin:$PATH"
else
  die "arduino-cli not found. Run ./setup.sh first."
fi

TARGET="${1:-}"
[[ -z "$TARGET" ]] && { usage; exit 1; }

case "$TARGET" in
  # ── gateway ────────────────────────────────────────────────────────────────
  gateway)
    PORT="${2:-/dev/ttyUSB0}"
    SKETCH="$REPO_ROOT/firmware/heltec_gateway"
    [[ -e "$PORT" ]] || die "Port $PORT not found. Is the Heltec connected? (ls /dev/ttyUSB*)"

    info "Compiling heltec_gateway..."
    "$ARDUINO_CLI_CMD" compile \
      --fqbn "$HELTEC_FQBN" \
      --warnings none \
      "$SKETCH"
    ok "Compile successful."

    info "Uploading to $PORT..."
    "$ARDUINO_CLI_CMD" upload \
      --fqbn "$HELTEC_FQBN" \
      --port "$PORT" \
      "$SKETCH"
    ok "heltec_gateway flashed to $PORT (Heltec #1 — base station)."
    echo
    echo "Monitor output: minicom -b 115200 -D $PORT"
    echo "Or:             python3 pi/serial_reader.py"
    ;;

  # ── field ──────────────────────────────────────────────────────────────────
  field)
    PORT="${2:-/dev/ttyUSB1}"
    SKETCH="$REPO_ROOT/firmware/heltec_field"
    [[ -e "$PORT" ]] || die "Port $PORT not found. Is the Heltec connected? (ls /dev/ttyUSB*)"

    info "Compiling heltec_field..."
    "$ARDUINO_CLI_CMD" compile \
      --fqbn "$HELTEC_FQBN" \
      --warnings none \
      "$SKETCH"
    ok "Compile successful."

    info "Uploading to $PORT..."
    "$ARDUINO_CLI_CMD" upload \
      --fqbn "$HELTEC_FQBN" \
      --port "$PORT" \
      "$SKETCH"
    ok "heltec_field flashed to $PORT (Heltec #2 — field node)."
    echo
    echo "Monitor output: minicom -b 115200 -D $PORT"
    ;;

  # ── erase ──────────────────────────────────────────────────────────────────
  erase)
    PORT="${2:-/dev/ttyUSB0}"
    [[ -e "$PORT" ]] || die "Port $PORT not found. (ls /dev/ttyUSB*)"

    if ! command -v esptool.py &>/dev/null; then
      # Check ~/.local/bin too
      if [[ -x "$HOME/.local/bin/esptool.py" ]]; then
        export PATH="$HOME/.local/bin:$PATH"
      else
        die "esptool.py not found. Run ./setup.sh first (or: pip3 install --user esptool)."
      fi
    fi

    info "Erasing flash on $PORT (put device in bootloader mode if upload fails)..."
    esptool.py --port "$PORT" erase_flash
    ok "Flash erased. Device is ready for Meshtastic or fresh firmware."
    echo
    echo "Next: flash Meshtastic via https://flasher.meshtastic.org"
    echo "  or: ./flash.sh gateway $PORT"
    ;;

  -h|--help) usage ;;
  *) die "Unknown target: $TARGET"; usage ;;
esac
