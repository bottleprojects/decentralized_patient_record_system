#include "network_manager.h"

NetworkManager::NetworkManager()
    : _ssid(WIFI_SSID),
      _password(WIFI_PASSWORD),
      _lastReconnectAttempt(0),
      _reconnectBackoffMs(2000) {}

bool NetworkManager::begin(const char* ssid, const char* password) {
    _ssid = ssid;
    _password = password;
    WiFi.mode(WIFI_STA);
    WiFi.begin(_ssid, _password);

    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - start) < 6000) {
        delay(200);
    }
    return (WiFi.status() == WL_CONNECTED);
}

bool NetworkManager::isConnected() {
    return (WiFi.status() == WL_CONNECTED);
}

bool NetworkManager::checkReconnect() {
    if (WiFi.status() == WL_CONNECTED) {
        _reconnectBackoffMs = 2000;
        return true;
    }

    unsigned long now = millis();
    if (now - _lastReconnectAttempt > _reconnectBackoffMs) {
        _lastReconnectAttempt = now;
        WiFi.reconnect();
        if (_reconnectBackoffMs < 30000) {
            _reconnectBackoffMs *= 2; // Exponential backoff up to 30s
        }
    }
    return false;
}

bool NetworkManager::sendTelemetry(const String& jsonPayload, String& outServerMode) {
    if (!isConnected()) return false;

    HTTPClient http;
    String url = String(BACKEND_BASE_URL) + String(INGEST_ENDPOINT);

    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(HTTP_TIMEOUT_MS);

    int httpResponseCode = http.POST(jsonPayload);
    bool success = false;

    if (httpResponseCode == 200) {
        String response = http.getString();
        int modeIdx = response.indexOf("\"mode\":\"");
        if (modeIdx != -1) {
            int endIdx = response.indexOf("\"", modeIdx + 8);
            if (endIdx != -1) {
                outServerMode = response.substring(modeIdx + 8, endIdx);
            }
        }
        success = true;
    }
    http.end();
    return success;
}

