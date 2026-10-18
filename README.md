# BackyardOS

BackyardOS is an IoT environmental-monitoring system built to better understand the microclimate and soil conditions around my backyard.

The project began after repeatedly losing plants to suspected root rot caused by poor drainage in heavy clay soil. Rather than continuing to guess at soil conditions, BackyardOS collects real environmental data that can be used to understand drainage behavior, identify plant stress, and support better irrigation decisions.

**Live Dashboard:** [backyardos-dash.onrender.com](https://backyardos-dash.onrender.com/)

## Current Status


BackyardOS has a working indoor monitoring pipeline, with **v0.10.0 — Outdoor Deployment** still in progress and **v0.11.0 — Backyard Advisor** development underway.

**As of October 17, 2026:** the new multi-probe perfboard is operating indoors. Four soil probes have been tested through the longer cables, with successful production uploads and separate dashboard cards. Outdoor installation is pending additional adhesive-lined heat shrink for the BME280 wiring. Outdoor reliability has not yet been verified.


The complete environmental-monitoring pipeline is operational:

`Soil Moisture Sensor + BME280 → ESP32 → Wi-Fi/HTTPS → FastAPI on Render → Supabase PostgreSQL → React Dashboard`

Two ESP32 nodes report under unique device IDs. `backyard-node-01` now collects four independent soil-probe readings and shares one BME280 environmental reading per cycle; `backyard-node-02` remains a separate single-probe node. Readings are identified by both `device_id` and `probe_id`.

The system currently supports:

- Independent soil-moisture sensing on GPIO35, GPIO34, GPIO32, and GPIO33 for the four-probe node.
- BME280 temperature, humidity, and pressure sensing over I2C.
- Multiple independently identified ESP32 sensor nodes.
- UTC timestamps synchronized through NTP.
- Automatic Wi-Fi reconnection.
- Retry handling for failed telemetry requests.
- Authenticated HTTPS telemetry using an API key.
- TLS certificate-chain validation.
- Hosted FastAPI ingestion and retrieval endpoints.
- Supabase PostgreSQL persistence through SQLModel.
- SQLite fallback for local backend development.
- Live and historical visualization through a React/Vite dashboard.
- Separate desktop and mobile views for multiple probes.
- Weather and forecast context through WeatherAPI.
- Home Assistant integration using the latest reading from each probe.





## Backyard Advisor

Backyard Advisor adds an evidence-based interpretation layer to the sensor platform.

The implemented pipeline separates deterministic measurements from AI-generated interpretation:

`Supabase telemetry → FastAPI analysis → verified findings → local advisor worker → Ollama/Mistral NeMo → response validation → local result`

Current capabilities include:

- `GET /advisor` for rule-based assessment of the latest reading from each device.
- `GET /advisor/trends` for deterministic 24-hour or 72-hour trend analysis.
- `GET /advisor/analysis?days=7` for verified multi-day moisture and temperature findings.
- Minimum-sample and sparse-data safeguards.
- Moisture direction, range, continuity, and net-change analysis.
- Temperature relationship analysis with explicit correlation limitations.
- A React dashboard panel displaying deterministic seven-day findings.
- A local Ollama worker using Mistral NeMo to interpret verified findings.
- Evidence-ID and structured-evidence validation for model responses.
- Atomic preservation of the last valid local result when generation, networking, or validation fails.
- Tests covering malformed responses, invented evidence, mismatched durations, missing fields, sparse data, and network failures.

The hosted dashboard currently displays deterministic findings from `/advisor/analysis`. The locally generated and validated model response is saved to `local_experiments/advisor_latest.json` and is not yet published to the hosted dashboard.

The local model is advisory only. It does not write sensor data or activate irrigation or other physical equipment.



## System Architecture

```text
                    Backyard Environment
                              |
              +---------------+---------------+
              |                               |
              v                               v
     +------------------+            +------------------+
     | Soil Moisture    |            |     BME280       |
     | Sensor           |            | Temp / RH / P    |
     +------------------+            +------------------+
              |                               |
              +---------------+---------------+
                              |
                              v
                     +------------------+
                     |      ESP32       |
                     |   Sensor Node    |
                     +------------------+
                              |
                       Wi-Fi / HTTPS
                              |
                     TLS + API Key
                              |
                              v
                     +------------------+
                     |     FastAPI      |
                     |      Render      |
                     +------------------+
                              |
                          SQLModel
                              |
                              v
                     +------------------+
                     |    PostgreSQL    |
                     |     Supabase     |
                     +------------------+
                              |
                              v
                     +------------------+
                     | React Dashboard  |
                     | Home Assistant   |
                     +------------------+
```

Weather and forecast data follow a separate path:

`WeatherAPI → FastAPI → 15-minute cache → React Dashboard`

## Hardware

Each sensor node uses:

- ESP32 development board
- Capacitive Soil Moisture Sensor v2.0
- BME280 temperature, humidity, and pressure sensor
- Node 01: soldered 50 × 70 mm perfboard with detachable JST connections and longer soil-probe cables
- Six soil-probe connection positions on the new board; four connected and tested
- USB power supply

Two sensor nodes are currently operating:

- `backyard-node-01`
- `backyard-node-02`

### Pin Configuration

| Component | ESP32 Connection |
|---|---:|
| Soil Probe 1 Analog Output | GPIO35 |
| Soil Probe 2 Analog Output | GPIO34 |
| Soil Probe 3 Analog Output | GPIO32 |
| Soil Probe 4 Analog Output | GPIO33 |
| Planned Soil Probe 5 (not yet verified) | GPIO36 / VP |
| Planned Soil Probe 6 (not yet verified) | GPIO39 / VN |
| BME280 SDA | GPIO21 |
| BME280 SCL | GPIO22 |
| BME280 Power | 3.3V |
| BME280 I2C Address | `0x76` |

## ESP32 Firmware

The ESP32 firmware currently:

- Reads raw soil-moisture ADC values.
- Converts raw soil readings into a constrained percentage.
- Reads temperature, humidity, and atmospheric pressure from the BME280.
- Connects to Wi-Fi.
- Synchronizes UTC time through NTP.
- Automatically attempts to reconnect after network interruptions.
- Resynchronizes time after reconnecting.
- Serializes sensor readings as JSON.
- Sends authenticated telemetry over HTTPS.
- Validates the backend TLS certificate chain.
- Retries failed telemetry requests up to three times.
- Submits telemetry every ten minutes.
- Identifies each node through `device_id` and each soil probe through `probe_id`.
- The multi-probe sketch reads the BME280 once per cycle and posts four separately identified probe readings with the same timestamp.

The four-probe sketch is in `firmware/BackyardOS_MultiProbe/`. See [multi-probe setup](docs/multi_probe_setup.md) for upload settings and verification steps.

Sensitive credentials are stored locally in `secrets.h` and are excluded from version control.

## Backend

The backend is built with:

- FastAPI
- SQLModel
- Uvicorn
- PostgreSQL on Supabase
- SQLite for local development

The production FastAPI service runs on Render and connects to Supabase through the `DATABASE_URL` environment variable.

### API Endpoints

#### `GET /`

Returns the backend health or root response.

#### `POST /readings`

Accepts authenticated ESP32 sensor telemetry.

Sensor write requests require a valid API key supplied through the `X-API-Key` header.

#### `GET /readings`

Returns sensor readings from the most recent seven days.

This endpoint supports dashboard charts and short-term environmental trend analysis while preventing the application from repeatedly transferring the complete historical database.

#### `GET /readings/latest`

Returns the newest available reading for each `(device_id, probe_id)` pair. Legacy uploads without `probe_id` default to Probe 1.

This lightweight endpoint is intended for:

- Home Assistant
- Current-condition displays
- Probe status checks
- Future bench-top controllers

#### `GET /weather`

Returns current weather and one-day forecast information retrieved through WeatherAPI.

Weather responses are cached for 15 minutes to reduce unnecessary external API requests.

## Database

Production telemetry is stored in Supabase PostgreSQL.

The original hosted database was migrated from Render PostgreSQL to Supabase without interrupting the existing backend or dashboard architecture. All 880 readings present at the time of migration were preserved, and new ESP32 telemetry continued posting successfully after the cutover.

SQLite remains available as a local-development fallback when `DATABASE_URL` is not defined.

## Dashboard

The BackyardOS dashboard is built with React, Vite, and Recharts.

It displays:

- Current soil moisture
- One compact temperature, humidity, and pressure header per node
- Separate soil gauges and historical soil charts per probe
- Raw moisture as secondary text beside each soil gauge
- Six-hour, 24-hour, and seven-day time ranges
- Probe-specific views
- Local weather and forecast context
- Device freshness status
- Soil-condition classifications
- Last successful weather refresh

Device freshness is classified as:

- `LIVE`
- `STALE`
- `OFFLINE`

Soil conditions are provisionally classified as:

- `DRY`
- `HEALTHY`
- `WET`
- `SATURATED`

The dashboard refreshes sensor data every five minutes. ESP32 nodes currently submit new readings every ten minutes.

The dashboard retains the last successfully retrieved weather data if a later weather refresh fails. It also includes retry handling for Render cold starts and empty-state handling when no chart data exists for the selected time range.

## Home Assistant Integration

BackyardOS is integrated with Home Assistant through the hosted API.

Home Assistant can retrieve the latest reading from each probe through:

```text
GET /readings/latest
```

This provides current BackyardOS conditions without downloading the full seven-day historical dataset.

The integration supports individual entities for readings such as:

- Soil moisture
- Temperature
- Humidity
- Atmospheric pressure
- Probe freshness

BackyardOS is displayed within Home Assistant as **Project Sunshine**.

## Soil-Moisture Calibration

Higher ADC values indicate drier conditions.

Lower ADC values indicate wetter conditions.

Current prototype reference values are:

| Condition | Raw ADC Value |
|---|---:|
| Air | Approximately `3300` |
| Dry soil | Approximately `2800` |
| Waterlogged soil | Approximately `1090` |

The firmware currently uses:

```cpp
const int dryValue = 2800;
const int wetValue = 1090;
```

Relative soil moisture is calculated using:

```text
(Dry Value - Raw Reading)
------------------------- x 100
(Dry Value - Wet Value)
```

The result is constrained between 0% and 100%.

These values remain preliminary and are specific to the current sensors and test conditions.

Known calibration limitations include:

- Different sensors may produce different raw readings.
- Soil composition affects sensor behavior.
- The original waterlogged test used a container without drainage.
- Field capacity has not yet been established.
- Current dashboard thresholds have not yet been validated against backyard clay soil.
- Long-term sensor drift has not yet been measured.

See [docs/calibration.md](docs/calibration.md) for additional calibration details.

## Reliability Testing

Both ESP32 nodes are being used for extended telemetry testing.

Testing currently evaluates:

- Long-duration sensor stability
- Wi-Fi reliability
- Automatic reconnection after network loss
- Telemetry recovery after reconnecting
- BME280 stability
- Soil-sensor drift
- Separation of readings by device ID
- Dashboard freshness reporting
- Backend and database usage

Node 01 now uses the new four-probe perfboard indoors. Node 02 remains independent. Hardware, cable, sensor, and calibration changes should be treated as boundaries when comparing historical readings; retaining a device ID does not establish an unchanged physical setup.

## Repository Structure

```text
BackyardOS/
├── firmware/                 # ESP32 firmware and hardware test sketches
├── backend/                 # FastAPI backend and database models
├── dashboard/               # React/Vite dashboard
├── docs/
│   ├── calibration.md
│   ├── engineering_design.md
│   ├── notes.md
│   └── system_architecture.md
├── .gitignore
├── CHANGELOG.md
└── README.md
```

## Development Milestones

### v0.1.0 — Initial Project Setup

- [x] Initialize the Git repository.
- [x] Create the project structure.
- [x] Add engineering and calibration documentation.
- [x] Establish the initial hardware plan.

### v0.2.0 — Environmental Sensor Integration

- [x] Connect the BME280.
- [x] Read temperature.
- [x] Read humidity.
- [x] Read atmospheric pressure.
- [x] Verify I2C communication at `0x76`.
- [x] Solder permanent BME280 headers.

### v0.3.0 — Unified Sensor Loop

- [x] Integrate soil moisture and BME280 readings.
- [x] Produce unified serial output.
- [x] Verify GPIO and I2C configuration.

### v0.4.0 — Networked Sensor Node

- [x] Connect the ESP32 to Wi-Fi.
- [x] Add NTP time synchronization.
- [x] Generate timestamped readings.
- [x] Separate local credentials from tracked firmware.

### v0.5.0 — Backend and Local Persistence

- [x] Build the FastAPI backend.
- [x] Create SQLModel data models.
- [x] Add SQLite persistence.
- [x] Add reading-ingestion and retrieval endpoints.

### v0.6.0 — Hosted Telemetry Pipeline

- [x] Deploy FastAPI to Render.
- [x] Add PostgreSQL persistence.
- [x] Send ESP32 telemetry over HTTPS.
- [x] Serialize readings as JSON.
- [x] Add persistent device identification.
- [x] Verify the complete hosted telemetry pipeline.

### v0.7.0 — Reliable Telemetry

- [x] Add automatic Wi-Fi reconnection.
- [x] Add failed-request retry handling.
- [x] Add API-key authentication.
- [x] Add TLS certificate validation.
- [x] Standardize stored timestamps to UTC.
- [x] Reduce telemetry frequency for long-term monitoring.

### v0.8.0 — Dashboard MVP

- [x] Build the React/Vite dashboard.
- [x] Display live sensor conditions.
- [x] Add historical trend charts.
- [x] Add six-hour, 24-hour, and seven-day filters.
- [x] Add probe freshness states.
- [x] Add soil-condition indicators.
- [x] Add responsive mobile support.
- [x] Add multiple-probe switching.
- [x] Add WeatherAPI context.
- [x] Add weather caching and refresh handling.
- [x] Add empty-state handling.
- [x] Preserve the last successful weather response after refresh failures.

### v0.9.0 — Database Migration and Resilience

- [x] Migrate production storage from Render PostgreSQL to Supabase.
- [x] Preserve existing telemetry history.
- [x] Verify new telemetry after the migration.
- [x] Maintain dashboard history through the cutover.
- [ ] Evaluate local ESP32 buffering during network outages.

### v0.10.0 — Outdoor Deployment

- [x] Assemble a second independent ESP32 sensor node.
- [x] Assign a unique device ID to Probe 2.
- [x] Verify the second BME280 at `0x76`.
- [x] Verify Probe 2 soil-moisture sensing.
- [x] Verify independent telemetry from both probes.
- [x] Add a lightweight latest-reading API endpoint.
- [x] Limit standard history responses to seven days.
- [x] Reduce dashboard polling to five minutes.
- [ ] Review long-term Probe 1 telemetry for gaps or reconnect events.
- [ ] Establish field capacity in representative backyard clay soil.
- [ ] Refine dry, healthy, wet, and saturated thresholds.
- [ ] Compare calibration behavior between probes.
- [x] Assemble and continuity-test the new soldered perfboard.
- [x] Verify four independent probes through the longer cables indoors.
- [x] Deploy multi-probe firmware, backend support, and dashboard grouping.
- [x] Confirm four successful uploads per cycle and separate probe cards.
- [x] Select a weather-resistant enclosure.
- [ ] Finish protecting the BME280 wiring when additional heat shrink arrives.
- [ ] Add protected ventilation or radiation shielding for the BME280.
- [ ] Route the soil probe through a sealed cable gland.
- [ ] Validate outdoor Wi-Fi reliability.
- [ ] Begin outdoor testing with USB power.
- [ ] Evaluate battery or solar power after the wired deployment is stable.

## Future Development

### Environmental Intelligence

Future versions may:

- Add plant and garden-bed profiles.
- Combine local telemetry with temperature, humidity, UV, rainfall probability, and forecast data.
- Detect prolonged dry or saturated soil.
- Identify extreme heat, freezing, high-UV, and severe-weather risks.
- Generate prioritized plant-care recommendations.
- Compare conditions across multiple probes or garden zones.
- Incorporate historical watering and dry-down behavior.
- Provide proactive alerts only when intervention is warranted.
- Track actions taken and evaluate their effect using later sensor data.
- Integrate environmental recommendations with Home Assistant.

### Optional Computer-Vision Expansion

Potential future computer-vision work may include:

- Camera-based plant-health monitoring.
- Detection of visible plant stress.
- Pest or disease identification.
- Physical-damage detection.
- Combining visual observations with environmental telemetry.

## Documentation

Additional project documentation is available in:

- [Multi-probe setup and deployment status](docs/multi_probe_setup.md)
- [Calibration](docs/calibration.md)
- [Engineering Design](docs/engineering_design.md)
- [Project Notes](docs/notes.md)
- [System Architecture](docs/system_architecture.md)
- [Changelog](CHANGELOG.md)

## Project Goal

The long-term goal of BackyardOS is to move from basic environmental sensing to a reliable backyard decision-support system.

Instead of reporting measurements alone, the system should eventually answer practical questions such as:

- Does this garden bed need water?
- Is the soil staying saturated for too long?
- Is a plant experiencing heat or environmental stress?
- Is incoming rain likely to create a drainage problem?
- Which backyard zone requires attention first?
- Did a previous watering or drainage recommendation improve conditions?

BackyardOS is being developed incrementally, with each stage validated before additional automation or intelligence is added.
