#include "ad8232_driver.h"

Ad8232Driver::Ad8232Driver()
    : _outputPin(AD8232_OUTPUT_PIN),
      _loPlusPin(AD8232_LO_PLUS_PIN),
      _loMinusPin(AD8232_LO_MINUS_PIN),
      _sdnPin(AD8232_SDN_PIN),
      _isInitialized(false),
      _latestSample(2048),
      _head(0),
      _count(0) {}

bool Ad8232Driver::begin(uint8_t outputPin, uint8_t loPlusPin, uint8_t loMinusPin, uint8_t sdnPin) {
    _outputPin = outputPin;
    _loPlusPin = loPlusPin;
    _loMinusPin = loMinusPin;
    _sdnPin = sdnPin;

    pinMode(_loPlusPin, INPUT);
    pinMode(_loMinusPin, INPUT);
    pinMode(_sdnPin, OUTPUT);
    digitalWrite(_sdnPin, HIGH); // Enable AD8232 instrumentation amplifier

    // Configure 12-bit ADC resolution (0-4095 range)
    analogReadResolution(12);
    analogSetAttenuation(ADC_11db); // Full-scale ~3.3V

    _head = 0;
    _count = 0;
    _isInitialized = true;
    return true;
}

void Ad8232Driver::sample() {
    // Strictly O(1) ISR-safe sampling with ZERO dynamic heap allocation
    if (!_isInitialized) return;

    bool loPlus = (digitalRead(_loPlusPin) == HIGH);
    bool loMinus = (digitalRead(_loMinusPin) == HIGH);

    int sampleVal = (loPlus || loMinus) ? 2048 : analogRead(_outputPin);
    _latestSample = sampleVal;

    // Statically bounded lockless circular buffer insertion
    if (_count < ECG_RING_BUFFER_SIZE) {
        _sampleRingBuffer[_head] = sampleVal;
        _head = (_head + 1) % ECG_RING_BUFFER_SIZE;
        _count++;
    }
}

Ad8232Data Ad8232Driver::getDataAndFlush() {
    Ad8232Data d;
    d.isConnected = _isInitialized;
    bool loPlus = (digitalRead(_loPlusPin) == HIGH);
    bool loMinus = (digitalRead(_loMinusPin) == HIGH);
    d.leadsOff = (loPlus || loMinus);
    d.latestSample = _latestSample;

    // Flush ring buffer in task context
    size_t numSamples = _count;
    d.sampleBuffer.reserve(numSamples);
    size_t startIdx = (_head + ECG_RING_BUFFER_SIZE - numSamples) % ECG_RING_BUFFER_SIZE;
    for (size_t i = 0; i < numSamples; i++) {
        d.sampleBuffer.push_back(_sampleRingBuffer[(startIdx + i) % ECG_RING_BUFFER_SIZE]);
    }
    _count = 0;

    if (!_isInitialized) d.qualityStatus = "SENSOR_DISCONNECTED";
    else if (d.leadsOff) d.qualityStatus = "INSUFFICIENT_SIGNAL";
    else d.qualityStatus = "VALID";

    return d;
}

