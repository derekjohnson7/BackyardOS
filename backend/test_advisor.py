
from datetime import datetime, timezone
from types import SimpleNamespace

from advisor import analyze_reading


test_cases = [
    ("Dry soil", 22, 30),
    ("Healthy range", 48, 25),
    ("Saturated soil", 92, 28),
    ("Extreme heat", 45, 40),
    ("Freezing", 45, -2),
]

for name, moisture, temperature_c in test_cases:
    reading = SimpleNamespace(
        device_id="backyard-test-01",
        timestamp=datetime.now(timezone.utc),
        soil_moisture_pct=moisture,
        temperature_c=temperature_c,
    )

    result = analyze_reading(reading)

    print(f"\nTEST: {name}")
    print(f"Observations: {result['observation_count']}")

    for observation in result["observations"]:
        print(
            f"  [{observation['severity']}] "
            f"{observation['message']}"
        )
