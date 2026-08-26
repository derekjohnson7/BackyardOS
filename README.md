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
- Display live and historical sensor data in a React/Vite dashboard.
- Automatically reconnect to the saved backend URL on page load.
- Auto-refresh dashboard data every 30 seconds.
- Retry dashboard requests during Render cold starts.
- Retrieve local weather and forecast context through WeatherAPI.
- Display current temperature, feels-like temperature, daily high/low, rain chance, UV index, humidity, wind, dew point, and sunset.
- Cache external weather responses for 15 minutes to reduce unnecessary API calls.
- Refresh dashboard weather data every 15 minutes.
- Display the timestamp of the last successful weather refresh.
- Support mobile switching between multiple future sensor probes.

The complete telemetry pipeline is operational:

Sensor telemetry:

`Sensors -> ESP32 -> Wi-Fi -> HTTPS/TLS -> FastAPI -> PostgreSQL -> React Dashboard`

Weather context:

`WeatherAPI -> FastAPI -> 15-minute cache -> React Dashboard`

The current milestone is focused on refining the dashboard with improved timestamp handling, plant-health indicators, and additional environmental context.

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
- `GET /weather`

## Soil Moisture Calibration

Current prototype reference values:

- Air: ~3300
- Dry soil: ~2800
- Waterlogged soil: ~1090

These values are preliminary and will be refined through additional field testing.

## Roadmap

### v0.8.0 — Dashboard MVP

- [x] Build React/Vite dashboard foundation.
- [x] Display soil moisture, temperature, humidity, and pressure.
- [x] Visualize historical sensor trends.
- [x] Connect dashboard to hosted FastAPI backend.
- [x] Add automatic refresh and backend retry handling.
- [x] Improve UTC/local timestamp handling.
- [x] Add node freshness states: LIVE, STALE, and OFFLINE.
- [x] Add soil-condition status indicators.
- [x] Add 6H, 24H, and 7D time-range controls.
- [x] Convert dashboard temperature display from Celsius to Fahrenheit.
- [x] Add metric-specific chart scaling.
- [x] Verify responsive mobile layout.
- [ ] Add empty-state handling for filtered charts.
- [ ] Refine soil-condition thresholds using collected field data.