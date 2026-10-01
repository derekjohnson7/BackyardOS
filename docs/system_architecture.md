# BackyardOS System Architecture

BackyardOS is organized into sensing, network, application, storage, visualization, and home-automation layers.

The production system currently uses two independent ESP32 sensor nodes. Each node collects local environmental data and sends authenticated telemetry to a hosted FastAPI backend.

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
        | Soil Sensor       |                 | Soil Sensor       |
        | BME280            |                 | BME280            |
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

Each BackyardOS sensor node combines three primary hardware components:

```text
          Backyard Environment
                   |
        +----------+----------+
        |                     |
        v                     v
+----------------+    +----------------+
| Soil Moisture  |    |     BME280     |
| Sensor         |    | Temp / RH / P  |
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

Each sensor node operates independently and uses a unique `device_id`.

Current device identifiers:

- `backyard-node-01`
- `backyard-node-02`

This prevents readings from different physical probes from being mixed in the database, dashboard, or Home Assistant.

## Hardware Connections

### Capacitive Soil-Moisture Sensor

| Sensor Connection | ESP32 Connection |
|---|---:|
| VCC | 3.3V |
| GND | GND |
| AOUT | GPIO35 |

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

1. Reads the raw soil-moisture ADC value from GPIO35.
2. Converts the raw ADC reading into a constrained percentage.
3. Reads temperature, humidity, and pressure from the BME280.
4. Connects to the configured Wi-Fi network.
5. Synchronizes UTC time through NTP.
6. Builds a timestamped JSON telemetry payload.
7. Opens a validated HTTPS connection to the FastAPI backend.
8. Authenticates the request using an API key.
9. Sends the reading to `POST /readings`.
10. Retries failed telemetry requests up to three times.
11. Waits until the next ten-minute reporting interval.

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

Returns the newest available reading from each unique `device_id`.

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

The database stores telemetry from both sensor nodes using the `device_id` field to maintain separation between probes.

The production database preserves:

- Historical soil-moisture readings
- Temperature readings
- Humidity readings
- Atmospheric-pressure readings
- Timestamps
- Device identity

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
- Separates telemetry by `device_id`.
- Displays the newest reading for each probe.
- Supports switching between sensor nodes.
- Displays historical charts.
- Supports six-hour, 24-hour, and seven-day chart views.
- Refreshes sensor data every five minutes.
- Refreshes weather data every 15 minutes.
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
Newest reading from each probe
      |
      v
Individual Home Assistant entities
```

Home Assistant uses the lightweight `/readings/latest` endpoint instead of downloading the full seven-day dataset.

BackyardOS entities can include:

- Probe 1 soil moisture
- Probe 1 temperature
- Probe 1 humidity
- Probe 1 pressure
- Probe 2 soil moisture
- Probe 2 temperature
- Probe 2 humidity
- Probe 2 pressure
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
- Two capacitive soil-moisture sensors
- BME280 communication at `0x76`
- Soil sensing through GPIO35
- NTP-based UTC timestamps
- Wi-Fi reconnection
- HTTPS telemetry
- TLS certificate validation
- API-key authentication
- FastAPI validation
- Supabase persistence
- Multi-probe dashboard views
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
- Moving beyond the breadboard prototype.
- Selecting or designing a weather-resistant enclosure.
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
