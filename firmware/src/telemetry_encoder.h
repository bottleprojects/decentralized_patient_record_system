#pragma once

#include <Arduino.h>
#include <vector>
#include "device_authentication.h"

class TelemetryEncoder {
public:
    TelemetryEncoder(DeviceAuthenticator* auth);

    String encodePacket(
        const char* sessionId,
        uint32_t sequenceNumber,
        const char* timestamp,
        bool fingerDetected,
        uint32_t irValue,
        bool leadsOff,
        int heartRate,
        int spo2,
        const std::vector<int>& ecgSamples,
        const char* acquisitionSource = "LIVE_HARDWARE"
    );

private:
    DeviceAuthenticator* _auth;
};

