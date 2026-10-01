
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
    