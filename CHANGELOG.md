# Changelog

## Version 0.1 (COMPLETE)

### Added
- Initialized Git repository
- Created GitHub repository
- Engineering Design Document
- Initial project structure
- Version 0.1 milestone

## v0.2.0 (COMPELTE)

### Added
- Integrated BME280 environmental sensor
- Added temperature readings
- Added humidity readings
- Added atmospheric pressure readings
- Verified I²C communication at address 0x76

### Fixed
- Corrected SDA/SCL wiring on ESP32
- Installed and soldered permanent BME280 headers

## v0.3.0 (COMPLETE)

### Added
- Combined capacitive soil moisture and BME280 readings in a single 
firmware loop
- Unified serial output for:
  - Raw soil moisture ADC
  - Relative soil moisture
  - Temperature
  - Relative humidity
  - Atmospheric pressure

### Verified
- Moisture sensor on GPIO35
- BME280 on I2C address 0x76
- BME280 SDA on GPIO21
- BME280 SCL on GPIO22


## v0.4.0 - Networked Sensor Node

### Added
- Wi-Fi connectivity via ESP32
- NTP time synchronization
- Timestamped environmental observations
- 10-second sensor reading interval
- Local credential management using `secrets.h`
- Example credential configuration with `secrets.example.h`

### Verified
- ESP32 successfully connects to 2.4 GHz IoT network
- NTP returns correct local timestamp
- Soil moisture, temperature, humidity, and pressure readings operate alongside Wi-Fi
- Wi-Fi credentials excluded from version control
