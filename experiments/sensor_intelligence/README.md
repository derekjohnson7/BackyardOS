# BackyardOS Sensor Intelligence — offline experiment

## Everyday use

From your BackyardOS repository folder, run:

```sh
python3 -m experiments.sensor_intelligence.run "/path/to/sensorreading_rows.csv"
```

Replace the quoted path with your exported CSV path. The command prints the location of `report.html`; open that file in your browser. No assistant, database connection, API key or third-party Python package is needed. Requires Python 3.10+ and the system timezone database for America/Chicago. If `python3` is unavailable, install Python before running.

Each run creates its own dated folder under `reports/`, containing a readable report, full audit, summary and a manifest recording the source hash and implementation hashes. Existing reports are preserved. Reports and review packages are ignored by Git; they remain on your computer, without Git backup. Do not place raw exports inside tracked code folders. The source CSV is opened read-only; no readings are changed and no network requests are made.

The HTML is an offline snapshot generated entirely from the export you supplied. It does not refresh automatically. After collecting more data, export another CSV and run the same command again. Include at least an hour before and after a watering event if you want to check the response. No additional watering is required for testing. Charts show Central time with daylight saving handled by America/Chicago; timestamps in the database/export are interpreted as UTC based on the user's confirmation. Source timestamp strings remain unchanged.

## What the report means

- **Unassisted possible watering:** a sustained wetter response meets the current safeguards. It is low confidence, not causal confirmation or a recommendation to water.
- **Assisted result:** an explicit user disturbance exclusion recovered a qualifying response. The exclusion and original warnings remain visible. This is not independent automatic detection.
- **Withheld:** a rise was seen but failed a safeguard; the report explains why. It does not mean no watering happened.
- **100%:** the percentage reached the calibration's wet endpoint, not measured physical saturation.

Charts plot actual measurements without interpolating outages. Green dots are retained readings; orange dots are user-excluded disturbances. Lines stop at gaps over 15 minutes and exclusions. Hover over dots for timestamps and IDs. Raw sensor values decreasing indicate a wetter response. Long histories may be easier to inspect by exporting a shorter period.

## Optional watering notes

The detector does not need watering labels. To compare your reported times separately, supply a JSON list using this format:

```json
[
  {"device_id":"backyard-node-01", "reported_time_utc":"2026-10-13T19:10:00+00:00", "precision":"approximate"}
]
```

Save it outside tracked code, for example `reports/my_waterings.json`, then run:

```sh
python3 -m experiments.sensor_intelligence.run "/path/to/export.csv" --labels reports/my_waterings.json
```

Label timestamps must include an offset. The example is 2:10 p.m. Central on October 13, 2026. Candidate association uses a one-hour tolerance and does not establish causality. Reports do not feed into detection or change thresholds.

## Optional explicit disturbance exclusions

Only exclude a reading when you independently know it was disturbed. Do not exclude inconvenient readings just to obtain a candidate. The optional JSON annotation format is:

```json
{
  "excluded_from_watering_interpretation": [
    {"device_id":"backyard-node-01", "id":"13812", "timestamp_utc":"2026-10-13T19:01:28+00:00", "reason":"User reports moving things around"}
  ]
}
```

Run the supplied example without private data or database access:

```sh
python3 -m experiments.sensor_intelligence.run experiments/sensor_intelligence/fixtures/node01_oct13_screenshot.csv --annotations experiments/sensor_intelligence/fixtures/node01_oct13_annotations.json
```

For your own export, use its CSV and annotation path. Exclusions require an exact device, ID and UTC timestamp match and a reason. An exclusion absent from the export fails with an explanatory error. Original source observations and unassisted results remain in the audit; exclusions cannot turn an assisted result into unassisted confirmation.

## Current safeguards and limitations

Only independent nodes 01 and 02 enter temporal analysis. Node 03 is temporary test data; it and unknown devices are retained but excluded. No cross-device matching or blanket date-based rejection of node 01 is applied.

Channel bounds: integer ADC 0–4095; moisture and humidity 0–100%; temperature −40–85°C; pressure 300–1100 hPa. These are instrument plausibility bounds, not plant thresholds. Flags distinguish invalid or missing/nonfinite values, ADC rails, percentage clipping, calibration mismatch, abrupt changes, frozen runs, duplicate IDs/timestamps and sampling discontinuities. Exact six-sample runs flag individual channels and simultaneous BME tuples retrospectively, including the prefix; naturally steady values may also be flagged.

Calibration is the documented dry 2800 / wet 1090 mapping, clipped to 0–100%; disagreement beyond 1 percentage point is flagged. Abrupt-step thresholds are 1000 ADC units, 60 moisture points, 10°C, 30 humidity points and 20 hPa per regular interval. Gaps >900 seconds and duplicate timestamps split segments. Intervals <300 seconds are suspect. No outages are interpolated.

Unassisted candidates require two baseline readings within 3 percentage points followed by three readings each at least 10 points higher and 171 raw units lower than the baseline median. All evidence must be contiguous and free of blocking flags. Clipped percentages and their unchanged runs are allowed when raw values support the change. Large moisture response steps may be allowed, but abrupt baseline steps, raw freezes, rails, calibration mismatch, environmental warnings and timing faults block results. Overlapping candidates are suppressed. Raw/percentage agreement is consistency within one sensor, not independent corroboration.

Assisted review recomputes comparisons after explicit exclusions, retaining the original audit. A recovered result requires exactly one exclusion within 30 minutes before onset, three valid baseline observations spanning 15–30 minutes, raw range <=171 and percentage range <=3, plus the normal sustained response. Remaining readings still obey cadence and hardware checks. Retained gaps >15 minutes remain blocking. Recovery comparisons can pass after removal of a known disturbed row, but probe handling can mimic lasting wetting. All outcomes remain low confidence.

User watering examples were used during development, not independent accuracy validation. Unknown watering, rain, calibration changes and probe movement limit causal conclusions. No forecasts, watering volumes, confirmed labels or irrigation advice are generated. Freeze the current version before checking a future event; changing rules to fit it turns it into another development example.

## Development and checks

```sh
python3 -m unittest discover -s experiments/sensor_intelligence -t . -p 'test_*.py' -v
```

25 tests cover detector safeguards, assisted exclusions, read-only inputs, unique output folders, malformed and empty exports, safe HTML rendering and the complete workflow. Test fixtures are screenshot-transcribed sensor readings under `fixtures/`, not a new database export.

The historical 13,752-row CSV produced three unassisted candidates: node 01 on August 22 and node 02 near September 15 and October 10 user reports. The evening August 22 dry-glitch recovery remains withheld; August 28 rapid startup sampling remains withheld. October 13 screenshot data produces one assisted result after explicit exclusion of record 13812, with no unassisted candidate. These are regression outcomes, not accuracy claims.

Advanced JSON-only CLI remains available: `python3 -m experiments.sensor_intelligence export.csv --summary`. The `build_report` module now invokes the complete workflow as well; it no longer needs pre-generated reports or dated narrative. `compare_waterings` remains a historical development helper using its bundled user reports.

Production inspection found that Advisor preparation drops raw ADC and its validator checks exact structured evidence. This experiment neither imports production services nor bypasses that contract. FastAPI, Advisor, firmware, dashboard and database integration remain outside scope. Nothing runs continuously or deploys as part of these commands.


## Nightly read-only export and review

A scheduled follow-up in the existing Codex chat runs at 12:10 a.m. America/Chicago. Keep this Mac powered on and the desktop app running. Its execution checkout is the chat workspace, not your Documents checkout. Generated exports/reports are local to that workspace under `reports/daily/` and are not uploaded to GitHub. The scheduled review reads those local files and returns meaningful findings or failures in the same chat, staying quiet when nothing actionable changes.

The command is also runnable manually from any checkout:

```sh
python3 -m experiments.sensor_intelligence.daily
```

It downloads the existing public read-only `/readings` endpoint, which returns a rolling seven days, not the complete historical table. No database password or key is used; no production route is changed. Each run saves that snapshot and a CSV for the previous Central calendar day with one hour of prior context, then invokes the report workflow. Calendar boundaries follow daylight saving (23/25-hour days are tested). The report labels the context window; report counts include context and late-night rises may need the following day's readings. Repeated runs preserve earlier files. An export cannot recover data older than the endpoint's rolling window after a prolonged interruption.

Network access must be permitted for this read-only endpoint in unattended runs. If the endpoint fails, the run reports failure rather than claiming success. The scheduled review checks node coverage and reports missing data. No automatic sensor exclusions or threshold changes are performed. The app schedule is stored by Codex, not installed by cloning this repository; you can pause it in the app's scheduled tasks. No separate macOS job is installed. Retention is manual: generated snapshots accumulate locally and are not a guaranteed backup of the full database.

28 tests pass, including daily window boundaries, daylight saving, context selection, missing-schema failure and the prior workflow/detector checks. A live endpoint export and report generation were verified during setup.
