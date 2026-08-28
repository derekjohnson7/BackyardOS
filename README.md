# BackyardOS

BackyardOS is an IoT environmental monitoring system built to better understand the microclimate and soil conditions around my backyard.

The project began after repeatedly losing plants to suspected root rot caused by poor drainage in heavy clay soil. Rather than continuing to guess at soil conditions, BackyardOS collects environmental data that can eventually be used to understand drainage behavior, identify plant stress, and support better irrigation decisions.

## Current Status

BackyardOS is currently at **v0.10.0 — Outdoor Deployment**.

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
- Persist sensor readings in Supabase PostgreSQL using SQLModel.
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

The current milestone is focused on final dashboard refinement, field validation of soil-condition thresholds, stale-data handling, and preparation for outdoor deployment.

## Architecture

Sensor telemetry:

`Sensors -> ESP32 -> Wi-Fi -> HTTPS/TLS -> FastAPI -> PostgreSQL -> React Dashboard`

Weather context:

`WeatherAPI -> FastAPI -> 15-minute cache -> React Dashboard`

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
- PostgreSQL on Supabase for hosted persistence
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

## Next Steps

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
- [x] Add external weather and forecast context.
- [x] Add 15-minute weather caching and refresh.
- [x] Display last successful weather refresh time.
- [x] Add mobile probe switching for future multi-node support.
- [x] Add stale-weather handling so the last successful weather data remains visible if a refresh fails.
- [x] Add empty-state handling for filtered charts.
- [ ] Refine soil-condition thresholds using collected field data.
- [ ] Continue validating sensor trends over multi-day dry-down and rewatering cycles.

### v0.9.0 — Database Migration & Resilience
- [x] Migrate hosted PostgreSQL from Render to Supabase before the current Render database expires.
- [x] Verify historical readings after migration.
- [x] Update Render `DATABASE_URL` to point to Supabase.
- [x] Confirm ESP32 telemetry and dashboard history remain uninterrupted after migration.
- [ ] Consider local buffering on the ESP32 so readings are not lost during network outages.

### v0.10.0 — Outdoor Deployment
- [ ] Move electronics from breadboard prototype to a more durable outdoor setup.
- [ ] Design or 3D-print a weather-resistant enclosure.
- [ ] Add protected ventilation for the BME280.
- [ ] Route the soil probe through a sealed cable gland.
- [ ] Validate Wi-Fi reliability and sensor behavior outdoors.
- [ ] Begin with USB power before evaluating battery/solar operation.

### Future — Agentic Environmental Intelligence
- [ ] Add configurable plant and garden-bed profiles with different environmental needs.
- [ ] Combine soil moisture, temperature, humidity, UV, rainfall probability, and forecast data into a unified environmental context.
- [ ] Add deterministic rules for environmental hazards such as:
  - extreme heat
  - high UV exposure
  - prolonged dry soil
  - prolonged saturated soil
  - freezing conditions
  - heavy-rain or severe-weather risk
- [ ] Add an agentic AI layer that evaluates current conditions, historical trends, forecasts, and plant profiles.
- [ ] Generate prioritized recommendations for watering, drainage, heat protection, and other plant-care actions.
- [ ] Allow the agent to evaluate multiple probes or garden zones and identify which areas require attention first.
- [ ] Provide proactive alerts only when conditions warrant intervention.
- [ ] Incorporate historical dry-down and watering behavior into future recommendations.
- [ ] Track whether recommendations were followed and use the resulting sensor data to evaluate outcomes.
- [ ] Explore integrations with notification or smart-home systems for proactive alerts and future automation.

### Optional Future Expansion — Computer Vision
- [ ] Explore camera-based plant-health monitoring.
- [ ] Explore detection of visible plant stress, pests, disease, or physical damage.
- [ ] Use visual observations as an additional input to the environmental intelligence layer.