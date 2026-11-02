#include "max30102_driver.h"

#define MAX30102_I2C_ADDR 0x57

Max30102Driver::Max30102Driver()
    : _isAvailable(false),
      _latestIr(0),
      _latestRed(0),
      _calculatedHr(0),
      _calculatedSpo2(0),
      _lastSampleTime(0),
      _irDc(0),
      _redDc(0),
      _irAc(0),
      _redAc(0),
      _lastPeakTime(0) {}

bool Max30102Driver::begin(uint8_t sdaPin, uint8_t sclPin) {
    Wire.begin(sdaPin, sclPin, MAX30102_I2C_FREQ);
    Wire.beginTransmission(MAX30102_I2C_ADDR);
    if (Wire.endTransmission() == 0) {
        _isAvailable = true;
        // Configuration: Reset and set Mode to SpO2 mode (Red + IR)
        Wire.beginTransmission(MAX30102_I2C_ADDR);
        Wire.write(0x09); // Mode Config
        Wire.write(0x03); // SpO2 Mode (Red + IR)
        Wire.endTransmission();

        // SpO2 Config: 100 samples/sec, 411us pulse width (18-bit ADC)
        Wire.beginTransmission(MAX30102_I2C_ADDR);
        Wire.write(0x0A);
        Wire.write(0x27);
        Wire.endTransmission();

        // LED Pulse Amplitude
        Wire.beginTransmission(MAX30102_I2C_ADDR);
        Wire.write(0x0C); // Red LED
        Wire.write(0x24); // ~7.2mA
        Wire.write(0x24); // IR LED ~7.2mA
        Wire.endTransmission();

        return true;
    }
    _isAvailable = false;
    return false;
}

void Max30102Driver::update() {
    if (!_isAvailable) return;

    // Read 6 bytes from FIFO data register (0x07)
    Wire.beginTransmission(MAX30102_I2C_ADDR);
    Wire.write(0x07);
    if (Wire.endTransmission() == 0) {
        Wire.requestFrom(MAX30102_I2C_ADDR, 6);
        if (Wire.available() >= 6) {
            uint32_t red = ((Wire.read() & 0x03) << 16) | (Wire.read() << 8) | Wire.read();
            uint32_t ir  = ((Wire.read() & 0x03) << 16) | (Wire.read() << 8) | Wire.read();

            _latestRed = red;
            _latestIr = ir;

            // Finger detection gating
            if (ir < FINGER_THRESHOLD_IR) {
                _calculatedHr = 0;
                _calculatedSpo2 = 0;
                _irDc = 0;
                _redDc = 0;
                return;
            }

            // DC Tracking filter (alpha = 0.95)
            if (_irDc == 0) _irDc = ir;
            else _irDc = 0.95f * _irDc + 0.05f * ir;

            if (_redDc == 0) _redDc = red;
            else _redDc = 0.95f * _redDc + 0.05f * red;

            _irAc = (float)ir - _irDc;
            _redAc = (float)red - _redDc;

            // Simple beat detector based on zero-crossing / peak
            unsigned long now = millis();
            if (_irAc > 50 && (now - _lastPeakTime) > 300) { // refractory period 300ms
                if (_lastPeakTime > 0) {
                    unsigned long delta = now - _lastPeakTime;
                    int instantHr = 60000 / delta;
                    if (instantHr >= HR_VALID_MIN && instantHr <= HR_VALID_MAX) {
                        _calculatedHr = (_calculatedHr == 0) ? instantHr : (int)(0.7f * _calculatedHr + 0.3f * instantHr);
                    }
                }
                _lastPeakTime = now;

                // Ratio of ratios algorithm for SpO2
                if (_irDc > 0 && _redDc > 0 && abs(_irAc) > 1.0f) {
                    float r = (_redAc / _redDc) / (_irAc / _irDc);
                    // Empirical calibration formula for MAX30102
                    int instantSpo2 = (int)(110.0f - 25.0f * r);
                    if (instantSpo2 >= SPO2_VALID_MIN && instantSpo2 <= SPO2_VALID_MAX) {
                        _calculatedSpo2 = (_calculatedSpo2 == 0) ? instantSpo2 : (int)(0.8f * _calculatedSpo2 + 0.2f * instantSpo2);
                    }
                }
            }
        }
    }
}

Max30102Data Max30102Driver::getData() const {
    Max30102Data d;
    d.isConnected = _isAvailable;
    d.fingerDetected = (_latestIr >= FINGER_THRESHOLD_IR);
    d.irValue = _latestIr;
    d.redValue = _latestRed;
    d.heartRate = d.fingerDetected ? _calculatedHr : 0;
    d.spo2 = d.fingerDetected ? _calculatedSpo2 : 0;
    if (!d.isConnected) d.qualityStatus = "SENSOR_DISCONNECTED";
    else if (!d.fingerDetected) d.qualityStatus = "SIGNAL_UNAVAILABLE";
    else d.qualityStatus = "VALID";
    return d;
}

