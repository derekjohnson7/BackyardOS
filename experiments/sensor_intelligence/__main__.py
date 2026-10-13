"""Read-only CSV diagnostics: python -m experiments.sensor_intelligence CSV."""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from statistics import median

CHANNELS = ('soil_moisture_raw', 'soil_moisture_pct', 'temperature_c', 'humidity_pct', 'pressure_hpa')
BOUNDS = ((0, 4095), (0, 100), (-40, 85), (0, 100), (300, 1100))
POLICY = dict(gap_seconds=900, minimum_step_seconds=300, frozen_samples=6,
              rise_percentage_points=10, raw_drop=171, persistence_samples=3,
              step_thresholds=dict(zip(CHANNELS, (1000, 60, 10, 30, 20))), calibration_dry=2800, calibration_wet=1090, calibration_tolerance=1)


def blocking_flags(record, baseline=False):
    """Keep every flag in evidence; censoring alone does not invalidate ADC response.

    Large moisture steps may be watering OR hardware changes. Permit only as low
    confidence candidates; never waive raw freezes, rails, or environmental faults.
    """
    blocked = []
    for channel, flags in record['flags'].items():
        allowed = {'abrupt_step'} if channel in CHANNELS[:2] and not baseline else set()
        if channel == 'soil_moisture_pct':
            allowed.add('calibration_clipped')
            if 'calibration_clipped' in flags:
                allowed.add('unchanged_run')
        if set(flags) - allowed:
            blocked.extend(f'{channel}:{flag}' for flag in sorted(set(flags) - allowed))
    return blocked


def analyze(rows):
    """Retain original strings; flags and evidence reference 1-based CSV data rows.

    Offline frozen runs flag their entire observed duration, including the prefix.
    This is retrospective analysis, not a causal streaming detector.
    """
    observations = []
    devices = defaultdict(list)
    id_counts = Counter(r.get('id') for r in rows)
    for index, source in enumerate(rows, 1):
        record = dict(source_row=index, source=dict(source), flags=defaultdict(list))
        observations.append(record)
        flags = record['flags']
        if source.get('device_id') not in ('backyard-node-01', 'backyard-node-02'):
            flags['record'].append('excluded_device')
            continue
        if id_counts[source.get('id')] > 1:
            flags['record'].append('duplicate_id')
        try:
            stamp = datetime.fromisoformat(source['timestamp'])
            stamp = stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
            record['timestamp_utc'] = stamp.isoformat()
            record['timestamp_central'] = stamp.astimezone(ZoneInfo('America/Chicago')).isoformat()
        except (ValueError, TypeError, KeyError):
            flags['record'].append('invalid_timestamp')
            continue
        values = {}
        for channel, (low, high) in zip(CHANNELS, BOUNDS):
            try:
                value = float(source[channel])
                if not math.isfinite(value):
                    raise ValueError()
                values[channel] = value
                if not low <= value <= high or (channel == 'soil_moisture_raw' and not value.is_integer()):
                    flags[channel].append('out_of_range')
            except (ValueError, TypeError, KeyError):
                values[channel] = None
                flags[channel].append('missing_or_nonfinite')
        raw, pct = (values[c] for c in CHANNELS[:2])
        if pct in (0, 100):
            flags['soil_moisture_pct'].append('calibration_clipped')
        if raw in (0, 4095):
            flags['soil_moisture_raw'].append('adc_rail')
        if raw is not None and pct is not None:
            expected = max(0, min(100, (2800 - raw) / 1710 * 100))
            if abs(expected - pct) > POLICY['calibration_tolerance']:
                flags['soil_moisture_pct'].append('calibration_mismatch')
        devices[source['device_id']].append((stamp, index, values, record))
    candidates, summaries, withheld = [], {}, []
    for device, records in sorted(devices.items()):
        records.sort(key=lambda r: (r[0], r[1]))
        timestamps = Counter(r[0] for r in records)
        intervals = []
        segment = 0
        for i, (stamp, _, values, record) in enumerate(records):
            if timestamps[stamp] > 1:
                record['flags']['record'].append('duplicate_timestamp')
            if i:
                seconds = (stamp - records[i-1][0]).total_seconds()
                if seconds > 0:
                    intervals.append(seconds)
                if seconds > POLICY['gap_seconds'] or seconds <= 0:
                    segment += 1
                    record['flags']['record'].append('gap_before' if seconds > 900 else 'nonpositive_interval')
                elif seconds < POLICY['minimum_step_seconds']:
                    record['flags']['record'].append('short_interval')
            record['segment'] = segment
            if i and 300 <= (stamp - records[i-1][0]).total_seconds() <= 900:
                for channel, threshold in zip(CHANNELS, (1000, 60, 10, 30, 20)):
                    previous = records[i-1][2][channel]
                    current = values[channel]
                    if previous is not None and current is not None and abs(current-previous) > threshold:
                        record['flags'][channel].append('abrupt_step')
        # Exact individual-channel freezes and simultaneous BME freezes remain distinct.
        for channels in [(c,) for c in CHANNELS] + [CHANNELS[2:]]:
            start = 0
            for end in range(1, len(records) + 1):
                same = end < len(records) and records[end][3]['segment'] == records[start][3]['segment'] and all(
                    records[end][2][c] is not None and records[end][2][c] == records[start][2][c] for c in channels)
                if same:
                    continue
                if end-start >= POLICY['frozen_samples']:
                    for row in records[start:end]:
                        for c in channels:
                            if row[2][c] is not None:
                                row[3]['flags'][c].append('frozen_bme_tuple' if len(channels) == 3 else 'unchanged_run')
                start = end
        last_end = -1
        for i in range(1, len(records)):
            previous_pct = records[i-1][2]['soil_moisture_pct']
            current_pct = records[i][2]['soil_moisture_pct']
            log_withheld = previous_pct is not None and current_pct is not None and current_pct - previous_pct >= POLICY['rise_percentage_points']
            if i <= last_end:
                continue
            window = records[max(0,i-2):i+3]
            reasons = []
            if i < 2:
                reasons.append('insufficient_baseline')
            if i+2 >= len(records):
                reasons.append('insufficient_followup')
            if len({r[3]['segment'] for r in window}) != 1:
                reasons.append('segment_boundary')
            for row in window:
                reasons.extend(blocking_flags(row[3], baseline=row[0] < records[i][0]))
            if reasons:
                if log_withheld:
                    withheld.append(dict(device_id=device, onset_utc=records[i][0].isoformat(),
                    onset_central=records[i][3]['timestamp_central'],
                    source_rows=[r[1] for r in window], reasons=sorted(set(reasons))))
                continue
            baseline = median(r[2]['soil_moisture_pct'] for r in window[:2])
            raw_baseline = median(r[2]['soil_moisture_raw'] for r in window[:2])
            if abs(window[0][2]['soil_moisture_pct']-window[1][2]['soil_moisture_pct']) > 3:
                if log_withheld:
                    withheld.append(dict(device_id=device, onset_utc=records[i][0].isoformat(), source_rows=[r[1] for r in window], reasons=['unstable_baseline']))
                continue
            rise = min(r[2]['soil_moisture_pct'] for r in window[2:]) - baseline
            drop = raw_baseline - max(r[2]['soil_moisture_raw'] for r in window[2:])
            if rise < POLICY['rise_percentage_points'] or drop < POLICY['raw_drop']:
                if log_withheld:
                    withheld.append(dict(device_id=device, onset_utc=records[i][0].isoformat(), source_rows=[r[1] for r in window], reasons=['response_not_sustained_or_raw_drop_too_small']))
                continue
            candidates.append(dict(id=f'{device}:candidate:{records[i][1]}', device_id=device,
                classification='candidate_watering_event', confidence='low',
                onset_interval=[window[1][0].isoformat(), window[2][0].isoformat()],
                onset_interval_central=[r[0].astimezone(ZoneInfo('America/Chicago')).isoformat() for r in window[1:3]],
                evidence=dict(source_rows=[r[1] for r in window], record_ids=[r[3]['source']['id'] for r in window],
                    raw_values=[r[2]['soil_moisture_raw'] for r in window],
                    percentage_values=[r[2]['soil_moisture_pct'] for r in window],
                    quality_flags=[dict(r[3]['flags']) for r in window],
                    preceding_context=[dict(source_row=r[1], timestamp_utc=r[0].isoformat(), flags=dict(r[3]['flags'])) for r in records[max(0,i-6):i-2]], baseline_pct=baseline,
                    minimum_sustained_rise_pp=round(rise, 3), minimum_raw_drop=drop,
                    persistence_seconds=(window[-1][0]-window[2][0]).total_seconds()),
                uncertainty=['Automatic candidate; user watering reports evaluated separately', 'Rain, probe movement or calibration changes can mimic wetting',
                             'No causal confirmation; thresholds are experimental']))
            last_end = i + 2
        summaries[device] = dict(rows=len(records), segments=segment+1,
            first=records[0][0].isoformat(), last=records[-1][0].isoformat(),
            median_positive_interval_seconds=median(intervals) if intervals else None)
    counts = Counter(f'{channel}:{flag}' for r in observations for channel, flags in r['flags'].items() for flag in set(flags))
    return dict(schema_version=2, policy=POLICY, timezone='UTC storage (user confirmed); America/Chicago display',
                limitations=['No interpolation', 'Flags indicate suspicion, not proven hardware failure',
                             'No blanket date-based rejection of node 01; configuration history unavailable',
                             'Three retrospective user reports are development checks, not independent accuracy validation'],
                input_rows=len(rows), devices=summaries, flag_counts=dict(sorted(counts.items())),
                candidates=candidates, withheld_transitions=withheld, observations=observations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv')
    parser.add_argument('--annotations', help='JSON with explicit user disturbance exclusions; assisted results stay separate')
    parser.add_argument('--summary', action='store_true', help='omit per-row observations')
    args = parser.parse_args()
    with open(args.csv, 'rb') as stream:
        digest = hashlib.sha256(stream.read()).hexdigest()
    with open(args.csv, newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        required = {'device_id', 'timestamp', 'id', *CHANNELS}
        if not required.issubset(reader.fieldnames or []):
            parser.error('CSV missing required columns')
        rows = list(reader)
        if args.annotations:
            from .disturbance_review import review_with_exclusions
            with open(args.annotations, encoding='utf-8') as annotations_stream:
                report = review_with_exclusions(rows, json.load(annotations_stream))
        else:
            report = analyze(rows)
    report['source_sha256'] = digest
    if args.summary:
        report.pop('observations')
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
