/*
 * heltec_field.ino
 * Heltec LoRa 32 #2 — Field Node
 *
 * Paired with the Flipper Zero over UART (Serial1).
 * Receives messages/commands from the Flipper and sends them over LoRa
 * to the gateway (Heltec #1) → Raspberry Pi.
 *
 * Also receives LoRa packets from the gateway and forwards
 * them to the Flipper over UART.
 *
 * Board: Heltec WiFi LoRa 32 V3
 * Library: Heltec ESP32 (https://github.com/HelTecAutomation/Heltec_ESP32)
 */

#include "LoRaWan_APP.h"
#include "HT_SSD1306Wire.h"

// ── LoRa config — must match heltec_gateway.ino ───────────────────────────────
#define LORA_FREQUENCY    915E6
#define LORA_BANDWIDTH    125E3
#define LORA_SPREADING    7
#define LORA_CODING_RATE  5
#define LORA_SYNC_WORD    0xAB
#define LORA_TX_POWER     14

// ── UART to Flipper Zero ───────────────────────────────────────────────────────
// Flipper Pin 13 (TX) → Heltec GPIO 5 (RX1)
// Flipper Pin 14 (RX) → Heltec GPIO 6 (TX1)
#define FLIPPER_RX_PIN  5
#define FLIPPER_TX_PIN  6
#define FLIPPER_BAUD    115200

// ── OLED ──────────────────────────────────────────────────────────────────────
SSD1306Wire display(0x3c, 500000, SDA_OLED, SCL_OLED, GEOMETRY_128_64, RST_OLED);

int txCount = 0;
int rxCount = 0;

void setupDisplay() {
  display.init();
  display.setFont(ArialMT_Plain_10);
  display.clear();
  display.drawString(0, 0, "Field node ready");
  display.display();
}

void updateDisplay(String status) {
  display.clear();
  display.drawString(0, 0,  "Field node");
  display.drawString(0, 14, "TX: " + String(txCount) + "  RX: " + String(rxCount));
  display.drawString(0, 28, status.substring(0, 21));
  display.display();
}

void setup() {
  Serial.begin(115200);   // USB debug

  // UART to Flipper
  Serial1.begin(FLIPPER_BAUD, SERIAL_8N1, FLIPPER_RX_PIN, FLIPPER_TX_PIN);

  Mcu.begin();
  setupDisplay();

  LoRa.begin(LORA_FREQUENCY);
  LoRa.setSpreadingFactor(LORA_SPREADING);
  LoRa.setSignalBandwidth(LORA_BANDWIDTH);
  LoRa.setCodingRate4(LORA_CODING_RATE);
  LoRa.setSyncWord(LORA_SYNC_WORD);
  LoRa.setTxPower(LORA_TX_POWER);
  LoRa.enableCrc();

  Serial1.println("{\"status\":\"field_ready\"}");
  updateDisplay("Ready");
}

void loop() {
  // ── Flipper → LoRa → Gateway ────────────────────────────────────────────────
  if (Serial1.available()) {
    String msg = Serial1.readStringUntil('\n');
    msg.trim();
    if (msg.length() > 0) {
      LoRa.beginPacket();
      LoRa.print(msg);
      LoRa.endPacket();
      txCount++;
      updateDisplay("TX: " + msg.substring(0, 16));
      Serial.println("[TX] " + msg);
    }
  }

  // ── Gateway → LoRa → Flipper ────────────────────────────────────────────────
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String incoming = "";
    while (LoRa.available()) {
      incoming += (char)LoRa.read();
    }
    int rssi = LoRa.packetRssi();
    rxCount++;

    // Forward to Flipper over UART
    String json = "{\"type\":\"rx\",\"payload\":\"" + incoming
                + "\",\"rssi\":" + String(rssi) + "}";
    Serial1.println(json);
    updateDisplay("RX: " + incoming.substring(0, 16));
    Serial.println("[RX] " + json);
  }
}
