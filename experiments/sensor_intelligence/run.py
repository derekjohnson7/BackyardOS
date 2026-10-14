"""One-command offline workflow: python3 -m experiments.sensor_intelligence.run export.csv"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from .__main__ import analyze, CHANNELS
from .build_report import render
from .compare_waterings import compare
from .disturbance_review import review_with_exclusions


def run(csv_path, output_root, annotations=None, labels=None):
    csv_path = Path(csv_path)
    content = csv_path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    # Analyze the exact bytes hashed; never contact the database or modify input.
    import io
    reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig'), newline=''))
    if not {'device_id', 'timestamp', 'id', *CHANNELS}.issubset(reader.fieldnames or []):
        raise ValueError('CSV missing required columns; export the complete sensorreading table columns.')
    rows = list(reader)
    report = review_with_exclusions(rows, annotations) if annotations is not None else analyze(rows)
    report['source_sha256'] = digest
    comparisons = compare(rows, labels) if labels else None
    destination = Path(output_root)/('sensor-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+digest[:8])
    destination.mkdir(parents=True, exist_ok=False)
    report['generated_at_utc'] = datetime.now(timezone.utc).isoformat()
    (destination/'audit.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    summary = {k:v for k,v in report.items() if k != 'observations'}
    (destination/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False), encoding='utf-8')
    if comparisons:
        (destination/'watering_comparison.json').write_text(json.dumps(comparisons, indent=2, allow_nan=False), encoding='utf-8')
    (destination/'report.html').write_text(render(report, comparisons), encoding='utf-8')
    manifest = {'source_sha256':digest,'policy':report['policy'],
                'exclusion_policy':report.get('exclusion_policy'), 'annotations':annotations,'watering_reports':labels,
                'implementation_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob('*.py'))}}
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv',type=Path)
    parser.add_argument('--output',type=Path,default=Path('reports'),help='Output folder; default reports/ (ignored by Git)')
    parser.add_argument('--annotations',type=Path,help='Optional explicit disturbance exclusions JSON')
    parser.add_argument('--labels',type=Path,help='Optional user-reported watering times JSON; never drives detection')
    args = parser.parse_args()
    try:
        def load(path):
            return json.loads(path.read_text(encoding='utf-8')) if path else None
        labels=load(args.labels)
        if labels is not None:
            if not isinstance(labels,list):raise ValueError('Watering labels must be a JSON list.')
            for label in labels:
                t=datetime.fromisoformat(label['reported_time_utc'])
                if t.tzinfo is None:raise ValueError('Watering label timestamps must include a UTC offset.')
        destination=run(args.csv,args.output,load(args.annotations),labels)
    except (OSError,ValueError,KeyError,TypeError) as error:
        parser.exit(2,f'Cannot generate report: {error}\n')
    print(f'Report ready: {(destination/"report.html").resolve()}')
    print('Open that file in your browser. No database or running system was changed.')


if __name__ == '__main__':
    main()
