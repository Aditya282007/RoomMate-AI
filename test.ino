// -------------------------
//      ROOMMATE ESP32
//    FINAL CODE + LOGS
// -------------------------

#include <WiFi.h>
#include <WebServer.h>
#include <LiquidCrystal.h>
#include <vector>

// ================== USER CONFIG ==================
const char* WIFI_SSID     = "Meet";
const char* WIFI_PASSWORD = "12345678";

const int GAS_ALERT_THRESHOLD = 300;
const int GAS_HYSTERESIS      = 50;
// =================================================

// Relay pins
const int RELAY_LIGHT_PIN = 25;
const int RELAY_FAN_PIN   = 26;

// Buzzer
const int BUZZER_PIN = 4;

// Sensors
const int GAS_SENSOR_PIN = 34;
const int PIR_PIN        = 27;

// LCD pins
const int LCD_RS = 19;
const int LCD_E  = 23;
const int LCD_D4 = 18;
const int LCD_D5 = 17;
const int LCD_D6 = 16;
const int LCD_D7 = 13;

LiquidCrystal lcd(LCD_RS, LCD_E, LCD_D4, LCD_D5, LCD_D6, LCD_D7);

// Relay logic
const int RELAY_ON  = LOW;
const int RELAY_OFF = HIGH;

WebServer server(80);

bool lightOn = false;
bool fanOn   = false;

int rawGasValue = 0;
float gasSmoothed = 0;
bool gasAlertState = false;

bool motionDetected = false;
bool lastMotionRaw  = false;
unsigned long lastMotionChange = 0;

const unsigned long PIR_DEBOUNCE_MS = 300;
unsigned long lastSensorRead = 0;
const unsigned long SENSOR_READ_INTERVAL_MS = 250;

// Failsafe tracking for light and fan commands
unsigned long lastLightCommandMs = 0;
unsigned long lastFanCommandMs   = 0;
// Max time a device is allowed to stay ON without a new command (here: 60 seconds)
const unsigned long DEVICE_FAILSAFE_MS = 60UL * 1000UL;

// LCD last cache
String lastLine1 = "";
String lastLine2 = "";

// WiFi timeout
const unsigned long WIFI_TIMEOUT_MS = 15000;

// ---------------------- LOG SYSTEM ----------------------

std::vector<String> logs;
const int MAX_LOGS = 100;

String timestamp() {
  return String(millis() / 1000) + "s";
}

void addLog(String msg) {
  String entry = "[" + timestamp() + "] " + msg;
  Serial.println(entry);

  logs.push_back(entry);
  if (logs.size() > MAX_LOGS) logs.erase(logs.begin());
}

// ---------------------------------------------------------

void updateRelays() {
  digitalWrite(RELAY_LIGHT_PIN, lightOn ? RELAY_ON : RELAY_OFF);
  digitalWrite(RELAY_FAN_PIN,   fanOn   ? RELAY_ON : RELAY_OFF);
}

void lcdUpdateIfChanged(const String &l1, const String &l2) {
  if (l1 == lastLine1 && l2 == lastLine2) return;

  lastLine1 = l1;
  lastLine2 = l2;

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(l1);
  lcd.setCursor(0, 1);
  lcd.print(l2);
}

void smoothGas(int raw) {
  const float alpha = 0.12;
  if (gasSmoothed == 0) gasSmoothed = raw;
  else gasSmoothed = alpha * raw + (1 - alpha) * gasSmoothed;
}

void readSensors() {
  rawGasValue = analogRead(GAS_SENSOR_PIN);
  smoothGas(rawGasValue);

  // PIR
  bool pirRaw = (digitalRead(PIR_PIN) == HIGH);
  unsigned long now = millis();

  if (pirRaw != lastMotionRaw) {
    lastMotionRaw = pirRaw;
    lastMotionChange = now;
  } else {
    if (now - lastMotionChange >= PIR_DEBOUNCE_MS) {
      if (motionDetected != pirRaw) {
        motionDetected = pirRaw;
        addLog(String("Motion: ") + (motionDetected ? "DETECTED" : "NO MOTION"));
      }
    }
  }

  // GAS alert hysteresis
  bool prevAlert = gasAlertState;

  if (!gasAlertState) {
    if (gasSmoothed >= GAS_ALERT_THRESHOLD) gasAlertState = true;
  } else {
    if (gasSmoothed < (GAS_ALERT_THRESHOLD - GAS_HYSTERESIS)) gasAlertState = false;
  }

  if (prevAlert != gasAlertState) {
    addLog(String("Gas Alert: ") + (gasAlertState ? "ON" : "OFF"));
  }

  digitalWrite(BUZZER_PIN, gasAlertState ? HIGH : LOW);
}

void sendCORS() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
}

void handleStatus() {
  sendCORS();

  char buffer[100];
  snprintf(buffer, sizeof(buffer), "Gas:%d|Motion:%s|Light:%s|Fan:%s",
    (int)gasSmoothed,
    motionDetected ? "Detected" : "None",
    lightOn ? "ON" : "OFF",
    fanOn ? "ON" : "OFF"
  );

  server.send(200, "text/plain", buffer);

  addLog("Status requested");
}

void handleLightOn() {
  lightOn = true;
  lastLightCommandMs = millis();
  updateRelays();
  lcdUpdateIfChanged("Light: ON", "Fan:" + String(fanOn ? "ON" : "OFF"));
  sendCORS();
  server.send(200, "text/plain", "LIGHT ON");

  addLog("Light turned ON");
}

void handleLightOff() {
  lightOn = false;
  lastLightCommandMs = millis();
  updateRelays();
  lcdUpdateIfChanged("Light: OFF", "Fan:" + String(fanOn ? "ON" : "OFF"));
  sendCORS();
  server.send(200, "text/plain", "LIGHT OFF");

  addLog("Light turned OFF");
}

void handleFanOn() {
  fanOn = true;
  lastFanCommandMs = millis();
  updateRelays();
  lcdUpdateIfChanged("Light:" + String(lightOn ? "ON" : "OFF"), "Fan: ON");
  sendCORS();
  server.send(200, "text/plain", "FAN ON");

  addLog("Fan turned ON");
}

void handleFanOff() {
  fanOn = false;
  lastFanCommandMs = millis();
  updateRelays();
  lcdUpdateIfChanged("Light:" + String(lightOn ? "ON" : "OFF"), "Fan: OFF");
  sendCORS();
  server.send(200, "text/plain", "FAN OFF");

  addLog("Fan turned OFF");
}

void handleLogs() {
  String output = "";
  for (String &l : logs) output += l + "\n";

  sendCORS();
  server.send(200, "text/plain", output);
}

void handleLogsClear() {
  logs.clear();
  addLog("Logs cleared by API");

  sendCORS();
  server.send(200, "text/plain", "LOGS CLEARED");
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  lcdUpdateIfChanged("Connecting WiFi", "");

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(200);
    if (millis() - start > WIFI_TIMEOUT_MS) {
      lcdUpdateIfChanged("WiFi Failed", "");
      addLog("WiFi Connection FAILED");
      return;
    }
  }

  lcdUpdateIfChanged("WiFi OK", WiFi.localIP().toString());
  addLog("WiFi Connected: " + WiFi.localIP().toString());
}

void setup() {
  Serial.begin(115200);

  pinMode(RELAY_LIGHT_PIN, OUTPUT);
  pinMode(RELAY_FAN_PIN,   OUTPUT);
  pinMode(BUZZER_PIN,      OUTPUT);
  pinMode(PIR_PIN,         INPUT);
  pinMode(GAS_SENSOR_PIN,  INPUT);

  lightOn = false;
  fanOn   = false;
  updateRelays();
  lastLightCommandMs = millis();
  lastFanCommandMs   = millis();
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  lcd.begin(16, 2);
  lcdUpdateIfChanged("RoomMate ESP32", "Booting...");

  addLog("System Boot");

  connectWiFi();

  server.on("/status", handleStatus);
  server.on("/light/on", handleLightOn);
  server.on("/light/off", handleLightOff);
  server.on("/fan/on", handleFanOn);
  server.on("/fan/off", handleFanOff);

  // NEW LOG ROUTES
  server.on("/logs", handleLogs);
  server.on("/logs/clear", handleLogsClear);

  server.begin();
  addLog("HTTP Server started");
}

void loop() {
  server.handleClient();

  unsigned long now = millis();
  if (now - lastSensorRead >= SENSOR_READ_INTERVAL_MS) {
    lastSensorRead = now;
    readSensors();

    lcdUpdateIfChanged(
      "Gas:" + String((int)gasSmoothed),
      (motionDetected ? "Motion" : "NoMotion") + String(" L:") + (lightOn ? "ON" : "OFF")
    );
  }

  // Failsafe: auto-turn devices OFF if they stay ON for too long without new commands
  if (lightOn && (now - lastLightCommandMs > DEVICE_FAILSAFE_MS)) {
    lightOn = false;
    updateRelays();
    addLog("Failsafe: Light auto-OFF");
  }

  if (fanOn && (now - lastFanCommandMs > DEVICE_FAILSAFE_MS)) {
    fanOn = false;
    updateRelays();
    addLog("Failsafe: Fan auto-OFF");
  }

  delay(1);
}
