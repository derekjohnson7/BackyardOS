
from datetime import datetime, timezone


def analyze_reading(reading):
    """
    Analyze one BackyardOS sensor reading.

    Initial thresholds are provisional and must be
    validated against actual backyard soil conditions.
    """

    observations = []

    # Check whether the sensor reading is current
    timestamp = reading.timestamp

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    age_minutes = (
        datetime.now(timezone.utc) - timestamp
    ).total_seconds() / 60

    if age_minutes >= 30:
        return {
            "device_id": reading.device_id,
            "timestamp": reading.timestamp.isoformat(),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "observations": [{
                "category": "connectivity",
                "severity": "caution",
                "message": (
                    "Sensor data is outdated. Current "
                    "environmental conditions cannot "
                    "be assessed reliably."
                ),
            }],
            "observation_count": 1,
        }

    moisture = reading.soil_moisture_pct
    temperature_f = reading.temperature_c * 9 / 5 + 32

    # Soil moisture observations
    if moisture < 30:
        observations.append({
            "category": "soil",
            "severity": "info",
            "message": (
                "Soil moisture is below the provisional "
                "dry threshold. Check soil conditions "
                "before deciding whether to water."
            ),
        })

    elif moisture >= 85:
        observations.append({
            "category": "soil",
            "severity": "caution",
            "message": (
                "Soil moisture is above the provisional "
                "saturation threshold. Monitor drainage "
                "and avoid unnecessary watering."
            ),
        })

    # Temperature observations
    if temperature_f >= 100:
        observations.append({
            "category": "temperature",
            "severity": "caution",
            "message": (
                "Air temperature is at least 100°F. "
                "Monitor plants for heat stress."
            ),
        })

    elif temperature_f <= 32:
        observations.append({
            "category": "temperature",
            "severity": "caution",
            "message": (
                "Freezing temperatures detected. "
                "Check cold-sensitive plants."
            ),
        })

    return {
        "device_id": reading.device_id,
        "timestamp": reading.timestamp.isoformat(),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "observations": observations,
        "observation_count": len(observations),
    }

def analyze_trend(readings):
    """
    Analyze moisture trends from historical sensor readings.

    Readings must be ordered from oldest to newest.
    Returns a summary without modifying any data.
    """
    if len(readings) < 2:
        return {
            "status": "insufficient_data",
            "message": "Not enough readings to determine a trend."
        }

    first = readings[0]
    last = readings[-1]

    # Ensure the latest reading is recent enough to trust
    latest_timestamp = last.timestamp

    if latest_timestamp.tzinfo is None:
        latest_timestamp = latest_timestamp.replace(
            tzinfo=timezone.utc
        )

    age_minutes = (
        datetime.now(timezone.utc) - latest_timestamp
    ).total_seconds() / 60

    if age_minutes >= 30:
        return {
            "status": "stale_data",
            "device_id": last.device_id,
            "message": (
                "Latest sensor reading is outdated. "
                "Current moisture trends cannot be "
                "assessed reliably."
            ),
            "observations": [],
        }
    moisture_start = first.soil_moisture_pct
    moisture_end = last.soil_moisture_pct

    moisture_change = round(
        moisture_end - moisture_start, 2
    )

    average_moisture = round(
        sum(r.soil_moisture_pct for r in readings)
        / len(readings),
        2
    )

    if moisture_change >= 5:
        trend = "increasing"
    elif moisture_change <= -5:
        trend = "decreasing"
    else:
        trend = "stable"
        
    # Check for persistent elevated moisture
    moisture_values = [
        r.soil_moisture_pct for r in readings
    ]

    duration_hours = (
        last.timestamp - first.timestamp
    ).total_seconds() / 3600

    moisture_range = (
        max(moisture_values) - min(moisture_values)
    )

    observations = []

    # Verify that readings adequately cover the period.
    # BackyardOS normally reports every 10 minutes.
    max_gap_minutes = max(
        (
            readings[i].timestamp - readings[i - 1].timestamp
        ).total_seconds() / 60
        for i in range(1, len(readings))
    )

    data_continuous = max_gap_minutes <= 30

    if (
        data_continuous
        and min(moisture_values) >= 65
    ):
        if duration_hours >= (72 - 20 / 60):
            observations.append({
                "category": "soil",
                "severity": "caution",
                "message": (
                    "Soil moisture has remained above the elevated-moisture "
                    "threshold for approximately 72 hours."
                ),
                "recommendation": (
                    "Check soil moisture at multiple depths and inspect drainage. "
                    "Although moisture may be gradually decreasing, verify soil "
                    "conditions before watering again."
                ),
            })

        elif duration_hours >= (24 - 20 / 60):
            observations.append({
                "category": "soil",
                "severity": "caution",
                "message": (
                    "Soil moisture has remained elevated "
                    "with little variation for approximately "
                    "24 hours."
                ),
                "recommendation": (
                    "Check moisture below the soil surface "
                    "and inspect drainage before watering "
                    "again."
                )
            })

    return {
        "status": "ok",
        "device_id": last.device_id,
        "reading_count": len(readings),
        "average_moisture_pct": average_moisture,
        "moisture_change_pct": moisture_change,
        "trend": trend,
        "duration_hours": round(duration_hours, 1),
        "observations": observations,
        "max_gap_minutes": round(max_gap_minutes, 1),
        "data_continuous": data_continuous,
        "minimum_moisture_pct": round(min(moisture_values), 2),
        "maximum_moisture_pct": round(max(moisture_values), 2),
        "moisture_range_pct": round(moisture_range, 2),
    }