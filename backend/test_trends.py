from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from advisor import analyze_trend


def make_readings(device_id, moisture_values, hours_between=1):
    """Generate simulated readings in chronological order."""
    start = datetime.now(timezone.utc) - timedelta(
        hours=(len(moisture_values) - 1) * hours_between
    )

    return [
        SimpleNamespace(
            device_id=device_id,
            timestamp=start + timedelta(hours=i * hours_between),
            soil_moisture_pct=moisture,
        )
        for i, moisture in enumerate(moisture_values)
    ]


# Scenario 1: Moisture stays near 70%
# Simulate 25 hours of readings at 10-minute intervals
stable = make_readings(
    "backyard-node-02",
    [70 + (i % 3 - 1) for i in range(151)],
    hours_between=1 / 6,
)

# Scenario 2: Moisture steadily decreases
drying = make_readings(
    "backyard-node-01",
    [75, 72, 69, 65, 60],
    hours_between=6,
)

# Scenario 3: Moisture increases
wetting = make_readings(
    "backyard-test-03",
    [40, 42, 45, 48, 52],
    hours_between=6,
)

# Scenario 4: Insufficient readings
insufficient = make_readings(
    "backyard-test-04",
    [70],
)

assert analyze_trend(stable)["trend"] == "stable"
assert analyze_trend(drying)["trend"] == "decreasing"
assert analyze_trend(wetting)["trend"] == "increasing"
assert analyze_trend(insufficient)["status"] == "insufficient_data"
assert len(analyze_trend(stable)["observations"]) == 1
assert analyze_trend(stable)["data_continuous"] is True

# Simulate a 24-hour outage between two readings
outage = make_readings(
    "backyard-test-outage",
    [70, 70],
    hours_between=24,
)

outage_result = analyze_trend(outage)

assert outage_result["data_continuous"] is False
assert outage_result["max_gap_minutes"] == 1440
assert len(outage_result["observations"]) == 0

print("Outage protection:", outage_result)

for name, readings in [
    ("Stable", stable),
    ("Drying", drying),
    ("Wetting", wetting),
    ("Insufficient data", insufficient),
]:
    print(f"{name}: {analyze_trend(readings)}")

# Scenario 5: Sensor stopped reporting two hours ago
stale = make_readings(
    "backyard-test-stale",
    [70] * 151,
    hours_between=1 / 6,
)

# Shift every timestamp two hours into the past
for reading in stale:
    reading.timestamp -= timedelta(hours=2)

stale_result = analyze_trend(stale)

assert stale_result["status"] == "stale_data"
assert stale_result["observations"] == []

print("Stale sensor protection:", stale_result)

print("\nAll trend analysis tests PASSED")