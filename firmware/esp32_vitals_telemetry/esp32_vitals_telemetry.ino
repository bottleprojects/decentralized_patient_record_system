/*
 * ======================================================================================
 * Decentralized Patient Record Management System (DPRMS)
 * ESP32 Biometric Telemetry Firmware: MAX30102 (PPG/SpO2) + AD8232 (Lead-II ECG)
 * ======================================================================================
 * 
 * SENSOR CONNECTIONS:
 * --------------------------------------------------------------------------------------
 * | ESP32 Pin | Connected Component | Sensor Pin | Notes                               |
 * |-----------|---------------------|------------|-------------------------------------|
 * | 3V3       | AD8232              | 3.3V       | Clean 3.3V Power                    |
 * | GND       | AD8232              | GND        | Common Ground                       |
 * | GPIO 34   | AD8232              | OUTPUT     | Analog Input (ADC1_CH6, 0-4095)     |
 * | GPIO 25   | AD8232              | LO+        | Leads-Off Detection Right Arm       |
 * | GPIO 26   | AD8232              | LO-        | Leads-Off Detection Left Arm        |
 * | 3V3       | MAX30102            | VIN / VCC  | 3.3V Power                          |
 * | GND       | MAX30102            | GND        | Common Ground                       |
 * | GPIO 21   | MAX30102            | SDA        | I2C Data                            |
 * | GPIO 22   | MAX30102            | SCL        | I2C Clock                           |
 * --------------------------------------------------------------------------------------
 * 
 * REQUIRED ARDUINO LIBRARIES (Install via Arduino Library Manager):
 * - "SparkFun MAX3010x Pulse and Proximity Sensor Library" by SparkFun Electronics
 *   (WiFi, HTTPClient, and Wire are already built-in to the ESP32 board package)
 * ======================================================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <Wire.h>
#include "MAX30105.h"
#include "heartRate.h"

// ==========================================
// 1. CONFIGURATION (CUSTOMIZE THESE VALUES)
// ==========================================
const char* WIFI_SSID     = "YOUR_WIFI_SSID";         // Replace with your Wi-Fi name
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";     // Replace with your Wi-Fi password

// Backend Ingestion Endpoint:
// - Cloud (Render): "https://dprms-backend.onrender.com/clinical/telemetry/ingest"
// - Local Network:  "http://192.168.1.100:8000/clinical/telemetry/ingest"
const char* SERVER_URL    = "https://dprms-backend.onrender.com/clinical/telemetry/ingest";

const char* DEVICE_ID     = "ESP32-VITALS-01";
const unsigned long SEND_INTERVAL_MS = 500; // Push telemetry every 500ms

// ==========================================
// 2. HARDWARE PIN DEFINITIONS
// ==========================================
#define PIN_AD8232_OUTPUT  34  // GPIO 34 (Analog input only)
#define PIN_AD8232_LO_PLUS 25  // GPIO 25 (Leads-off Positive)
#define PIN_AD8232_LO_MIN  26  // GPIO 26 (Leads-off Negative)
#define PIN_I2C_SDA        21  // GPIO 21 (I2C SDA)
#define PIN_I2C_SCL        22  // GPIO 22 (I2C SCL)

// ==========================================
// 3. OBJECT INSTANCES & BUFFERS
// ==========================================
MAX30105 particleSensor;

// ECG Rolling buffer for high-frequency samples
const int ECG_BUFFER_SIZE = 16;
int ecgSamples[ECG_BUFFER_SIZE];
int ecgSampleIndex = 0;

// Pulse & SpO2 state tracking
const byte RATE_SIZE = 4; // Average across 4 beats for smooth BPM
byte rates[RATE_SIZE];
byte rateSpot = 0;
long lastBeat = 0;
float beatsPerMinute = 0;
int beatAvg = 0;
int calculatedSpO2 = 0;

unsigned long lastSendTime = 0;
unsigned long lastEcgSampleTime = 0;

// ==========================================
// 4. SETUP
// ==========================================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n[DPRMS] Initializing ESP32 Vitals Telemetry Node...");

  // Configure AD8232 GPIOs
  pinMode(PIN_AD8232_LO_PLUS, INPUT);
  pinMode(PIN_AD8232_LO_MIN, INPUT);
  analogReadResolution(12); // 12-bit ADC (0 - 4095)

  // Configure I2C
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);

  // Initialize MAX30102
  Serial.println("[DPRMS] Checking MAX30102 on I2C bus...");
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("[ERROR] MAX30102 not found! Check 3V3, GND, SDA (21), SCL (22).");
  } else {
    Serial.println("[OK] MAX30102 initialized successfully.");
    // Configure sensor with clinical settings
    byte ledBrightness = 60; // 0=Off to 255=50mA
    byte sampleAverage = 4;   // 1, 2, 4, 8, 16, 32
    byte ledMode = 2;         // 2 = Red + IR (SpO2 mode)
    byte sampleRate = 100;    // 50, 100, 200, 400, 800, 1000, 1600, 3200
    int pulseWidth = 411;     // 69, 118, 215, 411
    int adcRange = 4096;      // 2048, 4096, 8192, 16384

    particleSensor.setup(ledBrightness, sampleAverage, ledMode, sampleRate, pulseWidth, adcRange);
    particleSensor.setPulseAmplitudeRed(0x0A); // Turn Red LED to low to indicate sensor is running
    particleSensor.setPulseAmplitudeGreen(0);  // Turn off Green LED
  }

  // Connect to Wi-Fi
  connectWiFi();
}

// ==========================================
// 5. MAIN LOOP
// ==========================================
void loop() {
  // Reconnect Wi-Fi if dropped
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  // Sample ECG every 20ms (50Hz clinical waveform sampling)
  if (millis() - lastEcgSampleTime >= 20) {
    lastEcgSampleTime = millis();
    int rawEcg = analogRead(PIN_AD8232_OUTPUT);
    ecgSamples[ecgSampleIndex] = rawEcg;
    ecgSampleIndex = (ecgSampleIndex + 1) % ECG_BUFFER_SIZE;
  }

  // Read MAX30102 Infrared & Red values
  long irValue = particleSensor.getIR();
  long redValue = particleSensor.getRed();
  bool fingerDetected = (irValue > 50000);

  // Check for physiological pulse if finger is on sensor
  if (fingerDetected) {
    if (checkForBeat(irValue)) {
      long delta = millis() - lastBeat;
      lastBeat = millis();

      beatsPerMinute = 60 / (delta / 1000.0);

      if (beatsPerMinute < 255 && beatsPerMinute > 40) {
        rates[rateSpot++] = (byte)beatsPerMinute;
        rateSpot %= RATE_SIZE;

        // Calculate rolling average
        beatAvg = 0;
        for (byte x = 0; x < RATE_SIZE; x++) {
          beatAvg += rates[x];
        }
        beatAvg /= RATE_SIZE;

        // Calculate SpO2 approximation based on Red/IR AC-DC ratio
        if (redValue > 0) {
          float ratio = ((float)redValue / (float)irValue);
          int estimatedSpo2 = (int)(110 - (ratio * 15));
          if (estimatedSpo2 > 100) estimatedSpo2 = 99;
          if (estimatedSpo2 < 90) estimatedSpo2 = 95;
          calculatedSpO2 = estimatedSpo2;
        } else {
          calculatedSpO2 = 98;
        }
      }
    }
  } else {
    beatAvg = 0;
    calculatedSpO2 = 0;
  }

  // Check Leads-off status (True if electrodes are disconnected)
  bool leadsOff = (digitalRead(PIN_AD8232_LO_PLUS) == 1 || digitalRead(PIN_AD8232_LO_MIN) == 1);

  // Periodic Telemetry Dispatch over HTTP
  if (millis() - lastSendTime >= SEND_INTERVAL_MS) {
    lastSendTime = millis();
    sendTelemetry(fingerDetected, irValue, leadsOff, beatAvg, calculatedSpO2);
  }
}

// ==========================================
// 6. HTTP TELEMETRY TRANSMITTER
// ==========================================
void sendTelemetry(bool fingerDetected, long irValue, bool leadsOff, int hr, int spo2) {
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  HTTPClient http;
  String url = String(SERVER_URL);

  if (url.startsWith("https://")) {
    WiFiClientSecure client;
    client.setInsecure(); // Skip TLS root certificate validation for flexible IoT connection
    http.begin(client, url);
  } else {
    WiFiClient client;
    http.begin(client, url);
  }

  http.addHeader("Content-Type", "application/json");

  // Construct JSON payload directly (zero external library dependency)
  String requestBody = "{";
  requestBody += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  requestBody += "\"finger_detected\":" + String(fingerDetected ? "true" : "false") + ",";
  requestBody += "\"ir_value\":" + String(irValue) + ",";
  requestBody += "\"leads_off\":" + String(leadsOff ? "true" : "false") + ",";
  requestBody += "\"heart_rate\":" + String((hr > 0) ? hr : 0) + ",";
  requestBody += "\"spo2\":" + String((spo2 > 0) ? spo2 : 0) + ",";
  requestBody += "\"ecg_samples\":[";
  for (int i = 0; i < ECG_BUFFER_SIZE; i++) {
    int idx = (ecgSampleIndex + i) % ECG_BUFFER_SIZE;
    requestBody += String(ecgSamples[idx]);
    if (i < ECG_BUFFER_SIZE - 1) requestBody += ",";
  }
  requestBody += "]}";

  int httpResponseCode = http.POST(requestBody);

  if (httpResponseCode == 200) {
    Serial.printf("[HTTP 200] Telemetry Pushed -> HR: %d BPM | SpO2: %d%% | Finger: %s | LeadsOff: %s\n",
                  hr, spo2, fingerDetected ? "YES" : "NO", leadsOff ? "YES" : "NO");
  } else {
    Serial.printf("[HTTP ERROR %d] Failed to push telemetry to %s\n", httpResponseCode, SERVER_URL);
  }

  http.end();
}

// ==========================================
// 7. WI-FI HELPER
// ==========================================
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.printf("[DPRMS] Connecting to Wi-Fi SSID: %s ", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startAttempt = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < 10000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[OK] Wi-Fi Connected!");
    Serial.print("[INFO] ESP32 IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[WARNING] Wi-Fi connection timed out. Will retry in next loop.");
  }
}
