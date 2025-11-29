#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ================== USER CONFIG ==================
const char* WIFI_SSID     = "YOUR_WIFI_SSID";      // TODO: set your WiFi SSID
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";  // TODO: set your WiFi password

// Gas sensor threshold for local buzzer alarm (0-4095)
// Python code currently uses ~300 as email threshold; calibrate as needed.
const int GAS_ALERT_THRESHOLD = 300;
// =================================================

// ========== PIN DEFINITIONS (ESP32 DevKit v1) ==========
const int RELAY_LIGHT_PIN = 25;   // Relay channel for LED light
const int RELAY_FAN_PIN   = 26;   // Relay channel for fan
const int BUZZER_PIN      = 4;    // Active buzzer
const int GAS_SENSOR_PIN  = 34;   // MQ gas sensor analog output (ADC1)
const int PIR_PIN         = 27;   // PIR motion sensor digital output

// I2C LCD (commonly 0x27 or 0x3F)
LiquidCrystal_I2C lcd(0x27, 16, 2);

// Relay logic (many relay modules are active LOW)
const int RELAY_ON  = LOW;
const int RELAY_OFF = HIGH;

// ========== GLOBAL STATE ==========
WebServer server(80);

bool lightOn = false;
bool fanOn   = false;

int  gasValue        = 0;
bool motionDetected  = false;

unsigned long lastSensorRead = 0;
const unsigned long SENSOR_READ_INTERVAL_MS = 200;  // 5 Hz

// ========== HELPERS ==========

void updateRelays() {
  digitalWrite(RELAY_LIGHT_PIN, lightOn ? RELAY_ON : RELAY_OFF);
  digitalWrite(RELAY_FAN_PIN,   fanOn   ? RELAY_ON : RELAY_OFF);
}

void updateLCD(const String &line1, const String &line2) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(line1);
  lcd.setCursor(0, 1);
  lcd.print(line2);
}

void readSensors() {
  gasValue = analogRead(GAS_SENSOR_PIN);
  motionDetected = (digitalRead(PIR_PIN) == HIGH);

  // Local buzzer alarm based on gas threshold
  if (gasValue >= GAS_ALERT_THRESHOLD) {
    digitalWrite(BUZZER_PIN, HIGH);
  } else {
    digitalWrite(BUZZER_PIN, LOW);
  }
}

// ========== HTTP HANDLERS ==========

// Format expected by existing Python code:
// "Gas:123|Motion:Detected|Light:ON|Fan:OFF"
void handleStatus() {
  // Ensure sensors are fresh enough
  unsigned long now = millis();
  if (now - lastSensorRead > SENSOR_READ_INTERVAL_MS) {
    readSensors();
    lastSensorRead = now;
  }

  String status = "Gas:" + String(gasValue) + "|";
  status += "Motion:" + String(motionDetected ? "Detected" : "None") + "|";
  status += "Light:" + String(lightOn ? "ON" : "OFF") + "|";
  status += "Fan:"   + String(fanOn   ? "ON" : "OFF");

  server.send(200, "text/plain", status);
}

void handleLightOn() {
  lightOn = true;
  updateRelays();
  updateLCD("Light: ON", "Fan: " + String(fanOn ? "ON" : "OFF"));
  server.send(200, "text/plain", "LIGHT ON");
}

void handleLightOff() {
  lightOn = false;
  updateRelays();
  updateLCD("Light: OFF", "Fan: " + String(fanOn ? "ON" : "OFF"));
  server.send(200, "text/plain", "LIGHT OFF");
}

void handleFanOn() {
  fanOn = true;
  updateRelays();
  updateLCD("Light: " + String(lightOn ? "ON" : "OFF"), "Fan: ON");
  server.send(200, "text/plain", "FAN ON");
}

void handleFanOff() {
  fanOn = false;
  updateRelays();
  updateLCD("Light: " + String(lightOn ? "ON" : "OFF"), "Fan: OFF");
  server.send(200, "text/plain", "FAN OFF");
}

void handleRoot() {
  String html = "<!DOCTYPE html><html><head><title>RoomMate ESP32</title></head><body>";
  html += "<h1>RoomMate ESP32</h1>";
  html += "<p>Endpoints:</p><ul>";
  html += "<li>/status</li>";
  html += "<li>/light/on</li>";
  html += "<li>/light/off</li>";
  html += "<li>/fan/on</li>";
  html += "<li>/fan/off</li>";
  html += "</ul></body></html>";
  server.send(200, "text/html", html);
}

// ========== WIFI ==========

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting to WiFi");
  updateLCD("Connecting WiFi", "...");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("Connected! IP: ");
  Serial.println(WiFi.localIP());

  updateLCD("WiFi Connected", WiFi.localIP().toString());
}

// ========== SETUP / LOOP ==========

void setup() {
  Serial.begin(115200);

  pinMode(RELAY_LIGHT_PIN, OUTPUT);
  pinMode(RELAY_FAN_PIN,   OUTPUT);
  pinMode(BUZZER_PIN,      OUTPUT);
  pinMode(GAS_SENSOR_PIN,  INPUT);
  pinMode(PIR_PIN,         INPUT);

  lightOn = false;
  fanOn   = false;
  updateRelays();
  digitalWrite(BUZZER_PIN, LOW);

  Wire.begin(21, 22); // SDA, SCL for ESP32 DevKit v1
  lcd.init();
  lcd.backlight();
  updateLCD("RoomMate ESP32", "Starting...");

  connectWiFi();

  // HTTP routes matching existing Python code
  server.on("/", HTTP_GET, handleRoot);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/light/on", HTTP_GET, handleLightOn);
  server.on("/light/off", HTTP_GET, handleLightOff);
  server.on("/fan/on", HTTP_GET, handleFanOn);
  server.on("/fan/off", HTTP_GET, handleFanOff);

  server.begin();
  Serial.println("HTTP server started");
  updateLCD("System Ready", "Waiting...");
}

void loop() {
  server.handleClient();

  unsigned long now = millis();
  if (now - lastSensorRead >= SENSOR_READ_INTERVAL_MS) {
    readSensors();
    lastSensorRead = now;
  }
}
