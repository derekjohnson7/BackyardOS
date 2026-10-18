# 2026-10-17

## Multi-probe indoor setup verified

- New 50 × 70 mm perfboard has six detachable soil-probe connections, shared 3.3 V/GND, and isolated analog signal paths. Continuity checks passed.
- Four probes are connected on GPIO35, GPIO34, GPIO32, and GPIO33 through the longer cables. Independent responses and repeated upload cycles were verified indoors.
- Node 01 posts four readings per cycle with distinct probe IDs and shared BME280 measurements. Backend, Supabase persistence, and dashboard cards are working; node 02 remains separate.
- The dashboard now shows environmental readings once per node in a compact header. Each probe retains its own soil graph, with raw moisture beside the gauge.
- Six connector positions are available; only four probes have been connected and tested.

## Outdoor deployment pending

The assembly is still indoors. Additional adhesive-lined heat shrink is needed to finish the BME280 wiring before outdoor installation. Outdoor Wi-Fi and long-term weather exposure remain to be tested. No field calibration or watering recommendations have been validated.

Hardware and cable changes mark boundaries in the historical data even when the same node ID is retained.

---

# 2026-07-22

## Moisture Sensor Calibration

Air
≈3300

Dry Soil
≈2800

Waterlogged Soil
≈1090

Current Test
≈1945

Observations

- Raw ADC decreases as moisture increases.
- One moisture sensor from the kit was defective.
- Initial prototype moved from GPIO34 to GPIO35.
- Aluminum container without drainage likely exaggerates saturation.


### Initial Troubleshooting

The initial moisture sensor consistently returned a raw ADC value of `0`,
suggesting that the ESP32 was not receiving a valid analog signal.

To isolate the issue:

1. Verified all wiring between the ESP32 and the moisture sensor.
2. Replaced each jumper wire to rule out faulty connections.
3. Confirmed the sketch was reading from the correct GPIO pin.
4. Swapped the moisture sensor with a second sensor from the kit.

After replacing the sensor, the ESP32 immediately reported raw readings of
approximately `3300` in air, confirming that the original moisture sensor
was defective rather than indicating a power supply or ESP32 issue.

First BME280 Reading:
Temperature = 27.23 °C
Pressure = 988.52 hPa
Approx. Altitude = 207.92 m
Humidity = 54.91 %
