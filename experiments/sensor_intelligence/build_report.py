"""Generate a self-contained readable report from the current analysis only."""
import html
from datetime import datetime
from zoneinfo import ZoneInfo


def escape(value):
    return html.escape(str(value))


REASONS = {
    'record:short_interval': 'Readings arrived less than five minutes apart.',
    'record:gap_before': 'An outage interrupted the evidence.',
    'segment_boundary': 'The evidence crosses an outage or duplicate timestamp.',
    'record:duplicate_timestamp': 'Multiple readings have the same time.',
    'record:duplicate_id': 'Record IDs are duplicated.',
    'insufficient_baseline': 'Not enough readings before the rise.',
    'insufficient_followup': 'Not enough readings after the rise.',
    'unstable_baseline': 'The starting moisture readings were changing.',
    'response_not_sustained_or_raw_drop_too_small': 'The wetter response did not persist or raw values did not support it.',
}


def reason_text(code):
    if code in REASONS:
        return REASONS[code]
    channel, _, flag = code.partition(':')
    labels = {'soil_moisture_raw': 'Raw moisture', 'soil_moisture_pct': 'Moisture percentage',
              'temperature_c': 'Temperature', 'humidity_pct': 'Humidity', 'pressure_hpa': 'Pressure'}
    flags = {'abrupt_step': 'changed abruptly', 'unchanged_run': 'repeated unchanged',
             'frozen_bme_tuple': 'repeated with the other environmental channels',
             'missing_or_nonfinite': 'is missing or invalid', 'out_of_range': 'is outside plausible sensor limits',
             'adc_rail': 'is at an ADC endpoint', 'calibration_mismatch': 'disagrees with the calibration'}
    return labels.get(channel, channel.replace('_', ' ')) + ' ' + flags.get(flag, flag.replace('_', ' ')) + '.'


def chart(observations, key, maximum):
    points = []
    for row in observations:
        try:
            value = float(row['source'][key])
            if not 0 <= value <= maximum:
                continue
            points.append((datetime.fromisoformat(row['timestamp_utc']).timestamp(), value, row))
        except (KeyError, ValueError, TypeError):
            continue
    points.sort(key=lambda p: p[0])
    if not points:
        return '<p>No valid readings to plot.</p>'
    lo, hi = points[0][0], points[-1][0]
    span = max(hi-lo, 1)
    svg = ['<svg viewBox="0 0 900 205" role="img" aria-label="Sensor readings over time">']
    for value in (0, maximum/2, maximum):
        y = 155-value/maximum*120
        svg.append(f'<path d="M60 {y}H855" stroke="#dce5e7"/><text x="48" y="{y+4}" text-anchor="end">{value:g}</text>')
    previous = None
    for stamp, value, row in points:
        x, y = 60+(stamp-lo)/span*795, 155-value/maximum*120
        excluded = 'user_excluded_disturbance' in row['flags'].get('record', [])
        if previous and not excluded and not previous[3] and 0 < stamp-previous[0] <= 900:
            svg.append(f'<path d="M{previous[1]:.2f} {previous[2]:.2f}L{x:.2f} {y:.2f}" stroke="#137c78" stroke-width="1.5"/>')
        tooltip = escape(f"{row['timestamp_central']} | {key}: {value:g} | ID {row['source'].get('id')}" + (' | excluded disturbance' if excluded else ''))
        color = '#c34c27' if excluded else '#137c78'
        svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.5" fill="{color}"><title>{tooltip}</title></circle>')
        previous = stamp, x, y, excluded
    for x, point in ((60, points[0]), (855, points[-1])):
        label = datetime.fromtimestamp(point[0], ZoneInfo('America/Chicago')).strftime('%b %d %I:%M %p %Z')
        svg.append(f'<text x="{x}" y="190" text-anchor="{"start" if x==60 else "end"}">{label}</text>')
    return ''.join(svg)+'</svg>'


def render(report, comparisons=None):
    body = ['<h1>Your sensor report</h1><p>Offline experiment · Times shown in Central time · No changes to your running system</p>',
            f"<section><h2>What this export contains</h2><p>{report['input_rows']:,} source rows. Node 03 and other devices are excluded from analysis, but retained in the audit. This report covers only the supplied export.</p>",
            f"<p><b>{len(report['candidates'])} unassisted possible watering event(s)</b>; <b>{len(report.get('assisted_candidates', []))} assisted result(s)</b> using explicit disturbance exclusions. None confirms watering or establishes that a plant needs water.</p></section>"]
    for device, details in report['devices'].items():
        observations = [o for o in report['observations'] if o['source'].get('device_id') == device]
        body.append(f"<section><h2>{escape(device)}</h2><p>{details['rows']:,} timestamped readings. Coverage: {escape(details['first'])} to {escape(details['last'])} UTC.</p><h3>Displayed moisture (%)</h3>")
        body.append(chart(observations, 'soil_moisture_pct', 100))
        body.append('<h3>Raw sensor value — lower means wetter</h3>'+chart(observations, 'soil_moisture_raw', 4095))
        body.append('<p>100% means the calibration’s wet limit was reached, not measured physical saturation. Dots are actual readings. Lines stop at gaps over 15 minutes and excluded readings. Orange dots mark user-excluded disturbances. Hover over a dot for its details.</p></section>')
    body.append('<section><h2>Possible watering events</h2>')
    all_candidates = report['candidates'] + report.get('assisted_candidates', [])
    if not all_candidates:
        body.append('<p>No qualifying event in this export. That does not mean no watering happened; check withheld results below and whether the export includes before-and-after readings.</p>')
    for c in all_candidates:
        mode = 'Assisted: disturbance warning' if 'detection_mode' in c else 'Unassisted: possible watering'
        e = c['evidence']
        body.append(f"<h3>{escape(c['device_id'])} — {mode}</h3><p>Change occurred between {escape(c['onset_interval_central'][0])} and {escape(c['onset_interval_central'][1])}. Low confidence.</p><p>Later readings stayed at least {e['minimum_sustained_rise_pp']:g} percentage points above the baseline, with raw values at least {e['minimum_raw_drop']:g} lower. Observed persistence: {e['persistence_seconds']/60:.1f} minutes. Evidence record IDs: {escape(', '.join(e['record_ids']))}.</p>")
        if 'detection_mode' in c:
            body.append('<p><b>Your exclusion helped recover this result.</b> Original warnings remain in the audit. Probe handling can mimic watering; this is not independent automatic confirmation.</p>')
        if e.get('preceding_context') and any(o['flags'] for o in e['preceding_context']):
            body.append('<p><b>Nearby context includes warnings.</b> Earlier disturbances or gaps limit interpretation even if the event window passed its checks.</p>')
    body.append('</section><section><h2>Why some rises were withheld</h2><p>Withheld means a rise was observed but the evidence failed a safeguard. It does not mean you did not water. These are substantial adjacent rises, not a complete list of every possible slow change.</p>')
    if not report['withheld_transitions']:
        body.append('<p>No withheld substantial adjacent rises in this export.</p>')
    for w in report['withheld_transitions']:
        stamp = datetime.fromisoformat(w['onset_utc']).astimezone(ZoneInfo('America/Chicago')).isoformat()
        body.append(f"<details><summary>{escape(w['device_id'])} · {stamp}</summary><ul>"+''.join('<li>'+escape(reason_text(r))+'</li>' for r in w['reasons'])+'</ul></details>')
    body.append('</section>')
    if comparisons:
        body.append('<section><h2>Your reported watering times</h2><p>Reports are compared separately from detection using a one-hour association window. A nearby candidate is not causal confirmation.</p>')
        for item in comparisons['comparisons']:
            label = item['user_report']
            local = datetime.fromisoformat(label['reported_time_utc']).astimezone(ZoneInfo('America/Chicago')).isoformat()
            body.append(f"<p><b>{escape(label['device_id'])} · {local}</b>: "+('Nearby unassisted candidate found.' if item['candidate_ids'] else 'No nearby unassisted candidate found; inspect withheld reasons and export coverage.')+'</p>')
        body.append('</section>')
    body.append('<section><h2>Sensor warnings in this export</h2><p>Counts can overlap. A warning means a reading deserves caution, not proven hardware failure. Clipping means a calibration endpoint; it is not a hardware fault.</p><ul>')
    for code, count in report['flag_counts'].items():
        description = {'soil_moisture_pct:calibration_clipped': 'Moisture percentage reached a calibration endpoint.',
                       'record:excluded_device': 'Rows belong to node 03 or another excluded device.',
                       'record:user_excluded_disturbance': 'Rows were explicitly excluded by you as disturbances.'}.get(code, reason_text(code))
        body.append('<li>'+escape(description)+f' <b>{count:,} reading(s)</b></li>')
    body.append('</ul></section>')
    body.append('<section><h2>What you need to do</h2><p>No extra watering is needed for testing. Keep collecting readings normally. For a future watering, note the node and time and export readings from at least an hour before through an hour afterward.</p><p>For an unassisted candidate, two starting readings must be within 3 percentage points, followed by three readings at least 10 points higher and 171 raw units lower. Readings must be 5–15 minutes apart, with no blocking sensor warnings. Assisted review requires your explicit exclusion and three steady starting readings. These thresholds are provisional. Tests verify software behavior, not real-world accuracy. Reports are snapshots and do not update themselves.</p></section>')
    body.append('<p class="small">Source SHA-256: '+escape(report.get('source_sha256', 'unavailable'))+'</p>')
    style='body{font:17px/1.65 system-ui;background:#eef4f3;color:#173438;margin:0}main{max-width:1000px;padding:32px 20px;margin:auto}section{background:white;border:1px solid #dce5e7;border-radius:12px;padding:24px;margin:24px 0}h1{font-size:38px}h2{line-height:1.3}svg{width:100%;height:auto}svg text{font:12px system-ui;fill:#53696a}.small{font-size:12px;overflow-wrap:anywhere}summary{cursor:pointer}@media print{section{break-inside:avoid}body{background:white}}'
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BackyardOS sensor report</title><style>'+style+'</style></head><body><main>'+''.join(body)+'</main></body></html>'


def main():
    from .run import main as run_main
    run_main()


if __name__ == '__main__':
    main()
