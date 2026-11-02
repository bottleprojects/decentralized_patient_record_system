# DPRMS Edge IoT Sensor Firmware (ESP32)

Cryptographically authenticated physiological telemetry firmware for the **Decentralized Patient Record Management System (DPRMS)**.

---

## 1. Hardware Architecture & Wiring

| Sensor | Sensor Pin | ESP32 Pin | Purpose |
| :--- | :--- | :--- | :--- |
| **MAX30102** (Optical PPG) | `VCC` | `3V3` | 3.3V Power |
| | `GND` | `GND` | Ground |
| | `SDA` | `GPIO 21` | I2C Data |
| | `SCL` | `GPIO 22` | I2C Clock |
| **AD8232** (Lead-II ECG) | `3.3V` | `3V3` | 3.3V Power |
| | `GND` | `GND` | Ground |
| | `OUTPUT` | `GPIO 36` | 12-bit ADC Input (ADC1_CH0) |
| | `LO+` | `GPIO 34` | Lead-Off Detection Positive |
| | `LO-` | `GPIO 35` | Lead-Off Detection Negative |
| | `SDN` | `GPIO 32` | Shutdown Pin (Active High Enable) |

> **IMPORTANT**:
> `GPIO 36`, `34`, and `35` connect to ADC1 on the ESP32. This avoids any conflict with Wi-Fi operations (ADC2 channels are disabled during active Wi-Fi transmission).

---

## 2. Integrity & Cryptographic Security Architecture

1. **Strict Transducer Validation**:
   - The firmware samples raw digital registers from the MAX30102 via I2C and raw biopotentials from the AD8232 via ADC1.
   - When no finger is detected or leads are off, values report `0` and flags report `finger_detected: false` / `leads_off: true`.
2. **Edge HMAC-SHA256 Signing**:
   - Each canonical packet is hashed and signed at the silicon level using hardware cryptographic accelerators (`mbedtls/md.h`).
   - The generated 256-bit hexadecimal signature is included in the payload `auth_tag`.
3. **Session Binding & Freshness**:
   - Telemetry packets are bound to the active `session_id`, synchronized via NTP UTC time, and verified against a 10-second sliding-window freshness tolerance.

---

## 3. Required Arduino Libraries

Install the following libraries via Arduino IDE Library Manager or PlatformIO:
- **SparkFun MAX3010x Pulse and Proximity Sensor Library** (by SparkFun Electronics)
- **WiFi** & **HTTPClient** (Built into the ESP32 Arduino Core)
- **mbedtls** (Built into the ESP32 Arduino Core)

---

## 4. Ingestion Payload Specification

```json
{
  "device_id": "ESP32_DPRMS_SN_7721A",
  "session_uuid": "sess_9f82a1b4",
  "timestamp_ms": 1740982145,
  "sensor_status": {
    "max30102_online": true,
    "finger_detected": true,
    "ad8232_leads_off": false
  },
  "telemetry": {
    "heart_rate_bpm": 76,
    "spo2_percent": 98,
    "raw_ir": 184520,
    "raw_red": 142100
  },
  "ecg_samples": [2048, 2055, 2060, 2190, 2450, 1820, 2045, ...]
}
```
