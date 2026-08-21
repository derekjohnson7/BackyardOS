# BackyardOS

BackyardOS is an IoT environmental monitoring system built to better understand the microclimate and soil conditions around my backyard.

The project began after repeatedly losing plants to suspected root rot caused by poor drainage in heavy clay soil. Rather than continuing to guess at soil conditions, BackyardOS collects environmental data that can eventually be used to understand drainage behavior, identify plant stress, and support better irrigation decisions.

## Current Status

BackyardOS is currently at **v0.8.0 — Dashboard MVP**.

The system can:

- Measure soil moisture using a capacitive moisture sensor.
- Measure temperature, humidity, and atmospheric pressure using a BME280.
- Connect an ESP32 sensor node to Wi-Fi.
- Synchronize timestamps using NTP and transmit readings in UTC.
- Automatically reconnect after Wi-Fi interruptions.
- Retry failed telemetry requests.
- Send authenticated HTTPS telemetry using an API key.
- Validate the backend TLS certificate chain.
- Accept sensor readings through a hosted FastAPI backend.
- Persist sensor readings in Render PostgreSQL using SQLModel.
- Retrieve historical sensor readings through the API.

The complete telemetry pipeline is operational:

`Sensors -> ESP32 -> Wi-Fi -> HTTPS/TLS -> API Key Auth -> FastAPI -> PostgreSQL`

The current milestone is focused on building the first dashboard for viewing current conditions and historical sensor trends.

## Architecture

Sensors -> ESP32 -> Wi-Fi/HTTPS -> FastAPI -> SQLModel -> PostgreSQL -> Dashboard

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
- PostgreSQL on Render for hosted persistence
- SQLite as a local-development fallback
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

### v0.8.0 — Dashboard MVP

- Visualize soil moisture over time.
- Visualize temperature and humidity.
- Display recent sensor readings.
