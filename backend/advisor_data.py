"""Data preparation helpers for Backyard Advisor."""

from collections import defaultdict
from datetime import datetime


def prepare_sensor_readings(readings):
    """Convert sensor records into standardized dictionaries."""
    prepared = []

    for reading in readings:
        if isinstance(reading, dict):
            record = reading
        else:
            record = {
                "device_id": reading.device_id,
                "timestamp": reading.timestamp,
                "soil_moisture_pct": reading.soil_moisture_pct,
                "temperature_c": reading.temperature_c,
            }

        timestamp = record["timestamp"]

        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()

        prepared.append({
            "device_id": record["device_id"],
            "timestamp": timestamp,
            "soil_moisture_pct": record["soil_moisture_pct"],
            "temperature_c": record["temperature_c"],
        })

    return sorted(
        prepared,
        key=lambda record: (
            record["device_id"],
            record["timestamp"],
        ),
    )


def prepare_moisture_inputs(readings):
    """
    Build summaries and daily histories for moisture analysis.

    Expects standardized readings from prepare_sensor_readings().
    """
    devices = defaultdict(list)

    for reading in readings:
        if (
            reading.get("device_id")
            and reading.get("soil_moisture_pct") is not None
        ):
            devices[reading["device_id"]].append(reading)

    summaries = []
    histories = []

    for device_id, records in sorted(devices.items()):
        records = sorted(
            records,
            key=lambda record: record["timestamp"],
        )

        values = [
            float(record["soil_moisture_pct"])
            for record in records
        ]

        summaries.append({
            "device_id": device_id,
            "reading_count": len(records),
            "first_timestamp": records[0]["timestamp"],
            "last_timestamp": records[-1]["timestamp"],
            "average_moisture_pct": round(
                sum(values) / len(values), 2
            ),
            "minimum_moisture_pct": round(min(values), 2),
            "maximum_moisture_pct": round(max(values), 2),
            "net_change_percentage_points": round(
                values[-1] - values[0], 2
            ),
        })

        daily = defaultdict(list)

        for record in records:
            day = record["timestamp"][:10]
            daily[day].append(
                float(record["soil_moisture_pct"])
            )

        histories.append({
            "device_id": device_id,
            "daily_averages": [
                {
                    "date": day,
                    "average_moisture_pct": round(
                        sum(day_values) / len(day_values), 2
                    ),
                    "reading_count": len(day_values),
                }
                for day, day_values in sorted(daily.items())
            ],
        })

    return summaries, histories