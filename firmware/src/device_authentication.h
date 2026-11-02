#pragma once

#include <Arduino.h>
#include <mbedtls/md.h>

class DeviceAuthenticator {
public:
    DeviceAuthenticator(const char* deviceId, const char* secretKey);

    // Computes HMAC-SHA256 hex string over canonical message
    String computeHMAC(
        const char* sessionId,
        uint32_t sequenceNumber,
        const char* timestamp,
        int heartRate,
        int spo2,
        uint32_t irValue,
        bool leadsOff
    );

    const char* getDeviceId() const { return _deviceId; }

private:
    const char* _deviceId;
    const char* _secretKey;
};

