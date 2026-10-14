"""Nightly read-only export from the existing seven-day readings endpoint."""
import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen
from zoneinfo import ZoneInfo
from .__main__ import CHANNELS
from .run import run

URL = 'https://backyardos.onrender.com/readings'
FIELDS = ['device_id','timestamp',*CHANNELS,'id']


def window(now):
    local = now.astimezone(ZoneInfo('America/Chicago'))
    end = datetime.combine(local.date(),datetime.min.time(),ZoneInfo('America/Chicago'))
    start = datetime.combine(local.date()-timedelta(days=1),datetime.min.time(),ZoneInfo('America/Chicago'))
    return start.astimezone(timezone.utc),end.astimezone(timezone.utc)


def select_day(rows, start, end):
    selected=[]
    for row in rows:
        if not isinstance(row,dict) or not set(FIELDS).issubset(row):
            raise ValueError('Endpoint response has missing fields; no report generated')
        try:
            stamp=datetime.fromisoformat(row['timestamp'])
            stamp=stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
        except (ValueError,TypeError):
            raise ValueError('Endpoint contains an invalid timestamp; cannot safely choose the daily window') from None
        if start-timedelta(hours=1) <= stamp < end:selected.append(row)
    return selected


def save_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS,extrasaction='ignore')
        writer.writeheader();writer.writerows(rows)


def daily(output, now=None, fetch=None):
    now=now or datetime.now(timezone.utc)
    start,end=window(now)
    if fetch is None:
        def fetch():
            with urlopen(URL,timeout=45) as response:return json.load(response)
    rows=fetch()
    if not isinstance(rows,list):raise ValueError('Expected a list of readings')
    selected=select_day(rows,start,end)
    day=start.astimezone(ZoneInfo('America/Chicago')).date().isoformat()
    folder=Path(output)/f'daily-{day}'/now.strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True,exist_ok=False)
    save_csv(folder/'seven_day_snapshot.csv',rows)
    save_csv(folder/'daily_with_context.csv',selected)
    report_folder=run(folder/'daily_with_context.csv',folder)
    metadata={'day_central':day,'window_start_utc':start.isoformat(),'window_end_utc_exclusive':end.isoformat(),
              'context_start_utc':(start-timedelta(hours=1)).isoformat(),
              'source_url':URL,'source_limit':'Existing endpoint returns seven days, not complete table history',
              'snapshot_rows':len(rows),'report_rows_with_context':len(selected),
              'actual_day_rows':len(select_day(rows,start+timedelta(hours=1),end)),
              'report':str((report_folder/'report.html').resolve()),
              'audit':str((report_folder/'audit.json').resolve()),
              'warning':'An hour before the day is included as context; final events near midnight may lack followup. No automatic exclusions or changes to detector settings.'}
    (folder/'daily_run.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    page=report_folder/'report.html'
    text=page.read_text()
    banner=f'<section><h2>Daily review: {day} Central time</h2><p>Includes one hour before this day for baseline context. The source is a seven-day endpoint snapshot, not the full historical table. Counts and candidate lists include that context. Late-night events may require tomorrow’s follow-up readings.</p></section>'
    page.write_text(text.replace('<main>','<main>'+banner,1),encoding='utf-8')
    return metadata


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('reports/daily'))
    args=parser.parse_args()
    try:result=daily(args.output)
    except Exception as error:
        # Do not emit response bodies or possible credential-bearing exception URLs.
        parser.exit(2,f'Daily export failed ({type(error).__name__}); no successful run claimed.\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
