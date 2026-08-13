# Soil Moisture Calibration

BackyardOS uses a capacitive soil moisture sensor connected to ESP32 GPIO35.

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

