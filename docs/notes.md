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
