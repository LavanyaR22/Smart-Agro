/*
 * ==================================================================================
 * AGRI Smart Irrigation - ESP32 Sensor Test Firmware
 * Board Target: ESP32 Dev Module (30-pin or 38-pin) / NodeMCU-32S
 *
 * Hardware Pin Connections:
 *   - DHT22 (Temp & Humidity):   DATA -> GPIO 4 (3.3V VCC, GND)
 *   - Capacitive Soil Sensor:    AOUT -> GPIO 34 (ADC1, 3.3V VCC, GND)
 *   - Relay Pin (Reserved):      GPIO 23 (DISABLED for safety during this test)
 *
 * Serial Monitor Baud Rate: 115200
 * ==================================================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <ArduinoJson.h> // Supports ArduinoJson v6 and v7

// ==================================================================================
// [CONFIGURATION SECTION]
// ==================================================================================

// Wi-Fi Telemetry Configuration:
// Set to true to stream real sensor data to the AGRI backend over HTTP.
const bool ENABLE_WIFI_TELEMETRY = true;

// Wi-Fi Credentials (Used when ENABLE_WIFI_TELEMETRY is true)
// Replace placeholders with your 2.4 GHz Wi-Fi credentials before uploading:
const char* WIFI_SSID = "Abdul hafeel’s iPhone";             // <-- Enter your 2.4 GHz Wi-Fi SSID
const char* WIFI_PASSWORD = "hafeel2234";     // <-- Enter your Wi-Fi password

// Backend API Endpoint (Used when ENABLE_WIFI_TELEMETRY is true)
// Target laptop's local LAN IPv4 address (port 8000).
// Current active Wi-Fi IPv4 address: 172.20.10.2 (verify using 'ipconfig' if changed).
const char* BACKEND_URL = "http://172.20.10.2:8000/api/telemetry";

// Stable hardware device identifier sent to the backend
const char* DEVICE_ID = "ESP32_FIELD_NODE_01";

// ==================================================================================
// [HARDWARE PIN DEFINITIONS]
// ==================================================================================

#define DHTPIN 4
#define DHTTYPE DHT22
#define SOIL_PIN 34

// Relay control
#define RELAY_PIN 23

// Most single-channel relay modules are active LOW.
// Keep relay control disabled until the test is explicitly enabled.
const bool ENABLE_RELAY_CONTROL = false;
const int RELAY_ON = LOW;
const int RELAY_OFF = HIGH;

// ==================================================================================
// [SOIL SENSOR CALIBRATION CONSTANTS]
// ==================================================================================
// Use the raw ADC readings from the Serial Monitor diagnostic to determine your values:
//   1. Hold probe in dry air              -> record raw ADC as AIR_VALUE  (typ. ~2800 to 3500)
//   2. Submerge up to white line in water -> record raw ADC as WATER_VALUE (typ. ~1200 to 1600)
const int PROVISIONAL_AIR_VALUE = 3200;    // Provisional baseline only
const int PROVISIONAL_WATER_VALUE = 1400;  // Provisional baseline only

// Safe sample interval: DHT22 physical hardware requires at least 2000 ms between reads.
const unsigned long SENSOR_READ_INTERVAL_MS = 2500;

DHT dht(DHTPIN, DHTTYPE);

// Cache variables for telemetry fallback when Wi-Fi is enabled
float lastValidTemperature = 0.0;
float lastValidHumidity = 0.0;
bool hasValidDHT = false;

// Forward declaration
void sendTelemetry(float temp, float hum, int rawSoilADC);

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n==================================================");
  Serial.println("  AGRI SMART IRRIGATION - SENSOR DIAGNOSTIC MODE");
  Serial.println("==================================================");

  // Safety: Keep the pump relay strictly de-energized during boot
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, RELAY_OFF);

  Serial.println("[Safety] Pump relay control is DISABLED.");
  Serial.printf("[Mode] Telemetry: %s\n",
                ENABLE_WIFI_TELEMETRY ? "Wi-Fi Enabled" : "Standalone Diagnostic (Serial Monitor Only)");
  Serial.println("[Sampling] Safe interval: 2.5 seconds (prevents sensor jitter)");

  // Initialize DHT22
  dht.begin();

  // Configure ADC resolution for ESP32 (12-bit: values 0 to 4095)
  analogReadResolution(12);

  // Initialize Wi-Fi only if explicitly enabled
  if (ENABLE_WIFI_TELEMETRY) {
    if (String(WIFI_SSID) == "YOUR_WIFI_SSID") {
      Serial.println("[WiFi Warning] Placeholder credentials detected. Skipping Wi-Fi.");
    } else {
      Serial.print("[WiFi] Connecting to: ");
      Serial.println(WIFI_SSID);
      WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

      int attempts = 0;
      while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
      }

      if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n[WiFi] Connected successfully!");
        Serial.print("[WiFi] ESP32 IP Address: ");
        Serial.println(WiFi.localIP());
      } else {
        Serial.println("\n[WiFi] Connection timed out. Running in offline/debug mode.");
      }
    }
  }

  Serial.println("\nStarting 2.5-second diagnostic sensor sampling...\n");
}

void loop() {
  // 1. Read DHT22 values
  float rawHum = dht.readHumidity();
  float rawTemp = dht.readTemperature();
  bool dhtReadSuccess = (!isnan(rawHum) && !isnan(rawTemp));

  if (dhtReadSuccess) {
    lastValidHumidity = rawHum;
    lastValidTemperature = rawTemp;
    hasValidDHT = true;
  }

  // 2. Read Capacitive Soil Moisture Sensor (Analog ADC on GPIO 34)
  int rawSoilADC = analogRead(SOIL_PIN);

  // 3. Print diagnostic results to Serial Monitor at 115200 baud
  Serial.println("--------------------------------------------------");
  if (dhtReadSuccess) {
    Serial.printf("  [DHT22] Temperature     : %.1f °C\n", rawTemp);
    Serial.printf("  [DHT22] Relative Humidity: %.1f %%\n", rawHum);
  } else {
    Serial.println("  [DHT22 ERROR] Reading failed (NaN returned)!");
    Serial.println("    -> Check VCC (3.3V), GND, and GPIO 4 connection.");
  }

  Serial.printf("  [SOIL]  Raw ADC (GPIO 34): %d (Valid range: 0 - 4095)\n", rawSoilADC);
  if (rawSoilADC >= 4000) {
    Serial.println("  [SOIL NOTICE] ADC near maximum - probe is in dry air or wire disconnected.");
  } else if (rawSoilADC <= 100) {
    Serial.println("  [SOIL NOTICE] ADC near zero - check for short to ground.");
  } else {
    Serial.println("  [SOIL STATUS] Analog signal detected. Record this value for calibration.");
  }
  Serial.println("--------------------------------------------------");

  // 4. HTTP Telemetry (stream to AGRI backend when Wi-Fi is enabled)
  if (ENABLE_WIFI_TELEMETRY) {
    if (WiFi.status() != WL_CONNECTED) {
      if (String(WIFI_SSID) != "YOUR_WIFI_SSID") {
        Serial.println("[WiFi] Wi-Fi disconnected. Reconnecting...");
        WiFi.disconnect();
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
      }
    } else {
      if (hasValidDHT) {
        sendTelemetry(lastValidTemperature, lastValidHumidity, rawSoilADC);
      } else {
        Serial.println("[HTTP] Awaiting first valid DHT22 reading before transmitting telemetry...");
      }
    }
  }

  delay(SENSOR_READ_INTERVAL_MS);
}

void sendTelemetry(float temp, float hum, int rawSoilADC) {
  HTTPClient http;
  if (!http.begin(BACKEND_URL)) {
    Serial.println("[HTTP] Failed to initialize connection to backend URL.");
    return;
  }

  http.addHeader("Content-Type", "application/json");

  // Construct JSON payload (compatible with ArduinoJson v6 and v7)
#if ARDUINOJSON_VERSION_MAJOR >= 7
  JsonDocument doc;
#else
  StaticJsonDocument<256> doc;
#endif

  // Requirement 4 & 5:
  // - Send actual DHT22 temperature and humidity
  // - Raw soil ADC reading directly (0 - 4095)
  // - soil_moisture: null (calibration is unconfirmed; never invent fake percentage)
  // - source: "hardware"
  // - device_id: stable hardware node identifier
  doc["temperature"] = round(temp * 10.0f) / 10.0f;
  doc["humidity"] = round(hum * 10.0f) / 10.0f;
  doc["soil_moisture"] = nullptr;
  doc["raw_soil_adc"] = rawSoilADC;
  doc["device_id"] = DEVICE_ID;
  doc["source"] = "hardware";

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  int httpResponseCode = http.POST(jsonPayload);
  if (httpResponseCode > 0) {
    Serial.printf("[HTTP] Telemetry POST response code: %d -> Ingested by backend!\n", httpResponseCode);
  } else {
    Serial.printf("[HTTP] POST failed, error: %s (Check if PC backend is accessible at %s)\n",
                  http.errorToString(httpResponseCode).c_str(), BACKEND_URL);
  }
  http.end();
}

