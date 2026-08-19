# BackyardOS System Architecture

BackyardOS is organized into separate sensing, network, backend, storage, and visualization layers.

## Current Architecture

```text
                         Backyard Environment
                     |
        +------------+------------+
        |                         |
        ▼                         ▼
+----------------+        +----------------+
| Soil Moisture  |        |     BME280     |
|     Sensor     |        | Temp / RH / P  |
+----------------+        +----------------+
        |                         |
        +------------+------------+
                     |
                     ▼
              +-------------+
              |    ESP32    |
              | Sensor Node |
              +-------------+
                     |
              Wi-Fi / HTTPS
                     |
              TLS + API Key
                     |
                     ▼
              +-------------+
              |   FastAPI   |
              |   Render    |
              +-------------+
                     |
                  SQLModel
                     |
                     ▼
              +-------------+
              | PostgreSQL  |
              |   Render    |
              +-------------+
                     |
                     ▼
              +-------------+
              |  Dashboard  |
              |   v0.8.0    |
              +-------------+
```

## Current Components

### ESP32 Sensor Node

The ESP32 currently:

- Reads soil moisture.
- Reads temperature, humidity, and pressure.
- Connects to Wi-Fi.
- Automatically attempts reconnection after network loss.
- Synchronizes UTC time using NTP.
- Generates timestamped environmental readings.
- Sends telemetry over HTTPS.
- Authenticates write requests using an API key.
- Validates the backend TLS certificate chain.
- Retries failed telemetry requests up to three times.
- Sends readings every 10 minutes.

### FastAPI Backend

The backend currently:

- Runs as a hosted Render web service.
- Accepts authenticated sensor readings through `POST /readings`.
- Validates incoming telemetry.
- Provides historical readings through `GET /readings`.
- Uses SQLModel for persistence.
- Reads configuration and secrets from environment variables.

### Database

Render PostgreSQL is used for hosted persistent storage.

SQLite remains available as a local-development fallback when `DATABASE_URL` is not defined.

## Current System Status

The full telemetry pipeline is operational:

`Sensors -> ESP32 -> Wi-Fi -> HTTPS/TLS -> API Key Auth -> FastAPI -> SQLModel -> PostgreSQL`

The current development focus is **v0.8.0 — Dashboard MVP**, which will provide visualization of current and historical environmental conditions.
