# Changelog

All notable changes to BackyardOS are documented in this file.

## v0.10.0 — Outdoor Deployment

**Status:** In progress

### Added

- Assembled a second independent ESP32 sensor node.
- Assigned the second node the device ID `backyard-node-02`.
- Integrated a second BME280 environmental sensor.
- Integrated a second capacitive soil-moisture sensor.
- Added `GET /readings/latest` to return the newest reading from each sensor node.
- Added support for lightweight Home Assistant and current-status requests.

### Improved

- Limited `GET /readings` responses to readings from the most recent seven days.
- Reduced unnecessary database reads and API response sizes.
- Reduced dashboard sensor polling from every 30 seconds to every five minutes.
- Reduced expected Render and Supabase bandwidth usage.
- Improved support for multiple independently identified sensor probes.

### Verified

- Confirmed Probe 2 Wi-Fi connectivity on a separate ESP32.
- Confirmed BME280 I2C communication at address `0x76`.
- Verified the second BME280 chip ID as `0x60`.
- Verified temperature, humidity, and atmospheric-pressure readings through the complete BackyardOS firmware.
- Verified Probe 2 soil-moisture sensing through GPIO35.
- Verified authenticated telemetry from `backyard-node-02` reaches the hosted FastAPI backend.
- Verified Probe 2 readings persist to Supabase PostgreSQL under a separate device ID.
- Confirmed Probe 1 and Probe 2 can operate simultaneously without mixing telemetry.
- Confirmed both probes can recover and resume telemetry after Wi-Fi interruptions.
- Confirmed `/readings/latest` returns one current reading per device.
- Confirmed the dashboard continues loading current and historical data after the seven-day API limit was introduced.

### In Progress

- Monitoring Probe 1 during extended unattended operation.
- Reviewing long-duration telemetry for gaps and reconnect events.
- Testing Probe 2 Wi-Fi reliability at increasing distances from the router.
- Comparing soil-sensor behavior between Probe 1 and Probe 2.
- Establishing field capacity in representative backyard clay soil.
- Refining dry, healthy, wet, and saturated soil thresholds.
- Preparing the sensor electronics for a more durable outdoor assembly.
- Evaluating weather-resistant enclosure options.
- Evaluating protected BME280 ventilation and radiation-shield options.
- Planning a sealed cable entry for the soil-moisture probe.

### Notes

- Probe 1 remains active as the primary reference node.
- Probe 2 is being used for additional reliability, calibration, and deployment testing.
- Production telemetry remains on a ten-minute interval.
- The dashboard currently retrieves sensor data every five minutes.
- `GET /readings` currently returns a maximum of seven days of telemetry.
- Longer historical data remains stored in Supabase even though it is not returned by the standard readings endpoint.
- Initial outdoor deployment will use USB power before battery or solar operation is evaluated.

---

## v0.9.0 — Database Migration and Resilience

**Status:** Complete

### Added

- Migrated the BackyardOS production database from Render PostgreSQL to Supabase PostgreSQL.
- Preserved all existing sensor telemetry during the migration.
- Updated the Render FastAPI backend to connect to Supabase through the existing `DATABASE_URL` configuration.

### Improved

- Removed dependence on Render’s expiring PostgreSQL instance.
- Retained the existing backend and dashboard architecture while changing the production database provider.
- Preserved historical chart continuity across the migration.

### Verified

- Confirmed all 880 existing sensor readings were migrated successfully.
- Verified the hosted dashboard loaded historical data correctly after the cutover.
- Verified new ESP32 telemetry was written to Supabase.
- Verified newly written telemetry appeared through the production dashboard.
- Confirmed the production pipeline:

  `ESP32 → Render FastAPI → Supabase PostgreSQL → React Dashboard`

### Notes

- An initial local migration attempt using Homebrew `pg_dump` was blocked by a PostgreSQL client/server version mismatch and macOS package compatibility.
- The migration was completed successfully using a Supabase PostgreSQL migration notebook in Google Colab.
- The previous Render PostgreSQL instance was temporarily retained as a rollback safeguard.
- SQLite remains available as a local-development fallback.
- Local ESP32 buffering during network outages remains a possible future resilience improvement.

---

## v0.8.0 — Dashboard MVP

**Status:** Complete

### Added

- Built a React/Vite dashboard for live and historical sensor telemetry.
- Added soil-moisture, temperature, humidity, and atmospheric-pressure readouts.
- Added Recharts-based historical trend visualization.
- Added six-hour, 24-hour, and seven-day chart filters.
- Added automatic dashboard sensor-data refresh.
- Added retry handling for Render cold starts.
- Added persistent backend URL configuration using `localStorage` with a production environment fallback.
- Added node freshness states:
  - `LIVE`
  - `STALE`
  - `OFFLINE`
- Added provisional soil-condition classifications:
  - `DRY`
  - `HEALTHY`
  - `WET`
  - `SATURATED`
- Added Fahrenheit temperature display while retaining Celsius in stored telemetry.
- Added metric-specific chart scaling.
- Added responsive mobile layout.
- Added mobile switching between multiple sensor probes.
- Added WeatherAPI integration through the FastAPI backend.
- Added `GET /weather`.
- Added one-day forecast data.
- Added current temperature and feels-like temperature.
- Added daily high and low temperatures.
- Added rain probability.
- Added UV index.
- Added weather-station humidity.
- Added wind direction, wind speed, and gust information.
- Added dew point.
- Added sunset time.
- Added 15-minute backend weather caching.
- Added 15-minute automatic weather refresh.
- Added the timestamp of the last successful weather refresh.
- Added stale-weather handling.
- Added empty-state handling for filtered charts.

### Improved

- Added external weather context alongside locally measured backyard conditions.
- Preserved the last successful weather response when a later refresh failed.
- Improved the Local Forecast card layout.
- Improved responsive dashboard presentation.
- Improved UTC and local timestamp handling.
- Improved support for multiple sensor nodes.

### Fixed

- Restored `GET /readings` after it was unintentionally removed during weather-backend development.
- Corrected dashboard syntax errors introduced during weather-display changes.
- Corrected a dashboard spelling error.

### Testing

- Began continuous multi-day telemetry collection using controlled soil samples.
- Began observing soil dry-down and rewatering behavior.
- Verified six-hour, 24-hour, and seven-day chart filtering.
- Verified mobile probe switching.
- Verified stale and offline device states.
- Verified weather-data caching and refresh behavior.
- Verified empty-state behavior when no data exists for a selected range.

### Notes

- Soil-condition thresholds remain provisional.
- Collected data will be used to evaluate sensor stability, dry-down behavior, and field thresholds.
- Temperature is stored and transmitted in Celsius.
- Fahrenheit conversion occurs only in the dashboard presentation layer.
- The original dashboard refresh interval was 30 seconds and was later increased to five minutes in v0.10.0.

---

## v0.7.0 — Reliable Telemetry

**Status:** Complete

### Added

- Added automatic Wi-Fi reconnection.
- Added retry handling for failed telemetry requests.
- Added API-key authentication using the `X-API-Key` request header.
- Added HTTPS certificate validation using the GTS Root R4 trust anchor.
- Standardized ESP32 timestamps to UTC.
- Reduced telemetry frequency from development timing to a ten-minute production interval.

### Improved

- Sensor telemetry now retries failed POST requests up to three times.
- Wi-Fi connectivity is checked before telemetry transmission.
- The ESP32 attempts to restore Wi-Fi connectivity when disconnected.
- NTP synchronization is requested again after Wi-Fi reconnection.
- Sensor write requests are rejected unless a valid API key is supplied.
- HTTPS connections validate the backend certificate chain.
- Telemetry timing was adjusted for long-term monitoring.

### Verified

- Verified successful ESP32 reconnection after Wi-Fi loss.
- Verified failed HTTPS requests are retried.
- Verified authenticated telemetry returns `200 OK`.
- Verified requests without the required API key are rejected.
- Verified UTC timestamps are generated by the ESP32.
- Verified HTTPS certificate validation against the hosted Render backend.
- Verified sensor readings continue to persist in PostgreSQL.
- Verified the reliable telemetry pipeline:

  `Sensors → ESP32 → Wi-Fi → HTTPS/TLS → API Key Authentication → FastAPI → PostgreSQL`

### Notes

- The telemetry interval is ten minutes.
- UTC provides a consistent time standard across dashboards and analytics.
- The ESP32 trusts the GTS Root R4 certificate authority.
- The root certificate may require future updates if the hosted backend changes certificate authorities.

---

## v0.6.0 — Networked Telemetry Pipeline

**Status:** Complete

### Added

- Deployed the FastAPI backend to Render.
- Added hosted PostgreSQL persistence.
- Added environment-based database configuration using `DATABASE_URL`.
- Added PostgreSQL support through `psycopg`.
- Added HTTPS telemetry transmission from the ESP32.
- Added JSON serialization of environmental readings.
- Added the persistent sensor ID `backyard-node-01`.
- Added automatic sensor uploads to `POST /readings`.
- Added Wi-Fi connection timeout behavior to prevent indefinite blocking.

### Verified

- Verified the ESP32 connects to Wi-Fi.
- Verified NTP timestamps are generated by the sensor node.
- Verified real soil-moisture, temperature, humidity, and pressure readings are transmitted over HTTPS.
- Verified FastAPI validates incoming telemetry.
- Verified PostgreSQL persists sensor readings.
- Verified `GET /readings` returns stored physical sensor observations.
- Verified the complete telemetry pipeline:

  `Sensors → ESP32 → Wi-Fi → HTTPS/JSON → FastAPI → PostgreSQL`

### Fixed

- Diagnosed persistent Wi-Fi authentication and association failures on the original ESP32.
- Tested multiple networks, firmware versions, and a second ESP32 to isolate the failure.
- Replaced the failing ESP32 board.
- Restored network connectivity.
- Corrected the soil-moisture sensor connection from GPIO32 to GPIO35.

### Notes

- SQLite remains available when `DATABASE_URL` is not defined.
- Hosted persistence originally used Render PostgreSQL.
- HTTPS initially used `WiFiClientSecure::setInsecure()`.
- TLS certificate validation was added in v0.7.0.

---

## v0.5.0 — Backend and Local Data Persistence

**Status:** Complete

### Added

- Built a FastAPI backend.
- Added SQLModel data models.
- Added SQLite persistence.
- Added `POST /readings`.
- Added `GET /readings`.
- Added automatic database initialization.
- Added Python dependency management through `requirements.txt`.

### Verified

- Verified the backend starts locally.
- Verified sensor-reading records can be created.
- Verified stored readings can be retrieved.
- Verified SQLite data persists between backend restarts.

### Notes

- This milestone established the local software foundation used by the later hosted telemetry pipeline.

---

## v0.4.0 — Networked Sensor Node

**Status:** Complete

### Added

- Added ESP32 Wi-Fi connectivity.
- Added NTP time synchronization.
- Added timestamped environmental readings.
- Added a ten-second development reading interval.
- Added local credential management through `secrets.h`.

### Verified

- Verified the ESP32 connects to the configured Wi-Fi network.
- Verified successful NTP synchronization.
- Verified timestamped sensor output through the serial monitor.

### Notes

- The ten-second development interval was later changed to ten minutes for long-term monitoring.
- `secrets.h` remains excluded from version control.

---

## v0.3.0 — Unified Sensor Loop

**Status:** Complete

### Added

- Combined soil-moisture and BME280 readings in one firmware loop.
- Added unified serial output for environmental readings.

### Verified

- Verified the soil-moisture sensor on GPIO35.
- Verified the BME280 at I2C address `0x76`.
- Verified SDA on GPIO21.
- Verified SCL on GPIO22.
- Verified simultaneous soil-moisture, temperature, humidity, and pressure readings.

---

## v0.2.0 — Environmental Sensor Integration

**Status:** Complete

### Added

- Integrated the BME280 environmental sensor.
- Added temperature readings.
- Added humidity readings.
- Added atmospheric-pressure readings.
- Added I2C scanner sketches for sensor troubleshooting.

### Fixed

- Corrected SDA and SCL wiring.
- Replaced unreliable friction-fit connections.
- Installed and soldered permanent BME280 headers.

### Verified

- Verified BME280 communication at I2C address `0x76`.
- Verified the BME280 chip ID.
- Verified stable temperature, humidity, and pressure output.

---

## v0.1.0 — Initial Project Setup

**Status:** Complete

### Added

- Initialized the local Git repository.
- Created the GitHub repository.
- Created the initial project structure.
- Added the backend directory.
- Added the dashboard directory.
- Added the documentation directory.
- Added engineering-design documentation.
- Added calibration documentation.
- Added project notes.
- Added system-architecture documentation.
- Added `.gitignore`.
- Added the initial README
