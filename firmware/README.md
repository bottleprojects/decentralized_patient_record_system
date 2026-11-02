# DPRMS ESP32 Cryptographic Sensor Gateway Firmware

## 1. Overview
This firmware runs on the **ESP32-WROOM-32** IoT microcontroller to provide hardware-authenticated biomedical telemetry for the Decentralized Patient Record Management System (DPRMS). It acquires real-time physiological data from:
1. **MAX30102**: Optical Photoplethysmography (PPG) sensor for Blood Oxygen Saturation (SpO2) and Pulse Rate.
2. **AD8232**: Single-Lead Electrocardiography (ECG) analog front-end for cardiac biopotential monitoring.

Every measurement packet is tagged with an incremental sequence counter, microsecond hardware timestamp, and cryptographically signed with **HMAC-SHA256** using a device-unique symmetric secret burned into the microcontroller.

---

## 2. Hardware Wiring & Pin Mapping

### A. MAX30102 Pulse Oximeter & Heart Rate Sensor (I2C)
| MAX30102 Pin | ESP32 Pin | Function | Notes |
|:---|:---|:---|:---|
| **VIN** | 3V3 | Power (3.3V) | Do not connect to 5V (damages I2C lines) |
| **GND** | GND | Ground | Common system ground |
| **SDA** | GPIO 21 | I2C Data | 4.7kΩ pull-up to 3.3V recommended |
| **SCL** | GPIO 22 | I2C Clock | 400 kHz Fast-Mode I2C |
| **INT** | GPIO 19 | Interrupt | Active Low |

### B. AD8232 Single-Lead ECG Analog Front-End
| AD8232 Pin | ESP32 Pin | Function | Notes |
|:---|:---|:---|:---|
| **3.3V** | 3V3 | Power (3.3V) | Clean analog power |
| **GND** | GND | Ground | Common system ground |
| **OUTPUT** | GPIO 36 (VP) | Analog Voltage Out | Connected to low-noise ADC1_CH0 |
| **LO+** | GPIO 34 | Leads-Off + Detect | Active High |
| **LO-** | GPIO 35 | Leads-Off - Detect | Active High |
| **SDN** | GPIO 32 | Shutdown Control | Active Low (HIGH = Enabled) |

> [!IMPORTANT]
> The AD8232 output is intentionally connected to **GPIO 36 (ADC1)**. On the ESP32, **ADC2 cannot be used when Wi-Fi is active**. Using ADC1 guarantees continuous, jitter-free analog sampling during wireless network transmissions.

---

## 3. Architecture & Firmware Modules
- `include/config.h`: Central hardware pin definitions, sampling rates, network endpoints, and compile-time pin validation checks.
- `src/device_authentication.h / .cpp`: Hardware-rooted HMAC-SHA256 signer using ESP32 `mbedtls` cryptographic engine.
- `src/max30102_driver.h / .cpp`: I2C driver for optical sampling at 100 Hz, finger-contact detection, and SpO2 calculation.
- `src/ad8232_driver.h / .cpp`: AD8232 instrumentation amplifier interface with lead-off monitoring.
- `src/telemetry_encoder.h / .cpp`: Canonical JSON serializer ensuring byte-for-byte reproducibility of signed messages.
- `src/network_manager.h / .cpp`: Wi-Fi connectivity manager with exponential backoff and HTTP/TLS client.
- `src/main.cpp`: FreeRTOS hardware timer setup running 500 Hz interrupt-driven ECG sampling and 2 Hz telemetry broadcast.

---

## 4. Build and Flashing Instructions

### Using PlatformIO (Recommended)
1. Install [VS Code](https://code.visualstudio.com/) and the [PlatformIO IDE](https://platformio.org/) extension.
2. Open the `firmware/` directory in VS Code.
3. Edit `include/config.h` to configure your Wi-Fi credentials (`WIFI_SSID`, `WIFI_PASSWORD`) and DPRMS backend URL (`BACKEND_BASE_URL`).
4. Connect the ESP32 to your workstation via USB.
5. Run:
```bash
pio run --target upload
pio device monitor -b 115200
```

### Using Arduino IDE 2.x
1. Install the **esp32 by Espressif Systems** board package (v2.0.14 or later).
2. Select **ESP32 Dev Module** under Tools > Board.
3. Set CPU Frequency: 240MHz, Flash Frequency: 80MHz, Upload Speed: 921600.
4. Open `src/main.cpp` and click **Upload**.

