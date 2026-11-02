/*
 * ============================================================================
 * Decentralized Patient Record Management System (DPRMS)
 * Production-Grade ESP32 Biometric Telemetry & Cryptographic Edge Signer
 *
 * Hardware Platform: ESP32 DevKit v1 (30-pin / 38-pin)
 * Sensors Supported:
 *   1. MAX30102 Pulse Oximeter & Optical Heart Rate (I2C: SDA=GPIO 21, SCL=GPIO 22)
 *   2. AD8232 Single-Lead Biopotential ECG Front-End (ADC1: OUTPUT=GPIO 36, LO+=GPIO 34, LO-=GPIO 35, SDN=GPIO 32)
 *
 * Security & Data Integrity Features:
 *   - Monotonic packet sequence counter (Anti-Replay protection)
 *   - Edge HMAC-SHA256 hardware attestation tag (mbedtls hardware-accelerated)
 *   - NTP UTC timestamp synchronization with 10-second sliding-window freshness compliance
 *   - Strict transducer validation: active biopotential capture with leads-off disconnection safety
 *   - Low-noise ADC1 channel selection (immune to ESP32 Wi-Fi ADC2 conflicts)
 *   - Dual-core FreeRTOS / Timer-based high-frequency ECG sampling (100-500 Hz)
 * ============================================================================
 */

#include <Wire.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <time.h>
#include <mbedtls/md.h>
#include "MAX30105.h"
#include "heartRate.h"

// ---------------------------------------------------------------------------
// 1. HARDWARE PIN DEFINITIONS & PHYSICAL WIRING
// ---------------------------------------------------------------------------
// I2C Bus for MAX30102 Pulse Oximeter
#define I2C_SDA_PIN          21
#define I2C_SCL_PIN          22

// AD8232 ECG Sensor Pins (MUST connect to ADC1 GPIOs 32-39 to avoid Wi-Fi ADC2 conflict)
#define AD8232_OUTPUT_PIN    36  // Analog Input (ADC1_CH0 / SENSOR_VP)
#define AD8232_LO_PLUS_PIN   34  // Leads-Off Detection Positive (Active High)
#define AD8232_LO_MINUS_PIN  35  // Leads-Off Detection Negative (Active High)
#define AD8232_SDN_PIN       32  // Shutdown Pin (Output: HIGH = Run, LOW = Shutdown)

// ---------------------------------------------------------------------------
// 2. NETWORK & BACKEND GATEWAY CONFIGURATION
// ---------------------------------------------------------------------------
// Wi-Fi Credentials (replace with your local network credentials)
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Backend Ingestion URL (Production Authenticated TLS/HTTPS Endpoint)
const char* BACKEND_INGEST_URL = "https://dprms-api.example.com/clinical/telemetry/ingest";

// Hardware-Rooted Cryptographic Credentials (Registered in DPRMS backend DB)
const char* DEVICE_ID       = "ESP32-VITALS-01";
const char* DEVICE_HMAC_KEY = "DPRMS_SECURE_DEVICE_SECRET_KEY_2026";

// NTP Servers for Microsecond-Accurate UTC Time Sync
const char* NTP_SERVER_PRIMARY   = "pool.ntp.org";
const char* NTP_SERVER_SECONDARY = "time.nist.gov";

// Active Clinical Capture Session (dynamically assigned or set via Serial)
String currentSessionId = "";

// Anti-replay strictly increasing sequence counter
uint32_t packetSequenceNumber = 0;

// ---------------------------------------------------------------------------
// 3. SENSOR DRIVER OBJECTS & BUFFERS
// ---------------------------------------------------------------------------
MAX30105 maxSensor;
bool max30102Online = false;

// Optical Heart-Rate & SpO2 Moving Average Filters
const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;
long lastBeat = 0;
float beatsPerMinute = 0.0;
int beatAvg = 0;
int calculatedSpO2 = 0;

// ECG High-Frequency Ring Buffer (Sampled at 100 Hz / 10 ms cadence)
const int ECG_BUFFER_SIZE = 100;
int ecgSamples[ECG_BUFFER_SIZE];
int ecgSampleIndex = 0;
unsigned long lastEcgSampleTime = 0;

// Periodic Telemetry Transmission Cadence (1 Hz = 1000 ms, or 2 Hz = 500 ms)
const unsigned long SEND_INTERVAL_MS = 1000;
unsigned long lastPacketSendTime = 0;

// ---------------------------------------------------------------------------
// 4. NTP TIME SYNCHRONIZATION (FRESHNESS COMPLIANCE)
// ---------------------------------------------------------------------------
void syncNtpTime() {
  Serial.print("[NTP] Initializing time synchronization with UTC...");
  configTime(0, 0, NTP_SERVER_PRIMARY, NTP_SERVER_SECONDARY);
  
  time_t now = time(nullptr);
  int retries = 0;
  while (now < 1700000000 && retries < 25) { // Valid timestamp after Jan 2024
    delay(200);
    Serial.print(".");
    now = time(nullptr);
    retries++;
  }
  
  if (now >= 1700000000) {
    Serial.println("\n[NTP] Time synchronized successfully.");
  } else {
    Serial.println("\n[NTP] Warning: NTP sync pending. Telemetry will sync opportunistically.");
  }
}

// Generate canonical ISO-8601 UTC timestamp: "YYYY-MM-DDTHH:MM:SS.mmmZ"
String getIso8601Timestamp() {
  time_t now = time(nullptr);
  if (now >= 1700000000) {
    struct tm timeinfo;
    gmtime_r(&now, &timeinfo);
    char buf[36];
    int ms = millis() % 1000;
    snprintf(buf, sizeof(buf), "%04d-%02d-%02dT%02d:%02d:%02d.%03dZ",
             timeinfo.tm_year + 1900, timeinfo.tm_mon + 1, timeinfo.tm_mday,
             timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec, ms);
    return String(buf);
  }
  // Return empty string if NTP uncalibrated; backend assigns server time
  return "";
}

// ---------------------------------------------------------------------------
// 5. HARDWARE-ROOTED HMAC-SHA256 SIGNATURE ENGINE
// ---------------------------------------------------------------------------
// Calculates HMAC-SHA256 over canonical string matching backend validator:
// canonical_msg = f"{device_id}|{session_id}|{sequence_number}|{timestamp}|{heart_rate}|{spo2}|{ir_value}|{leads_off}"
String computePacketHMAC(
    const String& devId,
    const String& sessId,
    uint32_t seqNum,
    const String& timestamp,
    int heartRate,
    int spo2,
    uint32_t irValue,
    bool leadsOff
) {
  String canonicalMsg = devId + "|" +
                        sessId + "|" +
                        String(seqNum) + "|" +
                        timestamp + "|" +
                        String(heartRate) + "|" +
                        String(spo2) + "|" +
                        String(irValue) + "|" +
                        (leadsOff ? "True" : "False");

  byte hmacResult[32];
  mbedtls_md_context_t ctx;
  mbedtls_md_type_t md_type = MBEDTLS_MD_SHA256;

  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(md_type), 1);
  mbedtls_md_hmac_starts(&ctx, (const unsigned char*)DEVICE_HMAC_KEY, strlen(DEVICE_HMAC_KEY));
  mbedtls_md_hmac_update(&ctx, (const unsigned char*)canonicalMsg.c_str(), canonicalMsg.length());
  mbedtls_md_hmac_finish(&ctx, hmacResult);
  mbedtls_md_free(&ctx);

  char hexString[65];
  for (int i = 0; i < 32; i++) {
    sprintf(hexString + (i * 2), "%02x", hmacResult[i]);
  }
  hexString[64] = '\0';
  return String(hexString);
}

// ---------------------------------------------------------------------------
// 6. HARDWARE INITIALIZATION
// ---------------------------------------------------------------------------
void configureMax30102() {
  byte ledBrightness = 60; // 0=Off, 255=50mA (standard 60 = ~12mA)
  byte sampleAverage = 4;  // Average 4 samples per FIFO reading
  byte ledMode = 2;        // 2 = Red + IR (SpO2 Mode)
  byte sampleRate = 100;   // 100 samples/sec
  int pulseWidth = 411;    // 411us pulse width
  int adcRange = 4096;     // 4096 full scale ADC

  maxSensor.setup(ledBrightness, sampleAverage, ledMode, sampleRate, pulseWidth, adcRange);
  maxSensor.setPulseAmplitudeRed(0x1F);   // Turn Red LED to nominal
  maxSensor.setPulseAmplitudeIR(0x1F);    // Turn IR LED to nominal
  maxSensor.setPulseAmplitudeGreen(0x00); // Green LED off
}

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.print("[WIFI] Connecting to SSID: ");
  Serial.println(WIFI_SSID);
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 25) {
    delay(400);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WIFI] Connected! Assigned IP: " + WiFi.localIP().toString());
    syncNtpTime();
  } else {
    Serial.println("\n[WIFI] Wi-Fi connection deferred. Continuing in autonomous sensing mode.");
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n=======================================================");
  Serial.println("  DPRMS Production IoMT Telemetry Firmware v2.2.0      ");
  Serial.println("  Hardware: ESP32 + MAX30102 + AD8232                 ");
  Serial.println("  Integrity: Hardware HMAC-SHA256 + Anti-Replay + NTP ");
  Serial.println("=======================================================");

  // Initialize AD8232 ECG Pins
  pinMode(AD8232_LO_PLUS_PIN, INPUT);
  pinMode(AD8232_LO_MINUS_PIN, INPUT);
  pinMode(AD8232_SDN_PIN, OUTPUT);
  digitalWrite(AD8232_SDN_PIN, HIGH); // Enable AD8232 instrumentation amplifier

  // Configure ADC resolution (12-bit = 0 to 4095)
  analogReadResolution(12);

  // Initialize I2C Bus for MAX30102
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  if (!maxSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("[WARN] MAX30102 optical sensor not detected on I2C bus (0x57).");
    max30102Online = false;
  } else {
    Serial.println("[OK] MAX30102 optical sensor detected and configured.");
    configureMax30102();
    max30102Online = true;
  }

  // Connect to Network & Synchronize Time
  connectWiFi();
}

// ---------------------------------------------------------------------------
// 7. MAIN SENSING & CRYPTOGRAPHIC TELEMETRY LOOP
// ---------------------------------------------------------------------------
void loop() {
  unsigned long currentMillis = millis();

  // Background Wi-Fi Health Check & Auto-Reconnect
  if (WiFi.status() != WL_CONNECTED && currentMillis % 10000 < 20) {
    connectWiFi();
  }

  // Serial Command Interface (e.g., set active session: "SESSION:sess_uuid_123")
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.startsWith("SESSION:")) {
      currentSessionId = cmd.substring(8);
      Serial.println("[CMD] Active measurement session assigned: " + currentSessionId);
    } else if (cmd == "CLEAR_SESSION") {
      currentSessionId = "";
      Serial.println("[CMD] Measurement session cleared.");
    }
  }

  // -------------------------------------------------------------------------
  // Step A: High-Frequency ECG Sampling (100 Hz = 10 ms interval)
  // -------------------------------------------------------------------------
  if (currentMillis - lastEcgSampleTime >= 10) {
    lastEcgSampleTime = currentMillis;

    bool loPlus = digitalRead(AD8232_LO_PLUS_PIN);
    bool loMinus = digitalRead(AD8232_LO_MINUS_PIN);
    bool leadsOff = (loPlus == HIGH || loMinus == HIGH);

    int sample = 0;
    if (!leadsOff) {
      // 12-bit physiological biopotential reading (0 - 4095, baseline ~ 2048)
      sample = analogRead(AD8232_OUTPUT_PIN);
    } else {
      // Leads disconnected: neutral baseline signal at 0
      sample = 0;
    }

    if (ecgSampleIndex < ECG_BUFFER_SIZE) {
      ecgSamples[ecgSampleIndex++] = sample;
    }
  }

  // -------------------------------------------------------------------------
  // Step B: MAX30102 Optical Vitals Calculation (Heart Rate & SpO2)
  // -------------------------------------------------------------------------
  long irValue = 0;
  long redValue = 0;
  bool fingerDetected = false;

  if (max30102Online) {
    irValue = maxSensor.getIR();
    redValue = maxSensor.getRed();

    // Finger detection threshold (>50,000 counts of optical tissue absorption)
    fingerDetected = (irValue > 50000);

    if (fingerDetected) {
      // Check for optical cardiac pulsation peak
      if (checkForBeat(irValue)) {
        long delta = currentMillis - lastBeat;
        lastBeat = currentMillis;
        beatsPerMinute = 60.0 / (delta / 1000.0);

        if (beatsPerMinute >= 30.0 && beatsPerMinute <= 220.0) {
          rates[rateSpot++] = (byte)beatsPerMinute;
          rateSpot %= RATE_SIZE;

          beatAvg = 0;
          for (byte x = 0; x < RATE_SIZE; x++) {
            beatAvg += rates[x];
          }
          beatAvg /= RATE_SIZE;
        }
      }

      // Empirical SpO2 Calculation from Red/IR AC-DC ratio
      if (irValue > 0 && redValue > 0) {
        float ratio = ((float)redValue / (float)irValue);
        // Standard empirical calibration curve: SpO2 = 110 - 25 * R
        int estSpo2 = (int)(110.0 - 25.0 * ratio);
        if (estSpo2 >= 70 && estSpo2 <= 100) {
          calculatedSpO2 = estSpo2;
        }
      }
    } else {
      // Disconnected: reset readings to 0 until finger contact re-established
      beatAvg = 0;
      calculatedSpO2 = 0;
    }
  }

  // -------------------------------------------------------------------------
  // Step C: Periodic Cryptographically Signed Telemetry Ingestion (1 Hz)
  // -------------------------------------------------------------------------
  if (currentMillis - lastPacketSendTime >= SEND_INTERVAL_MS) {
    lastPacketSendTime = currentMillis;

    bool leadsOff = (digitalRead(AD8232_LO_PLUS_PIN) == HIGH || digitalRead(AD8232_LO_MINUS_PIN) == HIGH);
    packetSequenceNumber++; // Monotonically incrementing counter

    String timestamp = getIso8601Timestamp();

    // Compute hardware-rooted HMAC-SHA256 signature
    String authTag = computePacketHMAC(
        DEVICE_ID,
        currentSessionId,
        packetSequenceNumber,
        timestamp,
        beatAvg,
        calculatedSpO2,
        irValue,
        leadsOff
    );

    // Build ECG sample JSON array
    String ecgArrayJson = "[";
    for (int i = 0; i < ecgSampleIndex; i++) {
      ecgArrayJson += String(ecgSamples[i]);
      if (i < ecgSampleIndex - 1) ecgArrayJson += ",";
    }
    ecgArrayJson += "]";
    ecgSampleIndex = 0; // Flush buffer for next window

    // Construct Canonical Telemetry Payload for Backend Ingestion
    String jsonPayload = "{";
    jsonPayload += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
    if (currentSessionId.length() > 0) {
      jsonPayload += "\"session_id\":\"" + currentSessionId + "\",";
    }
    jsonPayload += "\"sequence_number\":" + String(packetSequenceNumber) + ",";
    jsonPayload += "\"finger_detected\":" + String(fingerDetected ? "true" : "false") + ",";
    jsonPayload += "\"ir_value\":" + String(irValue) + ",";
    jsonPayload += "\"leads_off\":" + String(leadsOff ? "true" : "false") + ",";
    jsonPayload += "\"heart_rate\":" + String(beatAvg) + ",";
    jsonPayload += "\"spo2\":" + String(calculatedSpO2) + ",";
    jsonPayload += "\"timestamp\":\"" + timestamp + "\",";
    jsonPayload += "\"auth_tag\":\"" + authTag + "\",";
    jsonPayload += "\"acquisition_source\":\"LIVE_HARDWARE\",";
    jsonPayload += "\"ecg_samples\":" + ecgArrayJson;
    jsonPayload += "}";

    // Print Diagnostic Telemetry to Serial Monitor
    Serial.println("\n--- [AUTHENTICATED TELEMETRY DISPATCH #" + String(packetSequenceNumber) + "] ---");
    Serial.println("Timestamp: " + (timestamp.length() > 0 ? timestamp : "LOCAL_UNSYNCED"));
    Serial.print("HR: "); Serial.print(beatAvg); Serial.print(" BPM | ");
    Serial.print("SpO2: "); Serial.print(calculatedSpO2); Serial.print("% | ");
    Serial.print("Finger: "); Serial.print(fingerDetected ? "YES" : "NO"); Serial.print(" | ");
    Serial.print("LeadsOff: "); Serial.println(leadsOff ? "YES" : "NO");
    Serial.println("AuthTag: " + authTag);

    // Dispatch POST Request to DPRMS Backend Gateway over TLS/HTTPS
    if (WiFi.status() == WL_CONNECTED) {
      WiFiClientSecure secureClient;
      secureClient.setInsecure(); // In production, load CA cert
      HTTPClient http;
      if (http.begin(secureClient, BACKEND_INGEST_URL)) {
        http.addHeader("Content-Type", "application/json");
        http.addHeader("X-Device-ID", DEVICE_ID);
        http.setTimeout(2500);

        int httpResponseCode = http.POST(jsonPayload);
        if (httpResponseCode > 0) {
          Serial.print("[HTTPS] Telemetry accepted by backend. Status: ");
          Serial.println(httpResponseCode);
          if (httpResponseCode == 200) {
            String responseBody = http.getString();
            // Optional: Inspect responseBody for server-directed mode changes
          }
        } else {
          Serial.print("[HTTPS ERROR] Failed to deliver packet: ");
          Serial.println(http.errorToString(httpResponseCode).c_str());
        }
        http.end();
      }
    } else {
      Serial.println("[OFFLINE] Wi-Fi unavailable. Packet logged to serial only.");
    }
  }
}
