# BackyardOS System Architecture

BackyardOS is organized into sensing, network, application, storage, visualization, and home-automation layers.

The production system currently uses two independent ESP32 sensor nodes. `backyard-node-01` collects four independently identified soil-probe readings and one shared BME280 environmental reading per cycle. `backyard-node-02` remains an independent single-probe node. Both send authenticated telemetry to a hosted FastAPI backend.

## Current Production Architecture

```text
                           Backyard Environment
                                     |
                  +------------------+------------------+
                  |                                     |
                  v                                     v
        +-------------------+                 +-------------------+
        | Backyard Node 01  |                 | Backyard Node 02  |
        |                   |                 |                   |
        | 4 Soil Probes     |                 | 1 Soil Probe      |
        | 1 BME280          |                 | 1 BME280          |
        | ESP32             |                 | ESP32             |
        +-------------------+                 +-------------------+
                  |                                     |
                  |  Wi-Fi / HTTPS                      |
                  |  TLS + API Key                      |
                  |                                     |
                  +------------------+------------------+
                                     |
                                     v
                          +----------------------+
                          |   FastAPI Backend    |
                          |       Render         |
                          +----------------------+
                                     |
                                  SQLModel
                                     |
                                     v
                          +----------------------+
                          | PostgreSQL Database  |
                          |      Supabase        |
                          +----------------------+
                                     |
                  +------------------+------------------+
                  |                                     |
                  v                                     v
        +-------------------+                 +-------------------+
        | React Dashboard   |                 |  Home Assistant   |
        | Render            |                 | Project Sunshine  |
        +-------------------+                 +-------------------+
```

## Sensor Node Architecture

Each BackyardOS sensor node combines an ESP32, one BME280, and one or more capacitive soil-moisture probes:

```text
          Backyard Environment
                   |
        +----------+----------+
        |                     |
        v                     v
+----------------+    +----------------+
| Soil Probe(s)  |    |     BME280     |
| Independent ID |    | Temp / RH / P  |
+----------------+    +----------------+
        |                     |
        +----------+----------+
                   |
                   v
            +-------------+
            |    ESP32    |
            | Sensor Node |
            +-------------+
```

Each sensor node operates independently and uses a unique `device_id`. Soil readings within a node use `probe_id`, so the stable identity of a soil stream is the `(device_id, probe_id)` pair.

Current device identifiers:

- `backyard-node-01`
- `backyard-node-02`

This prevents readings from different nodes or physical soil probes from being mixed in the database, dashboard, Advisor analysis, or Home Assistant.

## Hardware Connections

### Capacitive Soil-Moisture Sensors

Node 01 currently uses four probes on separate ADC inputs. Node 02 retains the original single-probe connection.

| Probe | ESP32 Connection | Status |
|---|---:|---|
| Probe 1 | GPIO35 | Verified |
| Probe 2 | GPIO34 | Verified on Node 01 |
| Probe 3 | GPIO32 | Verified on Node 01 |
| Probe 4 | GPIO33 | Verified on Node 01 |
| Probe 5 | GPIO36 / VP | Expansion position; not verified |
| Probe 6 | GPIO39 / VN | Expansion position; not verified |

All soil probes share 3.3V and GND while retaining isolated analog signal paths.

The moisture sensor produces an analog signal.

Higher ADC values indicate drier conditions.

Lower ADC values indicate wetter conditions.

### BME280 Environmental Sensor

| BME280 Connection | ESP32 Connection |
|---|---:|
| VCC | 3.3V |
| GND | GND |
| SDA | GPIO21 |
| SCL | GPIO22 |

The BME280 communicates over I2C at address `0x76`.

It provides:

- Temperature
- Relative humidity
- Atmospheric pressure

## ESP32 Sensor Node

Each ESP32 currently performs the following operations:

1. Reads each configured soil probe from its assigned ADC input.
2. Converts each raw ADC reading into a constrained, still-provisional percentage.
3. Reads temperature, humidity, and pressure from the BME280 once per cycle.
4. Connects to the configured Wi-Fi network.
5. Synchronizes UTC time through NTP.
6. Builds timestamped JSON telemetry payloads identified by `device_id` and `probe_id`.
7. Reuses the cycle's BME280 values for each probe payload on a multi-probe node.
8. Opens a validated HTTPS connection to the FastAPI backend.
9. Authenticates each request using an API key.
10. Sends each reading to `POST /readings`.
11. Retries failed telemetry requests up to three times.
12. Waits until the next ten-minute reporting interval.

### ESP32 Reliability Behavior

The firmware includes:

- Wi-Fi connection timeout handling
- Automatic Wi-Fi reconnection
- NTP resynchronization after reconnecting
- HTTPS certificate-chain validation
- API-key authentication
- Failed-request retry handling
- Persistent device identification
- Ten-minute production telemetry intervals

The ESP32 trusts the GTS Root R4 certificate authority for HTTPS validation.

Local Wi-Fi credentials, API keys, and other sensitive values are stored in `secrets.h`, which is excluded from version control.

## Sensor Telemetry Flow

```text
Sensors
   |
   v
ESP32
   |
   | Read and format telemetry
   v
JSON Payload
   |
   | Wi-Fi / HTTPS
   | TLS certificate validation
   | X-API-Key authentication
   v
POST /readings
   |
   v
FastAPI on Render
   |
   | Pydantic / SQLModel validation
   v
Supabase PostgreSQL
```

A telemetry payload includes:

- UTC timestamp
- Device ID
- Probe ID
- Raw soil-moisture value
- Calculated soil-moisture percentage
- Temperature in Celsius
- Relative humidity percentage
- Atmospheric pressure in hPa

## FastAPI Backend

The FastAPI backend runs as a hosted Render web service.

It is responsible for:

- Accepting authenticated sensor telemetry
- Validating incoming readings
- Persisting readings through SQLModel
- Retrieving recent historical telemetry
- Retrieving the latest reading from each probe
- Providing weather and forecast data
- Caching external weather responses
- Reading configuration and secrets from environment variables

### API Endpoints

#### `GET /`

Provides the root or backend health response.

#### `POST /readings`

Accepts telemetry from authorized ESP32 sensor nodes.

Requests require a valid API key in the `X-API-Key` header.

#### `GET /readings`

Returns readings from the most recent seven days.

This endpoint is used primarily by the React dashboard for charts and environmental trend analysis.

The seven-day limit reduces:

- API response size
- Database transfer volume
- Render bandwidth usage
- Supabase egress usage
- Browser processing requirements

Older readings remain stored in Supabase even though the standard endpoint does not return them.

#### `GET /readings/latest`

Returns the newest available reading for each unique `(device_id, probe_id)` pair. Legacy uploads without `probe_id` default to Probe 1.

This endpoint is intended for lightweight consumers that need current conditions without downloading historical data.

Current consumers include:

- Home Assistant
- Probe status displays
- Current-condition cards
- Future ESP32-S3 bench-top controllers

#### `GET /weather`

Returns current-weather and one-day forecast data obtained through WeatherAPI.

Weather responses are cached for 15 minutes.

## Database Architecture

```text
FastAPI
   |
   | SQLModel
   v
DATABASE_URL
   |
   +-----------------------------+
   |                             |
   v                             v
Supabase PostgreSQL          Local SQLite
Production                   Development Fallback
```

### Production Database

Supabase PostgreSQL is used for hosted production persistence.

The database stores telemetry using both `device_id` and `probe_id` to maintain separation between nodes and individual soil probes.

The production database preserves:

- Historical soil-moisture readings
- Temperature readings
- Humidity readings
- Atmospheric-pressure readings
- Timestamps
- Device identity
- Probe identity

### Local Development Database

SQLite is used when `DATABASE_URL` is not defined.

This allows backend development and testing without requiring a connection to the production Supabase database.

## Dashboard Architecture

The dashboard is built with:

- React
- Vite
- Recharts

The dashboard runs as a hosted Render application.

```text
React Dashboard
      |
      +---- GET /readings
      |         |
      |         +---- Recent seven-day sensor history
      |
      +---- GET /weather
                |
                +---- Current conditions and forecast
```

The dashboard:

- Loads readings from the most recent seven days.
- Separates telemetry by `(device_id, probe_id)`.
- Displays one compact temperature, humidity, and pressure header per node.
- Displays the newest soil reading and an independent history for each probe.
- Supports switching among probes without duplicating shared environmental displays.
- Displays historical charts.
- Supports six-hour, 24-hour, and seven-day chart views.
- Refreshes sensor data every five minutes.
- Refreshes weather data every 15 minutes.

## Backyard Advisor Architecture

Backyard Advisor adds deterministic analysis and an optional local language-model interpretation layer without changing the sensor-ingestion path.

### Hosted deterministic path

`Supabase telemetry → FastAPI Advisor endpoints → React AdvisorPanel`

The hosted FastAPI service exposes:

- `GET /advisor` for rule-based analysis of the latest reading from each device/probe pair.
- `GET /advisor/trends` for deterministic 24-hour or 72-hour trend analysis grouped by device and probe.
- `GET /advisor/analysis?days=7` for verified multi-day findings consumed by the dashboard.

Deterministic application code calculates moisture direction, range, net change, data continuity, sample sufficiency, and supported temperature relationships. These verified findings—not model-generated measurements—are the numerical source of truth.

### Local interpretation path

`/advisor/analysis → advisor_worker.py → Ollama/Mistral NeMo → advisor_validation.py → local_experiments/advisor_latest.json`

The local worker:

- Retrieves verified findings from the hosted API.
- Sends only structured findings and project context to the local model.
- Requires schema version 2 with `interpretations`, `hypotheses_to_test`, `unknowns`, and qualitative `confidence`.
- Requires exactly one interpretation per finding.
- Rejects invented IDs, altered evidence objects, malformed fields, and inconsistent durations.
- Atomically replaces the saved result only after validation succeeds.
- Preserves the last valid result when generation, networking, or validation fails.

### Current deployment boundary

Ollama and Mistral NeMo run locally on the Mac mini. The hosted Render backend does not connect to the local Ollama service. The hosted React dashboard currently displays deterministic findings from `/advisor/analysis`; the validated local language-model response remains in `local_experiments/advisor_latest.json` and is not yet published to the dashboard.

The Advisor is read-only and advisory. It does not write sensor telemetry or activate irrigation or other physical equipment.

- Retries requests during Render cold starts.
- Preserves the last successful weather response after later failures.
- Displays empty states when no readings exist for a selected time range.
- Converts stored Celsius readings to Fahrenheit for presentation.
- Supports responsive desktop and mobile layouts.

### Device Freshness States

Dashboard device status is classified as:

- `LIVE`
- `STALE`
- `OFFLINE`

Freshness is determined from the timestamp of the newest reading associated with the selected sensor node.

### Soil-Condition States

Current provisional classifications are:

- `DRY`
- `HEALTHY`
- `WET`
- `SATURATED`

These states are derived from soil-moisture percentage.

The thresholds remain provisional until they can be validated through controlled dry-down and rewatering tests in representative backyard clay soil.

## Home Assistant Architecture

BackyardOS is integrated with Home Assistant as **Project Sunshine**.

```text
Home Assistant
      |
      | Periodic REST request
      v
GET /readings/latest
      |
      v
Newest reading from each device/probe pair
      |
      v
Individual Home Assistant entities
```

Home Assistant uses the lightweight `/readings/latest` endpoint instead of downloading the full seven-day dataset.

BackyardOS entities can include:

- Per-probe soil moisture for each `(device_id, probe_id)` pair
- Node-level temperature
- Node-level humidity
- Node-level atmospheric pressure
- Probe freshness or availability

This architecture keeps the Home Assistant integration independent from the React dashboard.

## Weather Architecture

Weather information follows a separate data path from physical backyard telemetry.

```text
WeatherAPI
    |
    v
FastAPI /weather
    |
    | 15-minute cache
    v
React Dashboard
```

The weather integration provides:

- Current temperature
- Feels-like temperature
- Daily high and low
- Rain probability
- UV index
- Relative humidity
- Wind direction
- Wind speed
- Wind gusts
- Dew point
- Sunset time

WeatherAPI data provides broader local context, while the BME280 measures conditions at the physical sensor location.

## Timing and Refresh Intervals

| Component | Current Interval |
|---|---:|
| ESP32 telemetry submission | 10 minutes |
| React dashboard sensor refresh | 5 minutes |
| Dashboard weather refresh | 15 minutes |
| Backend weather cache | 15 minutes |
| Home Assistant REST scan | 5 minutes |

The dashboard may refresh more often than new ESP32 telemetry is generated. This allows device freshness and backend availability to be reevaluated without waiting for the next sensor transmission.

## Security Model

BackyardOS currently uses several security controls:

- HTTPS for ESP32-to-backend communication
- TLS certificate-chain validation
- GTS Root R4 trust anchor on the ESP32
- API-key authentication for telemetry writes
- Environment variables for backend secrets
- Local `secrets.h` for ESP32 credentials
- `.gitignore` protection for untracked secrets
- Read-only public retrieval endpoints
- Separate production and local-development database configuration

Future security improvements may include:

- API-key rotation procedures
- Per-device API credentials
- Rate limiting
- More restrictive read access
- Additional telemetry validation
- Certificate-expiration monitoring

## Reliability and Failure Handling

### Wi-Fi Interruption

If a sensor node loses Wi-Fi:

1. The ESP32 detects the missing connection.
2. The ESP32 attempts to reconnect.
3. NTP synchronization is requested again after reconnection.
4. Telemetry transmission resumes.

### Failed Telemetry Request

If an HTTPS telemetry request fails:

1. The ESP32 retries the request.
2. Up to three attempts are made.
3. If all attempts fail, the reading is not currently buffered locally.
4. The next scheduled reading is attempted normally.

Local offline buffering remains a potential future improvement.

### Render Cold Start

If the hosted backend is sleeping:

1. A dashboard request may initially fail or respond slowly.
2. The dashboard retries the request.
3. Data is displayed when the backend becomes available.

### WeatherAPI Failure

If a weather refresh fails:

1. The last successful weather response remains visible.
2. The dashboard identifies that the latest refresh failed.
3. A later scheduled refresh attempts the request again.

### Missing Sensor Data

If a probe stops reporting:

1. Its newest timestamp becomes older.
2. The dashboard transitions the probe from `LIVE` to `STALE`.
3. A longer interruption changes the probe status to `OFFLINE`.
4. Existing historical readings remain available.

## Current System Status

The complete production telemetry pipeline is operational:

```text
Two ESP32 Sensor Nodes
          |
          v
Authenticated HTTPS Telemetry
          |
          v
FastAPI on Render
          |
          v
Supabase PostgreSQL
          |
          +------------------+
          |                  |
          v                  v
React Dashboard       Home Assistant
```

Currently verified:

- Two independent ESP32 sensor nodes
- Two BME280 environmental sensors
- Four independently identified soil probes on Node 01
- One independent soil probe on Node 02
- Shared BME280 readings recorded once per Node 01 cycle and attached to each probe payload
- BME280 communication at `0x76`
- Soil sensing through GPIO35, GPIO34, GPIO32, and GPIO33 on Node 01
- NTP-based UTC timestamps
- Wi-Fi reconnection
- HTTPS telemetry
- TLS certificate validation
- API-key authentication
- FastAPI validation
- Supabase persistence
- Per-probe ingestion, persistence, latest-reading retrieval, Advisor grouping, and dashboard histories
- Lightweight latest-reading retrieval
- Home Assistant integration
- Weather and forecast integration

## Current Development Focus

BackyardOS is currently in **v0.10.0 — Outdoor Deployment**.

Current priorities are:

- Reviewing long-term Probe 1 telemetry for gaps.
- Confirming unattended reconnect behavior.
- Establishing field capacity in representative backyard clay soil.
- Refining dry, healthy, wet, and saturated thresholds.
- Comparing calibration behavior between probes.
- Monitoring long-term sensor drift.
- Completing outdoor protection for the perfboard-based assembly.
- Finishing adhesive-lined heat-shrink protection for the BME280 wiring.
- Protecting the BME280 while maintaining airflow.
- Routing the soil probe through a sealed cable gland.
- Validating outdoor Wi-Fi performance.
- Beginning outdoor deployment with USB power.

Battery or solar power will be evaluated only after the wired outdoor system is stable.

## Future Architecture

Future versions may add:

- Local ESP32 buffering during network outages
- Configurable garden-bed and plant profiles
- Deterministic environmental-hazard rules
- Prolonged dry-soil detection
- Prolonged saturation detection
- Extreme-heat and high-UV alerts
- Rain and severe-weather risk evaluation
- Agentic environmental recommendations
- Home Assistant notifications
- Multiple backyard monitoring zones
- ESP32-S3 bench-top displays and controls
- Camera-based plant-health monitoring
- Automated irrigation recommendations
- Future irrigation-controller integration
