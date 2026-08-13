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
                     | Wi-Fi
                     |
                     | HTTP / JSON
                     ▼
              +-------------+
              |   FastAPI   |
              |   Backend   |
              +-------------+
                     |
                     | SQLModel
                     ▼
              +-------------+
              |   SQLite    |
              |  Database   |
              +-------------+
                     |
                     ▼
              +-------------+
              |  Dashboard  |
              |   Planned   |
              +-------------+
```

## Current Components

### ESP32 Sensor Node

The ESP32 currently:

- Reads soil moisture.
- Reads temperature, humidity, and pressure.
- Connects to Wi-Fi.
- Synchronizes time using NTP.
- Prints timestamped readings to Serial.

### FastAPI Backend

The backend currently:

- Accepts sensor readings.
- Validates incoming data.
- Stores readings in SQLite.
- Retrieves historical readings.

### Database

SQLite is used for local persistence through SQLModel.

## Current System Status

Working:

Sensors -> ESP32 -> Serial Output

Working separately:

API Request -> FastAPI -> SQLModel -> SQLite

Not yet connected:

ESP32 -> HTTP POST -> FastAPI

Connecting these two systems is the goal of v0.6.0.
