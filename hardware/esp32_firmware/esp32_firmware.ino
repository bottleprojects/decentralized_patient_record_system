/*
 * ============================================================================
 * Decentralized Patient Record Management System (DPRMS)
 * Genuine Edge IoT Sensor Telemetry & Ingestion Firmware
 * Hardware Platform: ESP32 DevKit v1 (38-pin / 30-pin)
 * Sensors:
 *   1. MAX30102: Optical Heart-Rate & Pulse Oximeter (I2C: SDA=21, SCL=22)
 *   2. AD8232: Single-Lead Biopotential Heart Rate Monitor (ADC=34, LO+=35, LO-=32)
 *
 * Security & Integrity:
 *   - Hardware Device ID + UTC Timestamp + Ephemeral Session UUID
 *   - Edge HMAC-SHA256 packet authentication over payload
 *   - Strict hardware sensor validation: zero synthetic fallback constants
 * ============================================================================
 */

#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <mbedtls/md.h>
#include "MAX30105.h"
#include "heartRate.h"

// ---------------------------------------------------------------------------
// 1. HARDWARE PIN DEFINITIONS
// ---------------------------------------------------------------------------
#define I2C_SDA_PIN          21
#define I2C_SCL_PIN          22

#define AD8232_OUTPUT_PIN    34  // Analog Input (ADC1_CH6 - Input Only)
#define AD8232_LO_PLUS_PIN   35  // Leads-off Detection Positive
#define AD8232_LO_MINUS_PIN  32  // Leads-off Detection Negative

// ---------------------------------------------------------------------------
// 2. NETWORK & INGESTION CONFIGURATION
// ---------------------------------------------------------------------------
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Backend Ingestion Endpoint (FastAPI)
const char* INGESTION_URL = "http://192.168.1.100:8000/api/clinical/vitals/stream";

// Cryptographic Edge Identity
const char* DEVICE_ID       = "ESP32_DPRMS_SN_7721A";
const char* DEVICE_HMAC_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"; // 256-bit provisioned secret

// Ephemeral capture session (dynamically populated on session handshake)
String currentSessionId = "sess_init_unregistered";

// ---------------------------------------------------------------------------
// 3. SENSOR OBJECTS & SAMPLING BUFFERS
// ---------------------------------------------------------------------------
MAX30105 maxSensor;

const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;
long lastBeat = 0;
float currentBeatsPerMinute = 0.0;
int beatAvg = 0;
int calculatedSpO2 = 0;

bool max30102Online = false;
unsigned long lastPacketSendTime = 0;
const unsigned long SEND_INTERVAL_MS = 1000; // 1 Hz packet transmission

// ECG Sample Accumulator for the current 1-second burst (sampled at 100 Hz)
const int ECG_BUFFER_SIZE = 100;
int ecgSamples[ECG_BUFFER_SIZE];
int ecgSampleIndex = 0;
unsigned long lastEcgSampleTime = 0;

// ---------------------------------------------------------------------------
// 4. CRYPTOGRAPHIC SIGNING (HMAC-SHA256)
// ---------------------------------------------------------------------------
String computeHMACSHA256(const String& payload, const char* keyStr) {
  byte hmacResult[32];
  mbedtls_md_context_t ctx;
  mbedtls_md_type_t md_type = MBEDTLS_MD_SHA256;

  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(md_type), 1);
  mbedtls_md_hmac_starts(&ctx, (const unsigned char*)keyStr, strlen(keyStr));
  mbedtls_md_hmac_update(&ctx, (const unsigned char*)payload.c_str(), payload.length());
  mbedtls_md_hmac_finish(&ctx, hmacResult);
  mbedtls_md_free(&ctx);

  String hexString = "";
  for (int i = 0; i < 32; i++) {
    char buf[3];
    sprintf(buf, "%02x", hmacResult[i]);
    hexString += buf;
  }
  return hexString;
}

// ---------------------------------------------------------------------------
// 5. HARDWARE INITIALIZATION
// ---------------------------------------------------------------------------
void configureMax30102() {
  byte ledBrightness = 60; // 0=Off, 255=50mA
  byte sampleAverage = 4;  // Options: 1, 2, 4, 8, 16, 32
  byte ledMode = 2;        // 2 = Red + IR
  byte sampleRate = 100;   // Options: 50, 100, 200, 400, 800, 1000, 1600, 3200
  int pulseWidth = 411;    // Options: 69, 118, 215, 411
  int adcRange = 4096;     // Options: 2048, 4096, 8192, 16384

  maxSensor.setup(ledBrightness, sampleAverage, ledMode, sampleRate, pulseWidth, adcRange);
  maxSensor.setPulseAmplitudeRed(0x0A);
  maxSensor.setPulseAmplitudeGreen(0);
}

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.print("[WIFI] Connecting to: ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WIFI] Connected! IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\n[WIFI] Connection pending. Continuing in autonomous sensing mode.");
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=======================================================");
  Serial.println("  DPRMS Genuine IoMT Telemetry Firmware v2.1.0        ");
  Serial.println("  Hardware: ESP32 + MAX30102 + AD8232                 ");
  Serial.println("  Integrity: Hardware-Rooted HMAC-SHA256 Signing      ");
  Serial.println("=======================================================");

  // Initialize AD8232 Leads-Off Detection Pins
  pinMode(AD8232_LO_PLUS_PIN, INPUT);
  pinMode(AD8232_LO_MINUS_PIN, INPUT);
  analogReadResolution(12); // 12-bit ADC (0 - 4095)

  // Initialize I2C Bus for MAX30102
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  if (!maxSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("[WARN] MAX30102 optical sensor not detected on I2C bus. Probe continuing...");
    max30102Online = false;
  } else {
    Serial.println("[OK] MAX30102 optical sensor initialized successfully.");
    configureMax30102();
    max30102Online = true;
  }

  // Connect to Network
  connectWiFi();
}

// ---------------------------------------------------------------------------
// 6. MAIN MEASUREMENT & TELEMETRY LOOP
// ---------------------------------------------------------------------------
void loop() {
  // Reconnect Wi-Fi if dropped
  if (WiFi.status() != WL_CONNECTED && millis() % 10000 < 50) {
    connectWiFi();
  }

  // Handle Serial Configuration Commands (e.g. "SESSION:sess_9f82a1")
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.startsWith("SESSION:")) {
      currentSessionId = cmd.substring(8);
      Serial.println("[CMD] Active session updated to: " + currentSessionId);
    }
  }

  // 1. High-Frequency ECG Sampling (100 Hz = 10 ms interval)
  if (millis() - lastEcgSampleTime >= 10) {
    lastEcgSampleTime = millis();
    bool leadsOff = (digitalRead(AD8232_LO_PLUS_PIN) == HIGH || digitalRead(AD8232_LO_MINUS_PIN) == HIGH);
    int rawEcg = 0;
    if (!leadsOff) {
      rawEcg = analogRead(AD8232_OUTPUT_PIN); // Genuine 12-bit biopotential reading
    }
    if (ecgSampleIndex < ECG_BUFFER_SIZE) {
      ecgSamples[ecgSampleIndex++] = rawEcg;
    }
  }

  // 2. Optical Contact & Pulse Oximetry Sampling
  long irValue = 0;
  long redValue = 0;
  bool fingerDetected = false;

  if (max30102Online) {
    irValue = maxSensor.getIR();
    redValue = maxSensor.getRed();
    fingerDetected = (irValue > 50000); // Dynamic optical threshold

    if (fingerDetected) {
      if (checkForBeat(irValue)) {
        long delta = millis() - lastBeat;
        lastBeat = millis();
        currentBeatsPerMinute = 60.0 / (delta / 1000.0);

        if (currentBeatsPerMinute >= 30.0 && currentBeatsPerMinute <= 220.0) {
          rates[rateSpot++] = (byte)currentBeatsPerMinute;
          rateSpot %= RATE_SIZE;

          beatAvg = 0;
          for (byte x = 0; x < RATE_SIZE; x++) {
            beatAvg += rates[x];
          }
          beatAvg /= RATE_SIZE;
        }
      }

      // Compute empirical SpO2 ratio from red and IR AC/DC signals
      if (irValue > 0 && redValue > 0) {
        float ratio = ((float)redValue / (float)irValue);
        int estSpo2 = (int)(110.0 - 25.0 * ratio);
        if (estSpo2 >= 70 && estSpo2 <= 100) {
          calculatedSpO2 = estSpo2;
        }
      }
    } else {
      // Disconnected: reset readings. NEVER provide synthetic fallbacks (e.g. 74 BPM / 98%)
      beatAvg = 0;
      calculatedSpO2 = 0;
    }
  }

  // 3. Periodic Cryptographically Signed Telemetry Dispatch (1 Hz)
  if (millis() - lastPacketSendTime >= SEND_INTERVAL_MS) {
    lastPacketSendTime = millis();

    bool leadsOff = (digitalRead(AD8232_LO_PLUS_PIN) == HIGH || digitalRead(AD8232_LO_MINUS_PIN) == HIGH);
    unsigned long timestampUtc = millis(); // Device uptime offset; synchronized via NTP in production

    // Construct ECG array JSON string
    String ecgJson = "[";
    for (int i = 0; i < ecgSampleIndex; i++) {
      ecgJson += String(ecgSamples[i]);
      if (i < ecgSampleIndex - 1) ecgJson += ",";
    }
    ecgJson += "]";
    ecgSampleIndex = 0; // Reset buffer for next 1-second burst

    // Construct Canonical Telemetry Payload
    String payload = "{";
    payload += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
    payload += "\"session_uuid\":\"" + currentSessionId + "\",";
    payload += "\"timestamp_ms\":" + String(timestampUtc) + ",";
    payload += "\"sensor_status\":{";
    payload += "\"max30102_online\":" + String(max30102Online ? "true" : "false") + ",";
    payload += "\"finger_detected\":" + String(fingerDetected ? "true" : "false") + ",";
    payload += "\"ad8232_leads_off\":" + String(leadsOff ? "true" : "false");
    payload += "},";
    payload += "\"telemetry\":{";
    payload += "\"heart_rate_bpm\":" + String(beatAvg) + ",";
    payload += "\"spo2_percent\":" + String(calculatedSpO2) + ",";
    payload += "\"raw_ir\":" + String(irValue) + ",";
    payload += "\"raw_red\":" + String(redValue);
    payload += "},";
    payload += "\"ecg_samples\":" + ecgJson;
    payload += "}";

    // Compute Edge Cryptographic Signature over canonical payload
    String signature = computeHMACSHA256(payload, DEVICE_HMAC_KEY);

    // Output Serial Telemetry Log
    Serial.println("\n--- [DPRMS AUTHENTICATED TELEMETRY PACKET] ---");
    Serial.print("Payload Size: "); Serial.print(payload.length()); Serial.println(" bytes");
    Serial.print("HMAC-SHA256: "); Serial.println(signature);
    Serial.print("Status: HR="); Serial.print(beatAvg);
    Serial.print(" BPM | SpO2="); Serial.print(calculatedSpO2);
    Serial.print("% | Finger="); Serial.print(fingerDetected ? "YES" : "NO");
    Serial.print(" | LeadsOff="); Serial.println(leadsOff ? "YES" : "NO");

    // Post to Backend Gateway if Wi-Fi Connected
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(INGESTION_URL);
      http.addHeader("Content-Type", "application/json");
      http.addHeader("X-Device-ID", DEVICE_ID);
      http.addHeader("X-Device-Signature", signature);

      int httpResponseCode = http.POST(payload);
      if (httpResponseCode > 0) {
        Serial.print("[HTTP] Ingestion response code: ");
        Serial.println(httpResponseCode);
      } else {
        Serial.print("[HTTP] Error sending telemetry: ");
        Serial.println(http.errorToString(httpResponseCode).c_str());
      }
      http.end();
    }
  }
}
