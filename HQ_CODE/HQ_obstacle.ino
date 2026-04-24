/*
 * ═══════════════════════════════════════════════════════════════════════
 *  HQ NODE — Single Port 4210 Edition
 * ═══════════════════════════════════════════════════════════════════════
 *  All traffic flows through port 4210 only.
 *
 *  Receives on 4210:
 *    FROM GUI : START | STOP | REVERSE  → forward to Car + apply actuators
 *    FROM ENV : T:x,H:x,G:x,F:x,EQ:x,STATE:x → forward to GUI
 *    FROM CAR : ENC:L:x,R:x,DIST:x,STATE:x   → forward to GUI
 *
 *  Sends on 4210:
 *    TO GUI   : sensor telemetry + encoder data (forwarded)
 *    TO CAR   : START | STOP | REVERSE (forwarded from GUI)
 * ═══════════════════════════════════════════════════════════════════════
 */

#include <WiFi.h>
#include <WiFiUdp.h>

// ─── WiFi AP ─────────────────────────────────────────────────────────────────
const char* ssid     = "HQ_Network";
const char* password = "12345678";

// ─── Single UDP port for everything ──────────────────────────────────────────
WiFiUDP    udp;
const int  PORT = 4210;
char       packet[256];

// ─── Known addresses (learned from first packet received) ────────────────────
IPAddress  pcIP;   bool pcKnown  = false;
IPAddress  carIP;  bool carKnown = false;

// ─── Output Pins ─────────────────────────────────────────────────────────────
const int relayPin  = 18;
const int buzzerPin = 25;
const int RED_LED   = 27;
const int B_LED     = 14;

// ─── Sensor State ────────────────────────────────────────────────────────────
float  envTemp = 0, envHum = 0;
int    envGas  = 0, envFlood = 0, envEQ = 0;
String envState = "SAFE";

// ─── Car State ───────────────────────────────────────────────────────────────
long   encLeft = 0, encRight = 0;
float  encDist = 0;
String carState = "IDLE";

// ─── Timers ──────────────────────────────────────────────────────────────────
unsigned long lastSend  = 0;
unsigned long lastPrint = 0;

// ─────────────────────────────────────────────────────────────────────────────
//  ACTUATORS
// ─────────────────────────────────────────────────────────────────────────────
void fanON()    { pinMode(relayPin, OUTPUT); digitalWrite(relayPin, LOW);  }
void fanOFF()   { pinMode(relayPin, INPUT);                                 }
void alarmON()  { ledcWriteTone(buzzerPin, 2500); digitalWrite(RED_LED, HIGH); digitalWrite(B_LED, HIGH); }
void alarmOFF() { ledcWriteTone(buzzerPin, 0);    digitalWrite(RED_LED, LOW);  digitalWrite(B_LED, LOW);  }

void applyActuators() {
  if (envEQ == 1 || envState == "QUAKE") {
    alarmON(); fanOFF();
  } else {
    (envState == "GAS" || envState == "HEAT" || envState == "ALL") ? fanON() : fanOFF();
    (envState != "SAFE") ? alarmON() : alarmOFF();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  SEND HELPERS
// ─────────────────────────────────────────────────────────────────────────────
void sendTo(IPAddress ip, const char* msg) {
  udp.beginPacket(ip, PORT);
  udp.print(msg);
  udp.endPacket();
}

void sendSensorToGUI() {
  if (!pcKnown) return;
  char msg[180];
  snprintf(msg, sizeof(msg), "T:%.1f,H:%.1f,G:%d,F:%d,EQ:%d,STATE:%s",
           envTemp, envHum, envGas, envFlood, envEQ, envState.c_str());
  sendTo(pcIP, msg);
}

// ─────────────────────────────────────────────────────────────────────────────
//  MESSAGE PARSER
// ─────────────────────────────────────────────────────────────────────────────
void parseMessage(const String& data, IPAddress senderIP) {

  // ── Obstacle alert from Car → forward to GUI ────────────────────────────
  if (data.startsWith("OBSTACLE:")) {
    Serial.print("CAR OBSTACLE → forwarding to GUI: "); Serial.println(data);
    if (pcKnown) sendTo(pcIP, data.c_str());
    return;
  }

  // ── Encoder data from Car → forward to GUI ───────────────────────────────
  if (data.startsWith("ENC:")) {
    carIP    = senderIP;
    carKnown = true;

    int lIdx = data.indexOf("L:");
    int rIdx = data.indexOf("R:");
    int dIdx = data.indexOf("DIST:");
    int sIdx = data.indexOf("STATE:");
    if (lIdx != -1) encLeft  = data.substring(lIdx + 2, data.indexOf(",", lIdx)).toInt();
    if (rIdx != -1) encRight = data.substring(rIdx + 2, data.indexOf(",", rIdx)).toInt();
    if (dIdx != -1) encDist  = data.substring(dIdx + 5, data.indexOf(",", dIdx)).toFloat();
    if (sIdx != -1) { carState = data.substring(sIdx + 6); carState.trim(); }

    if (pcKnown) sendTo(pcIP, data.c_str());   // forward to GUI
    return;
  }

  // ── Commands from GUI → forward to Car ───────────────────────────────────
  if (data == "START" || data == "REVERSE" || data == "STOP") {
    pcIP    = senderIP;
    pcKnown = true;

    if (data == "STOP") { fanOFF(); alarmOFF(); }

    if (carKnown) {
      sendTo(carIP, data.c_str());   // forward command to car
      Serial.print("Forwarded to Car: "); Serial.println(data);
    } else {
      Serial.println("Car not registered yet — command not forwarded");
    }
    return;
  }

  // ── Registration ping from GUI ────────────────────────────────────────────
  if (data == "REGISTER") {
    pcIP    = senderIP;
    pcKnown = true;
    Serial.print("GUI registered: "); Serial.println(pcIP);
    return;
  }

  // ── Car registration ping ─────────────────────────────────────────────────
  if (data.startsWith("CAR_ONLINE")) {
    carIP    = senderIP;
    carKnown = true;
    Serial.print("Car registered: "); Serial.println(carIP);
    return;
  }

  // ── Sensor telemetry from ENV → parse + forward to GUI ───────────────────
  int t = data.indexOf("T:");
  int h = data.indexOf("H:");
  int g = data.indexOf("G:");
  int f = data.indexOf("F:");
  int e = data.indexOf("EQ:");
  int s = data.indexOf("STATE:");

  if (t != -1) envTemp  = data.substring(t + 2, data.indexOf(",", t)).toFloat();
  if (h != -1) envHum   = data.substring(h + 2, data.indexOf(",", h)).toFloat();
  if (g != -1) envGas   = data.substring(g + 2, data.indexOf(",", g)).toInt();
  if (f != -1) envFlood = data.substring(f + 2, data.indexOf(",", f)).toInt();
  if (e != -1) envEQ    = data.substring(e + 3, data.indexOf(",", e)).toInt();
  if (s != -1) { envState = data.substring(s + 6); envState.trim(); }

  sendSensorToGUI();   // immediately push updated state to GUI
}

// ─────────────────────────────────────────────────────────────────────────────
//  SETUP
// ─────────────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  pinMode(RED_LED, OUTPUT);
  pinMode(B_LED,   OUTPUT);

  WiFi.softAP(ssid, password);
  udp.begin(PORT);
  ledcAttach(buzzerPin, 2000, 8);
  fanOFF();

  Serial.println("=== HQ NODE READY ===");
  Serial.print("AP IP: "); Serial.println(WiFi.softAPIP());
  Serial.println("All traffic on port 4210");
}

// ─────────────────────────────────────────────────────────────────────────────
//  MAIN LOOP
// ─────────────────────────────────────────────────────────────────────────────
void loop() {

  int sz = udp.parsePacket();
  if (sz) {
    IPAddress senderIP = udp.remoteIP();
    int len = udp.read(packet, sizeof(packet) - 1);
    if (len > 0) packet[len] = '\0';
    String msg = String(packet);
    msg.trim();
    Serial.print("RX ["); Serial.print(senderIP); Serial.print("]: "); Serial.println(msg);
    parseMessage(msg, senderIP);
  }

  applyActuators();

  if (millis() - lastSend > 1500) {
    lastSend = millis();
    sendSensorToGUI();
  }

  if (millis() - lastPrint > 1500) {
    lastPrint = millis();
    Serial.println("\n===== HQ STATUS =====");
    Serial.print("ENV STATE : "); Serial.println(envState);
    Serial.print("Temp/Hum  : "); Serial.print(envTemp); Serial.print(" / "); Serial.println(envHum);
    Serial.print("Gas/Flood : "); Serial.print(envGas);  Serial.print(" / "); Serial.println(envFlood);
    Serial.print("EQ        : "); Serial.println(envEQ);
    Serial.print("Car State : "); Serial.println(carState);
    Serial.print("Dist      : "); Serial.print(encDist); Serial.println(" cm");
    Serial.print("GUI IP    : "); Serial.println(pcKnown  ? pcIP.toString()  : "not registered");
    Serial.print("Car IP    : "); Serial.println(carKnown ? carIP.toString() : "not registered");
  }
}
