# Four probes on one ESP32

Probe IDs 1–4 use GPIO35, GPIO34, GPIO32, GPIO33 respectively. BME280 SDA uses
GPIO21 and SCL uses GPIO22. Power off before changing wiring.

## Current deployment status — October 17, 2026

Backend and dashboard support are deployed. The multi-probe sketch has been uploaded to the physical ESP32 and four probes have produced successful HTTP 200 uploads, persisted records, and separate dashboard cards over repeated cycles indoors.

The six-connection perfboard and four longer probe cable paths passed continuity checks. Four probes are currently connected and tested; positions 5 and 6 are expansion capacity only.

**Outdoor installation is pending additional adhesive-lined heat shrink for the BME280 wiring.** Outdoor Wi-Fi and weather-exposure reliability have not been verified. Soil percentages remain provisional.

The dashboard presents shared temperature, humidity, and pressure once per node in a compact header, with individual soil gauges/charts below. Environmental values remain repeated in stored probe rows for compatibility; the display does not rewrite or average them.

## Deploy backend and dashboard first

Backend startup adds `sensorreading.probe_id INTEGER NOT NULL DEFAULT 1` if
missing. Existing rows and old firmware uploads remain Probe 1. No rows are
deleted. Use your normal database backup before deployment. The database role
needs ALTER permission. If startup reports permission denied, run this in
Supabase SQL Editor, then restart:

```sql
ALTER TABLE public.sensorreading
  ADD COLUMN IF NOT EXISTS probe_id INTEGER NOT NULL DEFAULT 1;
```

Dashboard cards/charts and Advisor histories are separated by node AND probe.
`/readings/latest`, `/advisor`, and `/advisor/trends` now return an item per pair.
Other API consumers must also use both fields to group readings.

## Upload the new sketch

1. Open `firmware/BackyardOS_MultiProbe/BackyardOS_MultiProbe.ino` in Arduino.
   Copy your private `secrets.h` from the old sketch into this new folder.
   Do not commit it. Use ESP32 Dev Module and the connected serial port.
2. Keep `UPLOAD_ENABLED = false`. Upload, then use Serial Monitor at 115200.
   Four probes print every six seconds with WiFi active and database uploads off.
3. Confirm `DEVICE_ID` is `backyard-node-01`, with the old node 01 powered off.
   Retain the same physical Probe 1 to continue its history; document changes
   in physical sensor or calibration as boundaries in that history.
4. Before enabling uploads, confirm the deployed OpenAPI SensorReadingCreate
   schema contains `probe_id`. An old backend may ignore that field and mix
   histories. Deploy the new backend and dashboard before continuing.
5. Change `UPLOAD_ENABLED` to `true` and upload again. The interval automatically
   switches to ten minutes. Each cycle makes four `/readings` POSTs with separate
   `probe_id` values, one timestamp, and shared BME280 values read once that cycle.
   Confirm four successful responses and four node 01 probe cards after refresh.

## Limits

- Per-probe calibration entries inherit 2800 dry / 1090 wet as placeholders.
  Raw inputs were tested; new probe percentages are not yet calibrated.
- The sketch was uploaded and tested on the physical ESP32 using the Mac.
  Automated firmware compilation was not performed in this development workspace.
- Non-finite BME280 values skip uploads. Plausible-looking faulty values still
  need separate quality checks and recovery work.
- Shared environmental values repeat per probe row for endpoint compatibility;
  these are not independent environmental observations.
- Leave the other operating node's firmware unchanged: it defaults to Probe 1.
- To expand later, add entries for Probe 5 on GPIO36 (VP) and Probe 6 on GPIO39
  (VN), after testing those cable paths.

## Development verification

- 17 backend tests pass using the pinned backend requirements:
  `python -m pytest -q backend/test_multi_probe.py backend/test_advisor_worker.py backend/test_advisor_analysis_api.py -k 'not historical_analysis'`.
- The excluded historical fixture test requires the ignored,
  unavailable `backyard_readings_test.json` file.
- `node --test dashboard/test/probeIdentity.test.js` passes.
- `npm run build` passes in dashboard. Targeted lint passes for AdvisorPanel,
  probeIdentity and its test; App.jsx retains existing lint errors unrelated
  to this change (unused React import and React hook purity/effect rules).
- Migration was tested with SQLite, including existing rows and repeated startup.
  The deployed production backend now accepts and persists distinct probe IDs,
  verified through successful uploads and Supabase records. The production
  migration was not executed manually from this workspace.
