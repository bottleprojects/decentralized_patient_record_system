#pragma once

#include <Arduino.h>
#include <vector>
#include "../include/config.h"

struct Ad8232Data {
    bool isConnected;
    bool leadsOff;
    int latestSample;
    std::vector<int> sampleBuffer;
    const char* qualityStatus;
};

class Ad8232Driver {
public:
    Ad8232Driver();
    bool begin(
        uint8_t outputPin = AD8232_OUTPUT_PIN,
        uint8_t loPlusPin = AD8232_LO_PLUS_PIN,
        uint8_t loMinusPin = AD8232_LO_MINUS_PIN,
        uint8_t sdnPin = AD8232_SDN_PIN
    );
    void sample();
    Ad8232Data getDataAndFlush();

private:
    uint8_t _outputPin;
    uint8_t _loPlusPin;
    uint8_t _loMinusPin;
    uint8_t _sdnPin;
    bool _isInitialized;
    int _latestSample;
    std::vector<int> _samples;
};

