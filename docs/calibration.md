# Moisture Calibration

Version 0.1

Dry Reference
~2800

Field Capacity
TBD

Waterlogged
~1090

Formula

...

Future Improvements

...

### BME280 Bring-Up Notes

- Initial testing used friction-fit header pins before soldering.
- I²C scanner reported either no devices or inconsistent addresses.
- Random addresses indicated an unstable electrical connection rather than 
a software issue.
- Next step: solder headers and rerun I²C scan before further software 
debugging.
