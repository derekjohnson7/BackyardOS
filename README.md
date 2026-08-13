# BackyardOS

BackyardOS is an IoT environmental monitoring system built to better understand the microclimate and soil conditions around my backyard.

The project began after repeatedly losing plants to suspected root rot caused by poor drainage in heavy clay soil. Rather than continuing to guess at soil conditions, BackyardOS collects environmental data that can eventually be used to understand drainage behavior, identify plant stress, and support better irrigation decisions.

## Current Status

BackyardOS is currently at **v0.5.0**.

The system can:

- Measure soil moisture using a capacitive moisture sensor.
- Measure temperature, humidity, and atmospheric pressure using a BME280.
- Connect an ESP32 sensor node to Wi-Fi.
- Synchronize timestamps using NTP.
- Generate timestamped environmental observations.
- Accept sensor readings through a FastAPI backend.
- Store and retrieve readings using SQLModel and SQLite.

The ESP32 sensor node and backend are currently functional as separate components.

The next milestone is to connect them so that the ESP32 automatically sends sensor readings to the FastAPI backend over HTTP.

## Architecture

Sensors -> ESP32 -> Wi-Fi/HTTP -> FastAPI -> SQLModel -> SQLite -> Dashboard

## Hardware

- ESP32 development board
- Capacitive Soil Moisture Sensor v2.0
- BME280 temperature, humidity, and pressure sensor

### Current Pin Configuration

- Soil Moisture Analog Output: GPIO35
- BME280 SDA: GPIO21
- BME280 SCL: GPIO22
- BME280 I2C Address: 0x76

## Backend

The backend uses:

- FastAPI
- SQLModel
- SQLite
- Uvicorn

Current endpoints:

- `GET /`
- `POST /readings`
- `GET /readings`

## Soil Moisture Calibration

Current prototype reference values:

- Air: ~3300
- Dry soil: ~2800
- Waterlogged soil: ~1090

These values are preliminary and will be refined through additional field testing.

## Roadmap

### v0.6.0 — Networked Telemetry Pipeline

- Send ESP32 readings to FastAPI using HTTP POST.
- Serialize sensor readings as JSON.
- Add a persistent device ID.
- Verify physical sensor readings are automatically stored in SQLite.

### v0.7.0 — Reliable Telemetry

- Handle Wi-Fi interruptions.
- Handle failed API requests.
- Add retry behavior.
- Improve timestamp and connection handling.

### v0.8.0 — Dashboard MVP

- Visualize soil moisture over time.
- Visualize temperature and humidity.
- Display recent sensor readings.
