#!/usr/bin/env bash
# setup.sh — Quickstart installer for flipper-heltec-pi
#
# Installs everything needed to flash Heltec LoRa 32 V3 boards, run the
# Raspberry Pi MQTT bridge, and optionally the ham radio AI assistant.
#
# Usage:
#   ./setup.sh [options]
#
# After setup, flash boards with:
#   ./flash.sh gateway [PORT]   — flash Heltec #1 (base station)
#   ./flash.sh field   [PORT]   — flash Heltec #2 (field node)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARDUINO_CLI="$HOME/.local/bin/arduino-cli"
HELTEC_BOARD_URL="https://resource.heltec.cn/download/package_heltec_esp32_index.json"
HELTEC_FQBN="Heltec_ESP32_Dev-Boards:esp32:WIFI_LoRa_32_V3"

# ── Terminal colours ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()   { echo -e "${GREEN}[ OK ]${NC}  $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
die()  { echo -e "${RED}[ERR ]${NC}  $*" >&2; exit 1; }
step() { echo -e "\n${BOLD}${BLUE}━━━  $*  ━━━${NC}"; }

# ── Flags ─────────────────────────────────────────────────────────────────────
SKIP_ARDUINO=false
SKIP_MOSQUITTO=false
SKIP_HAM=false
SKIP_MESHTASTIC=false
SKIP_COMPILE=false

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --skip-arduino       Skip Arduino CLI + Heltec board/library setup
  --skip-compile       Skip sketch pre-compile (speeds up re-runs)
  --skip-mosquitto     Skip Mosquitto MQTT broker install + enable
  --skip-meshtastic    Skip Meshtastic + esptool Python tools
  --skip-ham           Skip ham radio AI assistant dependencies
  -h, --help           Show this help

What gets installed (all sections run by default):
  1. apt packages   — python3-pip/venv, git, curl, minicom, mosquitto
  2. dialout group  — serial port access for current user
  3. Pi venv        — .venv-pi/  with pyserial + paho-mqtt
  4. Arduino CLI    — ~/.local/bin/arduino-cli + Heltec ESP32 board support
  5. esptool        — ESP32 erase/flash utility (pip, global)
  6. Meshtastic CLI — meshtastic Python package (pip, global)
  7. Mosquitto      — MQTT broker enabled + started
  8. Ham radio venv — .venv-ham/ with Whisper + anthropic (optional)

After setup, flash with:
  ./flash.sh gateway [/dev/ttyUSB0]
  ./flash.sh field   [/dev/ttyUSB1]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-arduino)    SKIP_ARDUINO=true ;;
    --skip-compile)    SKIP_COMPILE=true ;;
    --skip-mosquitto)  SKIP_MOSQUITTO=true ;;
    --skip-meshtastic) SKIP_MESHTASTIC=true ;;
    --skip-ham)        SKIP_HAM=true ;;
    -h|--help)         usage; exit 0 ;;
    *) die "Unknown option: $1 (try --help)" ;;
  esac
  shift
done

# ── Helpers ───────────────────────────────────────────────────────────────────
require_sudo() {
  if [[ $EUID -eq 0 ]]; then
    die "Do not run this script as root. Run as your normal user — sudo will be invoked where needed."
  fi
  if ! sudo -n true 2>/dev/null; then
    info "Some steps require sudo. You may be prompted for your password."
    sudo -v
  fi
}

have() { command -v "$1" &>/dev/null; }

# ═════════════════════════════════════════════════════════════════════════════
step "1 / 8 — System packages"
# ═════════════════════════════════════════════════════════════════════════════

require_sudo

APT_PKGS=(
  python3-pip
  python3-venv
  git
  curl
  minicom          # serial monitor for debugging
  picocom          # lighter serial monitor
)

if ! $SKIP_MOSQUITTO; then
  APT_PKGS+=(mosquitto mosquitto-clients)
fi

info "Updating apt package list..."
sudo apt-get update -qq

MISSING_PKGS=()
for pkg in "${APT_PKGS[@]}"; do
  dpkg -s "$pkg" &>/dev/null || MISSING_PKGS+=("$pkg")
done

if [[ ${#MISSING_PKGS[@]} -gt 0 ]]; then
  info "Installing: ${MISSING_PKGS[*]}"
  sudo apt-get install -y -qq "${MISSING_PKGS[@]}"
  ok "Packages installed."
else
  ok "All apt packages already present."
fi

# ═════════════════════════════════════════════════════════════════════════════
step "2 / 8 — Serial port permissions (dialout group)"
# ═════════════════════════════════════════════════════════════════════════════

if groups "$USER" | grep -qw dialout; then
  ok "User $USER already in dialout group."
else
  sudo usermod -aG dialout "$USER"
  warn "Added $USER to dialout. Log out and back in (or run: newgrp dialout) for the change to take effect."
fi

# ═════════════════════════════════════════════════════════════════════════════
step "3 / 8 — Pi Python venv (.venv-pi)"
# ═════════════════════════════════════════════════════════════════════════════

VENV_PI="$REPO_ROOT/.venv-pi"

if [[ ! -d "$VENV_PI" ]]; then
  python3 -m venv "$VENV_PI"
  info "Created venv at $VENV_PI"
fi

"$VENV_PI/bin/pip" install --quiet --upgrade pip
"$VENV_PI/bin/pip" install --quiet -r "$REPO_ROOT/pi/requirements.txt"
ok "Pi venv ready. Activate with: source .venv-pi/bin/activate"

# ═════════════════════════════════════════════════════════════════════════════
step "4 / 8 — Arduino CLI + Heltec ESP32 board support"
# ═════════════════════════════════════════════════════════════════════════════

if $SKIP_ARDUINO; then
  warn "Skipping Arduino CLI setup (--skip-arduino)."
else
  mkdir -p "$HOME/.local/bin"

  if have arduino-cli || [[ -x "$ARDUINO_CLI" ]]; then
    ok "arduino-cli already installed ($(arduino-cli version 2>/dev/null | head -1 || echo 'version unknown'))."
  else
    info "Downloading arduino-cli..."
    curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh \
      | BINDIR="$HOME/.local/bin" sh -s -- --quiet
    ok "arduino-cli installed to ~/.local/bin/arduino-cli"
    export PATH="$HOME/.local/bin:$PATH"
  fi

  # Ensure PATH has arduino-cli for the rest of this script
  export PATH="$HOME/.local/bin:$PATH"

  ARDUINO_CLI_CMD="$(have arduino-cli && echo arduino-cli || echo "$ARDUINO_CLI")"

  # Init config if it doesn't exist
  if [[ ! -f "$HOME/.arduino15/arduino-cli.yaml" ]]; then
    "$ARDUINO_CLI_CMD" config init --quiet
    info "Initialized arduino-cli config."
  fi

  # Add Heltec board manager URL if not present
  CURRENT_URLS=$("$ARDUINO_CLI_CMD" config get board_manager.additional_urls 2>/dev/null || true)
  if echo "$CURRENT_URLS" | grep -q "heltec"; then
    ok "Heltec board manager URL already configured."
  else
    "$ARDUINO_CLI_CMD" config add board_manager.additional_urls "$HELTEC_BOARD_URL"
    info "Added Heltec board manager URL."
  fi

  info "Updating board index (may take a minute)..."
  "$ARDUINO_CLI_CMD" core update-index --quiet

  # Install Heltec ESP32 core if not present
  if "$ARDUINO_CLI_CMD" core list 2>/dev/null | grep -q "Heltec_ESP32_Dev-Boards"; then
    ok "Heltec ESP32 core already installed."
  else
    info "Installing Heltec ESP32 core (this downloads ~200 MB — grab a coffee)..."
    "$ARDUINO_CLI_CMD" core install Heltec_ESP32_Dev-Boards:esp32
    ok "Heltec ESP32 core installed."
  fi

  # The Heltec core bundles LoRaWan_APP and HT_SSD1306Wire — no extra lib installs needed.

  # ── Pre-compile both sketches ─────────────────────────────────────────────
  if $SKIP_COMPILE; then
    warn "Skipping sketch pre-compile (--skip-compile)."
  else
    for SKETCH in heltec_gateway heltec_field; do
      SKETCH_PATH="$REPO_ROOT/firmware/$SKETCH"
      info "Compiling $SKETCH..."
      if "$ARDUINO_CLI_CMD" compile \
          --fqbn "$HELTEC_FQBN" \
          --warnings none \
          "$SKETCH_PATH" 2>&1 | tail -3; then
        ok "$SKETCH compiled successfully."
      else
        warn "$SKETCH compile failed. Check that the Heltec library installed correctly."
        warn "Run manually: arduino-cli compile --fqbn $HELTEC_FQBN $SKETCH_PATH"
      fi
    done
  fi
fi

# ═════════════════════════════════════════════════════════════════════════════
step "5 + 6 / 8 — esptool + Meshtastic CLI"
# ═════════════════════════════════════════════════════════════════════════════

if $SKIP_MESHTASTIC; then
  warn "Skipping Meshtastic + esptool (--skip-meshtastic)."
else
  TOOLS_TO_INSTALL=()
  have esptool.py   || TOOLS_TO_INSTALL+=(esptool)
  have meshtastic   || TOOLS_TO_INSTALL+=(meshtastic)

  if [[ ${#TOOLS_TO_INSTALL[@]} -gt 0 ]]; then
    info "Installing: ${TOOLS_TO_INSTALL[*]}"
    pip3 install --quiet --user "${TOOLS_TO_INSTALL[@]}"
    export PATH="$HOME/.local/bin:$PATH"
    ok "esptool + meshtastic installed."
  else
    ok "esptool and meshtastic already installed."
  fi
fi

# ═════════════════════════════════════════════════════════════════════════════
step "7 / 8 — Mosquitto MQTT broker"
# ═════════════════════════════════════════════════════════════════════════════

if $SKIP_MOSQUITTO; then
  warn "Skipping Mosquitto setup (--skip-mosquitto)."
else
  if systemctl is-enabled mosquitto &>/dev/null; then
    ok "Mosquitto already enabled."
  else
    sudo systemctl enable mosquitto
    info "Mosquitto service enabled."
  fi

  if systemctl is-active mosquitto &>/dev/null; then
    ok "Mosquitto is running."
  else
    sudo systemctl start mosquitto
    ok "Mosquitto started."
  fi
fi

# ═════════════════════════════════════════════════════════════════════════════
step "8 / 8 — Ham radio AI assistant venv (.venv-ham)  [optional]"
# ═════════════════════════════════════════════════════════════════════════════

if $SKIP_HAM; then
  warn "Skipping ham radio venv (--skip-ham)."
else
  VENV_HAM="$REPO_ROOT/.venv-ham"

  # Whisper + torch pull in ~2 GB on first install — ask before proceeding.
  if [[ ! -d "$VENV_HAM" ]]; then
    echo
    read -r -p "Install ham radio AI assistant deps (Whisper/torch/anthropic, ~2 GB)? [y/N] " REPLY
    if [[ "$REPLY" =~ ^[Yy]$ ]]; then
      python3 -m venv "$VENV_HAM"
      "$VENV_HAM/bin/pip" install --quiet --upgrade pip
      info "Installing ham radio requirements (this will take a while)..."
      "$VENV_HAM/bin/pip" install -r "$REPO_ROOT/ham_radio/requirements.txt"
      ok "Ham radio venv ready. Activate with: source .venv-ham/bin/activate"
      warn "Set ANTHROPIC_API_KEY before running ham_radio_pipeline.py"
    else
      info "Skipped. Run later with: python3 -m venv .venv-ham && .venv-ham/bin/pip install -r ham_radio/requirements.txt"
    fi
  else
    ok "Ham radio venv already exists at $VENV_HAM."
  fi
fi

# ═════════════════════════════════════════════════════════════════════════════
echo
echo -e "${BOLD}${GREEN}━━━  Setup complete  ━━━${NC}"
echo
echo -e "${BOLD}Next steps:${NC}"
echo
echo "  1. Flash the Heltec boards (connect via USB-C first):"
echo "       ./flash.sh gateway [/dev/ttyUSB0]    — Heltec #1 base station"
echo "       ./flash.sh field   [/dev/ttyUSB1]    — Heltec #2 field node"
echo
echo "  2. Find attached serial ports:"
echo "       ls /dev/ttyUSB*"
echo "       dmesg | grep ttyUSB"
echo
echo "  3. Run the Pi MQTT bridge:"
echo "       source .venv-pi/bin/activate"
echo "       python3 pi/mqtt_bridge.py"
echo
echo "  4. Monitor serial output (debug):"
echo "       source .venv-pi/bin/activate"
echo "       python3 pi/serial_reader.py"
echo "       # or: minicom -b 115200 -D /dev/ttyUSB0"
echo
if ! groups "$USER" | grep -qw dialout; then
  echo -e "  ${YELLOW}⚠ Remember to log out and back in for dialout group membership to take effect.${NC}"
  echo
fi
echo "  See firmware/README.md for LoRa parameter reference."
echo "  See docs/meshtastic.md  for the Meshtastic alternate firmware path."
echo
