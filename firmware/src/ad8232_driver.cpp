#include "ad8232_driver.h"

Ad8232Driver::Ad8232Driver()
    : _outputPin(AD8232_OUTPUT_PIN),
      _loPlusPin(AD8232_LO_PLUS_PIN),
      _loMinusPin(AD8232_LO_MINUS_PIN),
      _sdnPin(AD8232_SDN_PIN),
      _isInitialized(false),
      _latestSample(2048) {}

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

    _samples.reserve(ECG_BUFFER_SIZE);
    _isInitialized = true;
    return true;
}

void Ad8232Driver::sample() {
    if (!_isInitialized) return;

    bool loPlus = (digitalRead(_loPlusPin) == HIGH);
    bool loMinus = (digitalRead(_loMinusPin) == HIGH);

    if (loPlus || loMinus) {
        _latestSample = 2048; // Baseline center value when leads are detached
    } else {
        _latestSample = analogRead(_outputPin);
    }

    if (_samples.size() < ECG_BUFFER_SIZE) {
        _samples.push_back(_latestSample);
    }
}

Ad8232Data Ad8232Driver::getDataAndFlush() {
    Ad8232Data d;
    d.isConnected = _isInitialized;
    bool loPlus = (digitalRead(_loPlusPin) == HIGH);
    bool loMinus = (digitalRead(_loMinusPin) == HIGH);
    d.leadsOff = (loPlus || loMinus);
    d.latestSample = _latestSample;
    d.sampleBuffer = _samples;
    _samples.clear();

    if (!_isInitialized) d.qualityStatus = "SENSOR_DISCONNECTED";
    else if (d.leadsOff) d.qualityStatus = "INSUFFICIENT_SIGNAL";
    else d.qualityStatus = "VALID";

    return d;
}

