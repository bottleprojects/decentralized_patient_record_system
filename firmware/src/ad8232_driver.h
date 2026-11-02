#pragma once

#include <Arduino.h>
#include <vector>
#include "../include/config.h"

#define ECG_RING_BUFFER_SIZE 128

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
    volatile bool _isInitialized;
    volatile int _latestSample;

    // Statically allocated, ISR-safe ring buffer: eliminates heap allocations in ISR
    volatile int _sampleRingBuffer[ECG_RING_BUFFER_SIZE];
    volatile size_t _head;
    volatile size_t _count;
};

