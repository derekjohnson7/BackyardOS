# Soil Moisture Calibration

BackyardOS uses a capacitive soil moisture sensor connected to ESP32 
GPIO35.

Higher ADC values indicate drier conditions.
Lower ADC values indicate wetter conditions.

## Current Reference Values

- Air: ~3300
- Dry soil: ~2800
- Waterlogged soil: ~1090

The firmware currently uses:

```cpp
const int dryValue = 2800;
const int wetValue = 1090;


```

Relative moisture is calculated using:

```text
(Dry Value - Raw Reading)
------------------------- x 100
(Dry Value - Wet Value)
```

The result is constrained between 0% and 100%.

These values are preliminary and specific to the current sensor and test 
conditions.

## Limitations

- Different sensors may produce different readings.
- Soil composition can affect calibration.
- The original waterlogged test used a container without drainage.
- Field capacity has not yet been established.

## Future Calibration Work

- Establish field capacity.
- Test directly in backyard clay soil.
- Compare multiple sensors.
- Track sensor drift.
- Develop dry, normal, wet, and waterlogged thresholds.
