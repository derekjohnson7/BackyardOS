# Experimental Sensor Intelligence

Offline, standard-library-only diagnostics. Run from the repository root:

```sh
python3 -m experiments.sensor_intelligence /path/to/sensorreading_rows.csv --summary
python3 -m unittest experiments.sensor_intelligence.test_sensor_intelligence -v
```

Omit `--summary` to include every original row (unchanged string values), channel flags, and chronological segment identifiers. Output is JSON on stdout; the CLI opens the CSV read-only and neither contacts services nor imports production modules. Reports include the source SHA-256. CSV data-row references are 1-based, excluding the header. Flags can overlap; counts are not additive. Excluded devices remain in the audit observations but never enter temporal analysis or event detection.

Architecture inspection: production FastAPI/SQLModel telemetry feeds deterministic Advisor findings; `backend/advisor_validation.py` validates referenced IDs and exact evidence objects. Existing Advisor preparation retains moisture percentage and temperature but drops raw ADC. This independent experiment preserves raw ADC and does not extend or bypass that validator. Its findings are not an Advisor input contract.

Policy is emitted in every report. Only independent nodes 01 and 02 are analyzed. No cross-device matching or blanket rejection of node 01 after an assumed hardware-change date. Source timestamps are UTC as confirmed by the user. Derived timestamps include UTC offsets and America/Chicago display times; source strings remain unchanged. Malformed timestamps are retained but excluded from chronology; nonfinite measurements are retained as source strings and flagged. Missing required columns reject the CLI input.

Per-channel bounds: ADC integers 0–4095, moisture/humidity 0–100, BME280 temperature −40–85°C, pressure 300–1100 hPa. These are instrument plausibility bounds, not plant thresholds. ADC rails, clipping, calibration mismatch (>1 percentage point from documented 2800/1090 endpoints), and abrupt steps are separate flags. Abrupt-step thresholds per interval are 1000 ADC, 60 moisture points, 10°C, 30 humidity points and 20 hPa. They express suspicion, not proof of failure. Exact runs of at least six samples flag individual unchanged channels and simultaneous frozen BME tuples, retrospectively including the prefix. Stable natural readings may also trigger unchanged-run flags.

Chronology is sorted per device without changing source rows. Gaps >900 seconds and duplicate timestamps break segments; intervals <300 seconds are suspect. Frozen runs never bridge segment boundaries. No outage interpolation or synthetic observations. Duplicate IDs and all timestamp collisions are flagged and barred from candidate evidence.

Candidates require two stable baseline samples (within 3 points) and three follow-up samples all at least 10 points higher and 171 ADC lower than the baseline median. The entire five-row window must be contiguous and free of blocking quality flags. Clipping and unchanged percentages at clipped endpoints are allowed when valid raw ADC values show the sustained decrease. Moisture abrupt-step flags in the response are retained but allowed for low-confidence candidates because both watering and hardware changes can cause them. Raw freezes, rails, calibration mismatch, cadence anomalies and all BME suspicion still block candidates. Overlapping candidate windows are suppressed. This deliberately sacrifices recall, especially for gradual watering and startup sampling. BME flags remain channel-specific even though the event gate conservatively rejects a window containing any suspect channel.

Every event remains low-confidence, with an onset interval, exact source-row references, measured deltas and persistence duration. User-reported watering times are stored separately from automatic detection. Rain, probe movement and calibration changes prevent causal confirmation from sensor values alone. Percentage and ADC derive from the same sensor and are consistency checks, not independent corroboration. No irrigation advice, estimated volumes, forecasts or confirmed watering labels are generated.

Validation on the supplied 13,752-row export: nodes 01/02 have 7,282/6,464 rows; all six node 03 rows are excluded. Both median positive intervals are 602 seconds. The updated policy retains three low-confidence candidates: one on node 01 (August 22), and two on node 02 (September 15 and October 10 UTC). The evening node 01 candidate is now withheld because an abrupt dry-looking baseline change can make recovery look like watering. The morning candidate has preceding outage/step context in its evidence and remains uncertain. This policy change trades some false-positive risk for better handling of clipped watering responses.

Three retrospective node 02 watering reports are stored in `watering_reports.json`, separate from detector inputs. The October time is approximate (21:00 UTC); record 12942 is only an observation anchor. Compare them using:

```sh
python3 -m experiments.sensor_intelligence.compare_waterings /path/to/sensorreading_rows.csv
```

The comparison includes original readings and flags within one hour of each report and candidate associations within a one-hour tolerance. This is explicitly a development check, not independent validation or a claim of detection accuracy. September and October have nearby candidates. August occurred during rapid startup sampling and remains undetected under the cadence safeguards. See `reports/watering_comparison.json` for the audit and `reports/sensor_intelligence_summary.json` for all candidates. Full per-row results are in `reports/sensor_intelligence_full.json`. No interpolation, production integration, database update or network access is involved.

Further safeguards: abrupt moisture steps are allowed only in the response, not in the two baseline readings. Substantial adjacent rises that fail checks include explicit reason codes and source-row references in `withheld_transitions`. These are diagnostic rejections, not a census of watering or absence of watering. The comparison report exposes these reasons separately from successful candidate associations.

After generating JSON reports, rebuild the readable HTML with `python3 -m experiments.sensor_intelligence.build_report /path/to/sensorreading_rows.csv`. Twenty-one tests cover the original cases plus baseline recovery, frozen ADC, duplicate IDs, fast-sampling reasons, missing percentages and explicitly assisted exclusions.


## Assisted review near an explicitly reported disturbance

`python3 -m experiments.sensor_intelligence experiments/sensor_intelligence/fixtures/node01_oct13_screenshot.csv --annotations experiments/sensor_intelligence/fixtures/node01_oct13_annotations.json --summary`

The optional annotations path preserves the original analysis and source rows, and adds `assisted_candidates` separately. It requires an exact device/record ID/UTC timestamp match with a reason. Only explicitly excluded rows are removed from candidate evidence; original flags and the excluded source remain in the audit. Without annotations this path does not run. Reported watering times do not drive detection.

A newly recoverable result must have exactly one excluded observation within 30 minutes before onset, three valid steady baseline samples spanning 15–30 minutes (raw range <=171 and percentage range <=3), and the normal three-sample sustained response. The retained sequence must still obey cadence/gap and hardware checks. Comparisons are recomputed after the explicit exclusion, so a pressure recovery or short interval caused by comparing against the disturbed row need not invalidate the retained evidence. Actual retained gaps >15 minutes remain blocking; nothing is interpolated. Original flags remain visible alongside the assisted candidate.

Today’s screenshot yields one low-confidence `possible_watering_with_disturbance_warning`; its unassisted result remains withheld. Twenty-one tests pass, including seven assisted-path checks. The prior historical export retains the same three candidates, including September and October; the evening August dry-glitch recovery remains withheld. This change can recover wetting evidence near a known disturbance but may also admit a sustained response caused by probe handling. It is assisted interpretation, not independent automatic confirmation. The October 13 example was used to develop this revision and is no longer a held-out accuracy check.


## Review and reproduce this version

Requires Python 3.10+ and the system timezone database (`America/Chicago`). No third-party Python packages, database credentials or service connections are required. Run commands from the repository root.

1. Run `python3 -m unittest experiments.sensor_intelligence.test_sensor_intelligence -v`.
2. Analyze a CSV with `python3 -m experiments.sensor_intelligence /path/to/export.csv --summary` (omit `--summary` for the full audit).
3. Compare the three historical user reports with `python3 -m experiments.sensor_intelligence.compare_waterings /path/to/export.csv`.
4. Analyze the screenshot fixture with the explicit annotations command above. The fixture is a manual transcription, not a database export.

Commands print JSON to stdout; redirect output if saving a new report. To rebuild the HTML snapshot, first save outputs from steps 2 and 3 to `reports/sensor_intelligence_summary.json` and `reports/watering_comparison.json`, and the annotated fixture analysis to `reports/node01_oct13_assisted.json`. Then run `python3 -m experiments.sensor_intelligence.build_report /path/to/export.csv`.

The HTML builder is a report for the October 2026 development examples, not a general live dashboard. Its dated narrative must be reviewed when analyzing a different export. The detector and comparison commands work on new CSV exports; the original labels remain development references, not independent validation labels.

Generated reports under `reports/` and review packages under `review_package/` are ignored by Git and remain on this computer. They are not backed up by a commit. The two small screenshot-derived test fixtures are versioned under `experiments/sensor_intelligence/fixtures/`; they contain sensor readings and the explicit user exclusion needed to reproduce the tests. No production files were modified. Local commits preserve code history but are not uploaded unless explicitly pushed.

For the next normal watering, preserve this version’s policy and source hashes in the review manifest. Record the node and approximate UTC or Central time before evaluating. Run the unassisted detector first; only use an exclusion when the user independently identifies a disturbance. Report unassisted and assisted outcomes separately. Do not tune thresholds against that same event and call it independent validation.
