#include "telemetry_encoder.h"

TelemetryEncoder::TelemetryEncoder(DeviceAuthenticator* auth) : _auth(auth) {}

String TelemetryEncoder::encodePacket(
    const char* sessionId,
    uint32_t sequenceNumber,
    const char* timestamp,
    bool fingerDetected,
    uint32_t irValue,
    bool leadsOff,
    int heartRate,
    int spo2,
    const std::vector<int>& ecgSamples,
    const char* acquisitionSource
) {
    // Generate hardware HMAC authentication tag
    String authTag = _auth ? _auth->computeHMAC(
        sessionId, sequenceNumber, timestamp, heartRate, spo2, irValue, leadsOff
    ) : "";

    String json = "{";
    json += "\"device_id\":\"" + String(_auth ? _auth->getDeviceId() : "ESP32-VITALS-01") + "\",";
    if (sessionId && strlen(sessionId) > 0) {
        json += "\"session_id\":\"" + String(sessionId) + "\",";
    }
    json += "\"sequence_number\":" + String(sequenceNumber) + ",";
    json += "\"finger_detected\":" + String(fingerDetected ? "true" : "false") + ",";
    json += "\"ir_value\":" + String(irValue) + ",";
    json += "\"leads_off\":" + String(leadsOff ? "true" : "false") + ",";
    json += "\"heart_rate\":" + String(heartRate) + ",";
    json += "\"spo2\":" + String(spo2) + ",";
    json += "\"timestamp\":\"" + String(timestamp ? timestamp : "") + "\",";
    json += "\"auth_tag\":\"" + authTag + "\",";
    json += "\"acquisition_source\":\"" + String(acquisitionSource) + "\",";

    json += "\"ecg_samples\":[";
    for (size_t i = 0; i < ecgSamples.size(); i++) {
        json += String(ecgSamples[i]);
        if (i + 1 < ecgSamples.size()) json += ",";
    }
    json += "]}";

    return json;
}

