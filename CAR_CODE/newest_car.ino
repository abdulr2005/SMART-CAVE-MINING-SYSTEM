/*
 * ═══════════════════════════════════════════════════════════════════════
 *  CAR NODE — Single Port 4210 Edition  (IR Debounce Fix)
 * ═══════════════════════════════════════════════════════════════════════
 *  FIX: IR sensor debounce added to prevent false steerLeft/steerRight
 *       calls caused by sensor flicker during forward motion
 * ═══════════════════════════════════════════════════════════════════════
 */

#include <WiFi.h>
#include <WiFiUdp.h>

// ─── WiFi ────────────────────────────────────────────────────────────────────
const char* ssid     = "HQ_Network";
const char* password = "12345678";

// ─── Single port ─────────────────────────────────────────────────────────────
WiFiUDP    udp;
const int  PORT = 4210;
char       rxBuf[180];

// HQ is always 192.168.4.1
IPAddress  hqIP(192, 168, 4, 1);

// ─── Motor Pins ──────────────────────────────────────────────────────────────
const int motor1Pin1 = 27; const int motor1Pin2 = 26; const int enable1Pin = 14;
const int motor2Pin1 = 25; const int motor2Pin2 = 33; const int enable2Pin = 32;

// ─── IR Sensor Pins ──────────────────────────────────────────────────────────
const int F_Left  =  4;  const int F_Right =  5;
const int R_Left  = 18;  const int R_Right = 19;

// ─── Encoder Pins ────────────────────────────────────────────────────────────
const int encLeftPin  = 16;
const int encRightPin = 17;

volatile long leftPulses  = 0;
volatile long rightPulses = 0;

const float WHEEL_DIAM     = 3.5f;
const int   PULSES_PER_REV = 74;

// ─── Ultrasonic ──────────────────────────────────────────────────────────────
const int trigPin      = 12;
const int echoPin      = 13;
const int STOP_DIST_CM = 15;

// ─── PWM ─────────────────────────────────────────────────────────────────────
const int PWM_FREQ = 30000;
const int PWM_RES  = 8;
const int DUTY     = 200;

// ─── State Machine ───────────────────────────────────────────────────────────
enum CarState { IDLE, RUNNING, OBSTACLE_WAIT, REVERSING_STATE };
volatile CarState carState = IDLE;

long fwdPulseTarget = 0;
long snapLeft = 0, snapRight = 0;

unsigned long lastEncSend  = 0;
unsigned long lastAnnounce = 0;

// ─── ISRs ────────────────────────────────────────────────────────────────────
void IRAM_ATTR countLeft()  { leftPulses++;  }
void IRAM_ATTR countRight() { rightPulses++; }

// ─────────────────────────────────────────────────────────────────────────────
//  UTILITY
// ─────────────────────────────────────────────────────────────────────────────
float pulsesToCm(long p) {
  return (p / (float)PULSES_PER_REV) * (3.14159f * WHEEL_DIAM);
}

float getUltrasonicDistance() {
  digitalWrite(trigPin, LOW);  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH); delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  long d = pulseIn(echoPin, HIGH, 30000);
  return (d == 0) ? 999.0f : d * 0.034f / 2.0f;
}

// ─────────────────────────────────────────────────────────────────────────────
//  DEBOUNCED IR READ — reads sensor twice 5ms apart, only acts if stable
// ─────────────────────────────────────────────────────────────────────────────
void readFrontSensors(int &fl, int &fr) {
  // First read
  int fl1 = digitalRead(F_Left);
  int fr1 = digitalRead(F_Right);

  delay(5); // wait 5ms

  // Second read
  int fl2 = digitalRead(F_Left);
  int fr2 = digitalRead(F_Right);

  // Only accept reading if it is stable across both samples
  // If unstable, fall back to HIGH (on-line) to prefer going straight
  fl = (fl1 == fl2) ? fl1 : HIGH;
  fr = (fr1 == fr2) ? fr1 : HIGH;
}

void readRearSensors(int &rl, int &rr) {
  int rl1 = digitalRead(R_Left);
  int rr1 = digitalRead(R_Right);

  delay(5);

  int rl2 = digitalRead(R_Left);
  int rr2 = digitalRead(R_Right);

  rl = (rl1 == rl2) ? rl1 : HIGH;
  rr = (rr1 == rr2) ? rr1 : HIGH;
}

// ─────────────────────────────────────────────────────────────────────────────
//  ANNOUNCE TO HQ
// ─────────────────────────────────────────────────────────────────────────────
void announceToHQ() {
  udp.beginPacket(hqIP, PORT);
  udp.print("CAR_ONLINE");
  udp.endPacket();
  Serial.println("Announced to HQ");
}

// ─────────────────────────────────────────────────────────────────────────────
//  ENCODER BROADCAST → HQ
// ─────────────────────────────────────────────────────────────────────────────
void sendEncoderData() {
  long  avg  = (leftPulses + rightPulses) / 2;
  float dist = pulsesToCm(avg);
  const char* st = (carState == RUNNING)         ? "FWD"
                 : (carState == REVERSING_STATE)  ? "REV"
                 : (carState == OBSTACLE_WAIT)    ? "BLOCKED"
                 :                                  "IDLE";
  char msg[180];
  snprintf(msg, sizeof(msg), "ENC:L:%ld,R:%ld,DIST:%.1f,STATE:%s",
           leftPulses, rightPulses, dist, st);
  udp.beginPacket(hqIP, PORT);
  udp.print(msg);
  udp.endPacket();
  Serial.print("TX → HQ: "); Serial.println(msg);
}

// ─────────────────────────────────────────────────────────────────────────────
//  OBSTACLE ALERT → HQ
// ─────────────────────────────────────────────────────────────────────────────
void sendObstacleAlert(float dist) {
  char msg[80];
  snprintf(msg, sizeof(msg), "OBSTACLE:%.1f", dist);
  udp.beginPacket(hqIP, PORT);
  udp.print(msg);
  udp.endPacket();
  Serial.print("TX OBSTACLE → HQ: "); Serial.println(msg);
}

// ─────────────────────────────────────────────────────────────────────────────
//  MOTION PRIMITIVES
// ─────────────────────────────────────────────────────────────────────────────
void moveForward() {
  digitalWrite(motor1Pin1, HIGH);
  digitalWrite(motor1Pin2, LOW);
  digitalWrite(motor2Pin1, HIGH);
  digitalWrite(motor2Pin2, LOW);
}

void moveBackward() {
  digitalWrite(motor1Pin1, LOW);
  digitalWrite(motor1Pin2, HIGH);
  digitalWrite(motor2Pin1, LOW);
  digitalWrite(motor2Pin2, HIGH);
}

void steerLeft() {
  digitalWrite(motor1Pin1, LOW);
  digitalWrite(motor1Pin2, LOW);
  digitalWrite(motor2Pin1, HIGH);
  digitalWrite(motor2Pin2, LOW);
}

void steerRight() {
  digitalWrite(motor1Pin1, HIGH);
  digitalWrite(motor1Pin2, LOW);
  digitalWrite(motor2Pin1, LOW);
  digitalWrite(motor2Pin2, LOW);
}

void revSteerLeft() {
  digitalWrite(motor1Pin1, LOW);
  digitalWrite(motor1Pin2, HIGH);
  digitalWrite(motor2Pin1, LOW);
  digitalWrite(motor2Pin2, LOW);
}

void revSteerRight() {
  digitalWrite(motor1Pin1, LOW);
  digitalWrite(motor1Pin2, LOW);
  digitalWrite(motor2Pin1, LOW);
  digitalWrite(motor2Pin2, HIGH);
}

void stopMotors() {
  digitalWrite(motor1Pin1, LOW); digitalWrite(motor1Pin2, LOW);
  digitalWrite(motor2Pin1, LOW); digitalWrite(motor2Pin2, LOW);
}

// ─────────────────────────────────────────────────────────────────────────────
//  UDP COMMAND HANDLER
// ─────────────────────────────────────────────────────────────────────────────
void checkUDP() {
  int sz = udp.parsePacket();
  if (!sz) return;

  int len = udp.read(rxBuf, sizeof(rxBuf) - 1);
  if (len <= 0) return;
  rxBuf[len] = '\0';

  String cmd = String(rxBuf);
  cmd.trim();
  Serial.print("RX CMD: "); Serial.println(cmd);

  if (cmd == "START") {
    leftPulses = rightPulses = 0;
    fwdPulseTarget = 0;
    carState = RUNNING;
    Serial.println("→ RUNNING");
    sendEncoderData();
  }
  else if (cmd == "REVERSE") {
    fwdPulseTarget = (leftPulses + rightPulses) / 2;
    snapLeft  = leftPulses;
    snapRight = rightPulses;
    carState  = REVERSING_STATE;
    Serial.print("→ REVERSING  target = "); Serial.println(fwdPulseTarget);
    sendEncoderData();
  }
  else if (cmd == "STOP") {
    stopMotors();
    carState = IDLE;
    Serial.println("→ IDLE");
    sendEncoderData();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  SETUP
// ─────────────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  pinMode(motor1Pin1, OUTPUT); pinMode(motor1Pin2, OUTPUT); pinMode(enable1Pin, OUTPUT);
  pinMode(motor2Pin1, OUTPUT); pinMode(motor2Pin2, OUTPUT); pinMode(enable2Pin, OUTPUT);
  pinMode(F_Left, INPUT); pinMode(F_Right, INPUT);
  pinMode(R_Left, INPUT); pinMode(R_Right, INPUT);
  pinMode(trigPin, OUTPUT); pinMode(echoPin, INPUT);
  pinMode(encLeftPin,  INPUT_PULLUP);
  pinMode(encRightPin, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(encLeftPin),  countLeft,  FALLING);
  attachInterrupt(digitalPinToInterrupt(encRightPin), countRight, FALLING);

  ledcAttach(enable1Pin, PWM_FREQ, PWM_RES);
  ledcAttach(enable2Pin, PWM_FREQ, PWM_RES);
  ledcWrite(enable1Pin, DUTY);
  ledcWrite(enable2Pin, DUTY);

  WiFi.begin(ssid, password);
  Serial.print("Connecting");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\nCar IP: " + WiFi.localIP().toString());

  udp.begin(PORT);
  Serial.println("--- CAR READY (IR Debounce Fix) ---");

  announceToHQ();
  lastAnnounce = millis();
}

// ─────────────────────────────────────────────────────────────────────────────
//  MAIN LOOP
// ─────────────────────────────────────────────────────────────────────────────
void loop() {

  checkUDP();

  if (millis() - lastAnnounce > 5000) {
    lastAnnounce = millis();
    announceToHQ();
  }

  if (carState == IDLE) { stopMotors(); return; }

  // ── REVERSING ─────────────────────────────────────────────────────────────
  if (carState == REVERSING_STATE) {
    long revDone = ((leftPulses - snapLeft) + (rightPulses - snapRight)) / 2;

    if (revDone < fwdPulseTarget) {
      int rl, rr;
      readRearSensors(rl, rr);  // debounced rear sensor read

      if      (rl == HIGH && rr == HIGH) moveBackward();
      else if (rl == HIGH && rr == LOW)  revSteerLeft();
      else if (rl == LOW  && rr == HIGH) revSteerRight();
      else                               moveBackward();
    } else {
      stopMotors();
      carState = IDLE;
      Serial.println("--- RETURNED TO START ---");
      sendEncoderData();
    }

    if (millis() - lastEncSend > 500) { lastEncSend = millis(); sendEncoderData(); }
    delay(20);
    return;
  }

  // ── OBSTACLE_WAIT ─────────────────────────────────────────────────────────
  if (carState == OBSTACLE_WAIT) {
    stopMotors();
    if (millis() - lastEncSend > 2000) {
      lastEncSend = millis();
      sendEncoderData();
    }
    return;
  }

  // ── RUNNING ───────────────────────────────────────────────────────────────
  if (carState == RUNNING) {
    long  avgPulses  = (leftPulses + rightPulses) / 2;
    float distanceCm = pulsesToCm(avgPulses);

    float obsDist = getUltrasonicDistance();
    if (obsDist > 0 && obsDist < STOP_DIST_CM) {
      stopMotors();
      fwdPulseTarget = avgPulses;
      carState = OBSTACLE_WAIT;
      Serial.print("!!! OBSTACLE at "); Serial.print(obsDist); Serial.println(" cm !!!");
      sendObstacleAlert(obsDist);
      return;
    }

    // ── DEBOUNCED IR READ ──────────────────────────────────────────────────
    int fl, fr;
    readFrontSensors(fl, fr);  // reads twice 5ms apart, only uses stable value

    Serial.print("FL:"); Serial.print(fl);
    Serial.print(" FR:"); Serial.print(fr);

    if      (fl == HIGH && fr == HIGH) { Serial.println(" → FORWARD");     moveForward(); }
    else if (fl == HIGH && fr == LOW)  { Serial.println(" → STEER LEFT");  steerLeft();   }
    else if (fl == LOW  && fr == HIGH) { Serial.println(" → STEER RIGHT"); steerRight();  }
    else                               { Serial.println(" → STOP");        stopMotors();  }

    if (millis() - lastEncSend > 500) { lastEncSend = millis(); sendEncoderData(); }
    delay(20);
  }
}