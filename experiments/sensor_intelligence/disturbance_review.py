"""Explicit user exclusions support assisted review, never confirmed watering."""
from datetime import datetime
from .__main__ import analyze, POLICY, blocking_flags


def review_with_exclusions(rows, annotations):
    original = analyze(rows)
    requested = annotations.get('excluded_from_watering_interpretation', [])
    excluded = {}
    for annotation in requested:
        matches = [o for o in original['observations'] if
                   o['source'].get('device_id') == annotation['device_id'] and
                   o['source'].get('id') == str(annotation['id']) and
                   o.get('timestamp_utc') == annotation['timestamp_utc']]
        if len(matches) != 1 or not annotation.get('reason', '').strip():
            raise ValueError('Each exclusion must match exactly one device, ID and UTC timestamp and include a reason')
        excluded[matches[0]['source_row']] = annotation
    for o in original['observations']:
        if o['source_row'] in excluded:
            o['flags'].setdefault('record', []).append('user_excluded_disturbance')
            o['exclusion_reason'] = excluded[o['source_row']]['reason']
    # Original flags/timing remain in the audit. Recompute comparisons on retained
    # observations; no generated values and no gaps longer than 900s are bridged.
    retained = [o for o in original['observations'] if o['source_row'] not in excluded]
    filtered = analyze([o['source'] for o in retained])
    assisted = []
    original_ids = {tuple(c['evidence']['record_ids']) for c in original['candidates']}
    for candidate in filtered['candidates']:
        if tuple(candidate['evidence']['record_ids']) in original_ids:
            continue
        onset = datetime.fromisoformat(candidate['onset_interval'][1])
        device = candidate['device_id']
        local_exclusions = [o for o in original['observations'] if o['source_row'] in excluded
                            and o['source']['device_id'] == device and
                            0 < (onset-datetime.fromisoformat(o['timestamp_utc'])).total_seconds() <= 1800]
        if len(local_exclusions) != 1:
            continue
        # Require three clean baseline observations spanning >=15 min, plus the
        # detector's three clean response samples. Extra baseline protects against
        # briefly dry-looking glitches and clipped percentages hiding ADC changes.
        before = sorted([o for o in filtered['observations'] if o['source']['device_id'] == device
                         and 'timestamp_utc' in o and datetime.fromisoformat(o['timestamp_utc']) < onset],
                        key=lambda o: o['timestamp_utc'])[-3:]
        if len(before) != 3:
            continue
        if any(blocking_flags(o, baseline=True) for o in before):
            continue
        duration = (datetime.fromisoformat(before[-1]['timestamp_utc'])-datetime.fromisoformat(before[0]['timestamp_utc'])).total_seconds()
        if not 900 <= duration <= 1800:
            continue
        raw = [float(o['source']['soil_moisture_raw']) for o in before]
        pct = [float(o['source']['soil_moisture_pct']) for o in before]
        if max(raw)-min(raw) > POLICY['raw_drop'] or max(pct)-min(pct) > 3:
            continue
        mapping = {i: o for i, o in enumerate(retained, 1)}
        evidence_rows = [mapping[i] for i in candidate['evidence']['source_rows']]
        candidate['id'] = f"{device}:assisted:{evidence_rows[2]['source_row']}"
        candidate['classification'] = 'possible_watering_with_disturbance_warning'
        candidate['detection_mode'] = 'assisted_by_explicit_user_exclusion'
        candidate['evidence']['source_rows'] = [o['source_row'] for o in evidence_rows]
        candidate['evidence']['quality_flags'] = [o['flags'] for o in evidence_rows]
        candidate['evidence']['preceding_context'] = [dict(source_row=o['source_row'], timestamp_utc=o['timestamp_utc'], flags=o['flags'])
                                                      for o in original['observations'] if o in local_exclusions]
        candidate['evidence']['additional_baseline_record_ids'] = [o['source']['id'] for o in before]
        candidate['evidence']['excluded_records'] = [dict(source_row=o['source_row'], source=o['source'], reason=o['exclusion_reason']) for o in local_exclusions]
        candidate['uncertainty'].append('User-excluded disturbance is near onset; probe handling can mimic wetting. This is assisted review, not independent automatic detection.')
        assisted.append(candidate)
    if excluded:
        original['flag_counts']['record:user_excluded_disturbance'] = len(excluded)
    original['assisted_candidates'] = assisted
    original['exclusion_policy'] = dict(explicit_annotations_only=True, maximum_exclusions_near_onset=1,
        proximity_seconds=1800, baseline_samples=3, baseline_span_seconds=[900,1800], maximum_raw_baseline_range=171,
        no_interpolation=True, unassisted_results_preserved=True)
    return original
