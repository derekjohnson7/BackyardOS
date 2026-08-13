# Changelog

## v0.1.0 — Initial Project Setup (COMPLETE)

### Added
- Initialized Git repository.
- Created GitHub repository.
- Created initial project structure.
- Added engineering design documentation.
- Added calibration documentation.

## v0.2.0 — Environmental Sensor Integration (COMPLETE)

### Added
- Integrated BME280 environmental sensor.
- Added temperature readings.
- Added humidity readings.
- Added atmospheric pressure readings.
- Verified I2C communication at address `0x76`.

### Fixed
- Corrected SDA/SCL wiring.
- Installed and soldered permanent BME280 headers.

## v0.3.0 — Unified Sensor Loop (COMPLETE)

### Added
- Combined soil moisture and BME280 readings in one firmware loop.
- Added unified serial output.

### Verified
- Moisture sensor on GPIO35.
- BME280 on address `0x76`.
- SDA on GPIO21.
- SCL on GPIO22.

## v0.4.0 — Networked Sensor Node (COMPLETE)

### Added
- Wi-Fi connectivity.
- NTP time synchronization.
- Timestamped environmental readings.
- 10-second reading interval.
- Local credential management using `secrets.h`.

## v0.5.0 — Backend & Data Persistence (COMPLETE)

### Added
- FastAPI backend.
- SQLModel data models.
- SQLite persistence.
- `POST /readings`.
- `GET /readings`.
- Automatic database initialization.
- Dependency management through `requirements.txt`.

## Next Milestone

### v0.6.0 — Networked Telemetry Pipeline

- Connect ESP32 directly to FastAPI.
- Send readings as JSON.
- Add persistent device ID.
- Store physical sensor readings automatically in SQLite.
