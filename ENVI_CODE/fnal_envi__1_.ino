/*
 * ═══════════════════════════════════════════════════════════════════════
 *  ENV NODE  —  Environment Sensor Station
 * ═══════════════════════════════════════════════════════════════════════
 *  Sensors:
 *    DHT22   — temperature & humidity  (pin 14)
 *    MQ gas  — analog + digital        (pins 32, 35)
 *    Flood   — analog water sensor     (pin 34)
 *    EQ      — vibration + button      (pins 13, 33)
 *
 *  Connects to HQ_Network WiFi AP and sends telemetry
 *  every 1000 ms to HQ (192.168.4.1 : 4210).
 *
 *  Message format:
 *    T:<temp>,H:<hum>,G:<gas>,F:<flood>,EQ:<0|1>,STATE:<STATE>
 *
 *  States (priority order):
 *    QUAKE  — earthquake detected (overrides all)
 *    ALL    — gas + heat + flood simultaneously
 *    GAS    — gas above threshold
 *    HEAT   — temperature above 45 °C
 *    FLOOD  — water level above threshold
 *    SAFE   — no hazard
 * ═══════════════════════════════════════════════════════════════════════
 */

#include <WiFi.h>
#include <WiFiUdp.h>
#include "DHT.h"

// ─── WiFi ────────────────────────────────────────────────────────────────────
const char* ssid     = "HQ_Network";
const char* password = "12345678";

// ─── UDP ─────────────────────────────────────────────────────────────────────
WiFiUDP    udp;
const char* hqIP    = "192.168.4.1";
const int   udpPort = 4210;

// ─── MQ Gas Sensor ───────────────────────────────────────────────────────────
#define MQ_ANA_PIN  32
#define MQ_DIG_PIN  35
#define GAS_TH      2000

// ─── Flood / Water Sensor ────────────────────────────────────────────────────
#define FLOOD_ANA_PIN 34
#define FLOOD_TH      2000

// ─── DHT22 Temperature & Humidity ────────────────────────────────────────────
#define DHTPIN   14
#define DHTTYPE  DHT22
DHT dht(DHTPIN, DHTTYPE);
#define TEMP_TH  45.0f

// ─── Earthquake Detection ────────────────────────────────────────────────────
#define BUTTON_PIN 33   // manual test button (active LOW)
#define VIB_PIN    13   // SW-420 vibration sensor

// ─────────────────────────────────────────────────────────────────────────────
//  SETUP
// ─────────────────────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);

  pinMode(MQ_DIG_PIN,  INPUT);
  pinMode(FLOOD_ANA_PIN, INPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(VIB_PIN,    INPUT);

  dht.begin();

  // Connect to HQ Access Point
  WiFi.begin(ssid, password);
  Serial.print("Connecting to HQ_Network");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nENV node connected! IP: " + WiFi.localIP().toString());
  udp.begin(udpPort);
  Serial.println("--- ENV NODE READY ---");
}

// ─────────────────────────────────────────────────────────────────────────────
//  MAIN LOOP
// ─────────────────────────────────────────────────────────────────────────────

void loop() {

  // ── Read all sensors ──────────────────────────────────────────────────────

  // Gas
  int  gasAna    = analogRead(MQ_ANA_PIN);
  int  gasDig    = digitalRead(MQ_DIG_PIN);
  bool gasDanger = (gasAna > GAS_TH || gasDig == LOW);

  // Temperature / Humidity
  float temp = dht.readTemperature();
  float hum  = dht.readHumidity();
  bool  heatDanger = (!isnan(temp) && temp > TEMP_TH);

  // Flood
  int  floodAna   = analogRead(FLOOD_ANA_PIN);
  bool floodDanger = (floodAna > FLOOD_TH);

  // Earthquake (button OR vibration sensor)
  bool buttonEQ    = (digitalRead(BUTTON_PIN) == LOW);
  bool vibEQ       = (digitalRead(VIB_PIN)    == LOW);
  bool eqDanger    = buttonEQ || vibEQ;

  // ── Determine system state (priority order) ───────────────────────────────
  String state;
  if      (eqDanger)                              state = "QUAKE";
  else if (gasDanger && heatDanger && floodDanger) state = "ALL";
  else if (gasDanger)                             state = "GAS";
  else if (heatDanger)                            state = "HEAT";
  else if (floodDanger)                           state = "FLOOD";
  else                                            state = "SAFE";

  // ── Build and send UDP message ────────────────────────────────────────────
  char msg[180];
  snprintf(msg, sizeof(msg),
           "T:%.1f,H:%.1f,G:%d,F:%d,EQ:%d,STATE:%s",
           isnan(temp) ? 0.0f : temp,
           isnan(hum)  ? 0.0f : hum,
           gasAna,
           floodAna,
           eqDanger ? 1 : 0,
           state.c_str());

  udp.beginPacket(hqIP, udpPort);
  udp.write((uint8_t*)msg, strlen(msg));
  udp.endPacket();

  Serial.println(msg);

  delay(1000);
}
