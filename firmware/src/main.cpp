#include <Arduino.h>
#include "../include/config.h"
#include "device_authentication.h"
#include "max30102_driver.h"
#include "ad8232_driver.h"
#include "telemetry_encoder.h"
#include "network_manager.h"

// Hardware instances
DeviceAuthenticator authenticator(DEVICE_ID, DEVICE_HMAC_SECRET);
Max30102Driver ppgSensor;
Ad8232Driver ecgSensor;
TelemetryEncoder encoder(&authenticator);
NetworkManager network;

// Operational telemetry state
uint32_t packetSequence = 0;
String currentMode = "BOTH";
unsigned long lastTransmitTime = 0;
unsigned long lastPpgUpdateTime = 0;

// High-resolution hardware timer for 500 Hz ECG sampling
hw_timer_t* ecgTimer = NULL;
portMUX_TYPE timerMux = portMUX_INITIALIZER_UNLOCKED;

void IRAM_ATTR onEcgTimer() {
    portENTER_CRITICAL_ISR(&timerMux);
    ecgSensor.sample();
    portEXIT_CRITICAL_ISR(&timerMux);
}

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("\n[DPRMS] Initializing ESP32 Cryptographic Sensor Gateway...");

    // 1. Initialize AD8232 ECG Front-End
    if (ecgSensor.begin()) {
        Serial.println("[DPRMS] AD8232 ECG sensor initialized successfully.");
    } else {
        Serial.println("[ERROR] Failed to initialize AD8232 ECG sensor.");
    }

    // 2. Initialize MAX30102 Pulse Oximeter
    if (ppgSensor.begin()) {
        Serial.println("[DPRMS] MAX30102 Optical sensor initialized successfully.");
    } else {
        Serial.println("[ERROR] Failed to initialize MAX30102 sensor. Check I2C wiring.");
    }

    // 3. Connect to Secure Clinical IoT Network
    Serial.print("[DPRMS] Connecting to Wi-Fi...");
    if (network.begin()) {
        Serial.println(" Connected! IP: " + WiFi.localIP().toString());
    } else {
        Serial.println(" Offline mode. Will attempt background reconnection.");
    }

    // 4. Setup 500 Hz hardware timer for ADC sampling (Timer 0, Prescaler 80 -> 1 tick = 1us, alarm 2000us = 500Hz)
    ecgTimer = timerBegin(0, 80, true);
    timerAttachInterrupt(ecgTimer, &onEcgTimer, true);
    timerAlarmWrite(ecgTimer, 2000, true);
    timerAlarmEnable(ecgTimer);
    Serial.println("[DPRMS] Hardware sampling timer enabled at 500 Hz.");
}

void loop() {
    unsigned long now = millis();

    // 1. Update optical PPG sensor at 100 Hz
    if (now - lastPpgUpdateTime >= 10) {
        lastPpgUpdateTime = now;
        ppgSensor.update();
    }

    // 2. Check network link and reconnect if needed
    network.checkReconnect();

    // 3. Telemetry packet construction and transmission cadence (2 Hz / 500 ms)
    if (now - lastTransmitTime >= TELEMETRY_INTERVAL_MS) {
        lastTransmitTime = now;

        // Fetch buffered data
        Max30102Data ppg = ppgSensor.getData();
        portENTER_CRITICAL(&timerMux);
        Ad8232Data ecg = ecgSensor.getDataAndFlush();
        portEXIT_CRITICAL(&timerMux);

        packetSequence++;

        // ISO-8601 millisecond timestamp from device uptime
        char timeStr[32];
        sprintf(timeStr, "2026-11-02T%02lu:%02lu:%02lu.%03luZ",
                (now / 3600000) % 24,
                (now / 60000) % 60,
                (now / 1000) % 60,
                now % 1000);

        // Encode and cryptographically sign packet
        String payload = encoder.encodePacket(
            "",                      // active session ID (empty in streaming mode)
            packetSequence,
            timeStr,
            ppg.fingerDetected,
            ppg.irValue,
            ecg.leadsOff,
            ppg.heartRate,
            ppg.spo2,
            ecg.sampleBuffer,
            "LIVE_HARDWARE"
        );

        // Transmit securely to DPRMS backend
        String serverMode;
        bool sent = network.sendTelemetry(payload, serverMode);
        if (sent && serverMode.length() > 0) {
            currentMode = serverMode;
        }

        #if CORE_DEBUG_LEVEL >= 3
        Serial.printf("[TX] Seq=%u HR=%d SpO2=%d Samples=%d Sent=%s Mode=%s\n",
                      packetSequence, ppg.heartRate, ppg.spo2,
                      (int)ecg.sampleBuffer.size(), sent ? "YES" : "NO", currentMode.c_str());
        #endif
    }
}

