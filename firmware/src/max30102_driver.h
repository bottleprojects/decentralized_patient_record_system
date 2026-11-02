#pragma once

#include <Arduino.h>
#include <Wire.h>
#include "../include/config.h"

struct Max30102Data {
    bool isConnected;
    bool fingerDetected;
    uint32_t irValue;
    uint32_t redValue;
    int heartRate;
    int spo2;
    const char* qualityStatus;
};

class Max30102Driver {
public:
    Max30102Driver();
    bool begin(uint8_t sdaPin = MAX30102_SDA_PIN, uint8_t sclPin = MAX30102_SCL_PIN);
    void update();
    Max30102Data getData() const;

private:
    bool _isAvailable;
    uint32_t _latestIr;
    uint32_t _latestRed;
    int _calculatedHr;
    int _calculatedSpo2;
    unsigned long _lastSampleTime;
    
    // DC filtering & peak detection state
    float _irDc;
    float _redDc;
    float _irAc;
    float _redAc;
    unsigned long _lastPeakTime;
};

