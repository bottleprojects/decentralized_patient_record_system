#pragma once

#include <Arduino.h>

/**
 * ============================================================================
 * DPRMS ESP32 FIRMWARE - HARDWARE & NETWORK CONFIGURATION
 * Decentralized Patient Record Management System (DPRMS)
 * ============================================================================
 */

// --- Device Identity & Cryptographic Credentials ---
#define DEVICE_ID             "ESP32-VITALS-01"
#define DEVICE_MODEL          "ESP32-WROOM-32-V1"
#define FIRMWARE_VERSION      "1.2.0"
// Pre-shared HMAC-SHA256 device key (burned into secure flash / eFuse in production)
#define DEVICE_HMAC_SECRET    "DPRMS_SECURE_DEVICE_SECRET_KEY_2026"

// --- Wi-Fi & Backend Endpoint Configuration (Production Authenticated TLS/HTTPS) ---
#define WIFI_SSID             "Hospital_Secure_IoT"
#define WIFI_PASSWORD         "Clinical_Vitals_2026!"
#define BACKEND_BASE_URL      "https://dprms-api.example.com"
#define INGEST_ENDPOINT       "/clinical/telemetry/ingest"
#define MODE_ENDPOINT         "/clinical/telemetry/mode"
#define HTTP_TIMEOUT_MS       3000

// --- Hardware Pin Definitions for MAX30102 Pulse Oximeter ---
// I2C Interface (Standard ESP32 hardware I2C bus)
#define MAX30102_SDA_PIN      21
#define MAX30102_SCL_PIN      22
#define MAX30102_I2C_FREQ     400000 // 400 kHz Fast Mode
#define MAX30102_INT_PIN      19

// Optical Signal Quality & Detection Thresholds
#define FINGER_THRESHOLD_IR   50000  // Minimum IR raw count indicating optical tissue coupling
#define SPO2_VALID_MIN        70     // Clinically plausible SpO2 lower limit
#define SPO2_VALID_MAX        100    // Physiological maximum
#define HR_VALID_MIN          35     // Lower bradycardia threshold
#define HR_VALID_MAX          220    // Maximum tachycardia threshold

// --- Hardware Pin Definitions for AD8232 Single-Lead ECG Front-End ---
// ADC Configuration (Using low-noise ADC1 channel)
#define AD8232_OUTPUT_PIN     36     // ADC1_CHANNEL_0 (GPIO 36 / SENSOR_VP)
#define AD8232_LO_PLUS_PIN    34     // Leads-Off detection + (Active High)
#define AD8232_LO_MINUS_PIN   35     // Leads-Off detection - (Active High)
#define AD8232_SDN_PIN        32     // Shutdown pin (Active Low, HIGH = Enabled)

// Sampling Parameters
#define ECG_SAMPLING_RATE_HZ  500    // 500 samples/sec (2 ms period)
#define ECG_BUFFER_SIZE       64     // Circular DMA transmission buffer
#define TELEMETRY_INTERVAL_MS 500    // Telemetry transmission cadence (2 Hz)

// --- Compile-Time Pin Validation ---
#if (AD8232_OUTPUT_PIN < 32 || AD8232_OUTPUT_PIN > 39)
#error "AD8232 output must connect to ADC1 (GPIOs 32-39) to prevent Wi-Fi ADC2 conflict!"
#endif

