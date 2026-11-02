#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "../include/config.h"

class NetworkManager {
public:
    NetworkManager();
    bool begin(const char* ssid = WIFI_SSID, const char* password = WIFI_PASSWORD);
    bool isConnected();
    bool checkReconnect();
    
    // Transmits JSON telemetry packet to DPRMS ingestion endpoint
    bool sendTelemetry(const String& jsonPayload, String& outServerMode);

private:
    const char* _ssid;
    const char* _password;
    unsigned long _lastReconnectAttempt;
    uint32_t _reconnectBackoffMs;
};

