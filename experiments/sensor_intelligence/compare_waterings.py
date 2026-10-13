"""Compare user reports separately; labels never enter automatic detection."""
import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .__main__ import analyze


def compare(rows, labels):
    report = analyze(rows)
    comparisons = []
    for label in labels:
        stamp = datetime.fromisoformat(label['reported_time_utc']).astimezone(timezone.utc)
        nearby = [r for r in report['observations'] if r['source']['device_id'] == label['device_id']
                  and 'timestamp_utc' in r and abs((datetime.fromisoformat(r['timestamp_utc'])-stamp).total_seconds()) <= 3600]
        nearby.sort(key=lambda r: r['timestamp_utc'])
        # One hour is a reporting association window, not confirmation of causality.
        candidates = [c for c in report['candidates'] if c['device_id'] == label['device_id']
                      and datetime.fromisoformat(c['onset_interval'][0])-timedelta(hours=1) <= stamp
                      <= datetime.fromisoformat(c['onset_interval'][1])+timedelta(hours=1)]
        withheld = [w for w in report['withheld_transitions'] if w['device_id'] == label['device_id'] and abs((datetime.fromisoformat(w['onset_utc'])-stamp).total_seconds()) <= 3600]
        comparisons.append(dict(withheld_transitions=withheld, user_report=label, association_tolerance_seconds=3600,
            candidate_ids=[c['id'] for c in candidates], nearby_observations=nearby,
            assessment=('Candidate near reported watering; not independent validation' if candidates else
            ('Automatic result withheld: ' + ', '.join(sorted({reason for w in withheld for reason in w['reasons']})) if withheld else 'No nearby candidate or qualifying abrupt rise'))))
    return dict(comparisons=comparisons, warning='Retrospective development checks; no precision/recall claim')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv')
    args = parser.parse_args()
    with open(args.csv, newline='', encoding='utf-8-sig') as stream:
        rows = list(csv.DictReader(stream))
    labels = json.loads(Path(__file__).with_name('watering_reports.json').read_text())
    print(json.dumps(compare(rows, labels), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
