/*
 * heltec_gateway.ino
 * Heltec LoRa 32 #1 — Base Gateway
 *
 * Receives LoRa packets from the field node (Heltec #2)
 * and forwards them over USB serial to the Raspberry Pi.
 *
 * Also receives commands from the Pi over serial and
 * broadcasts them over LoRa to the field node.
 *
 * Board: Heltec WiFi LoRa 32 V3
 * Library: Heltec ESP32 (https://github.com/HelTecAutomation/Heltec_ESP32)
 */

#include "LoRaWan_APP.h"
#include "HT_SSD1306Wire.h"

// ── LoRa config — must match heltec_field.ino ────────────────────────────────
#define LORA_FREQUENCY    915E6   // 915 MHz (US). Use 868E6 for EU.
#define LORA_BANDWIDTH    125E3
#define LORA_SPREADING    7
#define LORA_CODING_RATE  5
#define LORA_SYNC_WORD    0xAB    // private network sync word
#define LORA_TX_POWER     14      // dBm

// ── Serial config ─────────────────────────────────────────────────────────────
#define SERIAL_BAUD       115200

// ── OLED display ──────────────────────────────────────────────────────────────
SSD1306Wire display(0x3c, 500000, SDA_OLED, SCL_OLED, GEOMETRY_128_64, RST_OLED);

int packetCount = 0;

void setupDisplay() {
  display.init();
  display.setFont(ArialMT_Plain_10);
  display.clear();
  display.drawString(0, 0, "Gateway ready");
  display.display();
}

void updateDisplay(const String& lastMsg, int rssi) {
  display.clear();
  display.drawString(0, 0,  "Gateway [RX: " + String(packetCount) + "]");
  display.drawString(0, 14, "RSSI: " + String(rssi) + " dBm");
  display.drawString(0, 28, lastMsg.substring(0, 21));
  display.display();
}

void setup() {
  Serial.begin(SERIAL_BAUD);

  Mcu.begin();
  setupDisplay();

  LoRa.begin(LORA_FREQUENCY);
  LoRa.setSpreadingFactor(LORA_SPREADING);
  LoRa.setSignalBandwidth(LORA_BANDWIDTH);
  LoRa.setCodingRate4(LORA_CODING_RATE);
  LoRa.setSyncWord(LORA_SYNC_WORD);
  LoRa.setTxPower(LORA_TX_POWER);
  LoRa.enableCrc();

  Serial.println("{\"status\":\"gateway_ready\"}");
}

void loop() {
  // ── Receive LoRa → forward to Pi over serial ────────────────────────────────
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String incoming = "";
    while (LoRa.available()) {
      incoming += (char)LoRa.read();
    }
    int rssi = LoRa.packetRssi();
    float snr  = LoRa.packetSnr();
    packetCount++;

    // Forward as JSON so the Pi can parse it easily
    String json = "{\"type\":\"rx\",\"payload\":\"" + incoming
                + "\",\"rssi\":" + String(rssi)
                + ",\"snr\":" + String(snr, 1) + "}";
    Serial.println(json);
    updateDisplay(incoming, rssi);
  }

  // ── Receive Pi serial command → broadcast over LoRa ────────────────────────
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() > 0) {
      LoRa.beginPacket();
      LoRa.print(cmd);
      LoRa.endPacket();
      Serial.println("{\"type\":\"tx\",\"payload\":\"" + cmd + "\"}");
    }
  }
}
