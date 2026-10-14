from datetime import datetime,timezone
import json
from pathlib import Path
import tempfile
import unittest
from .daily import daily,window,select_day,FIELDS


class DailyTests(unittest.TestCase):
    def test_dst_calendar_days(self):
        for now,hours in [('2026-03-09T05:10:00+00:00',23),('2026-11-02T06:10:00+00:00',25)]:
            start,end=window(datetime.fromisoformat(now))
            self.assertEqual((end-start).total_seconds(),hours*3600)

    def test_context_and_end_exclusion(self):
        start,end=window(datetime(2026,10,14,5,10,tzinfo=timezone.utc))
        rows=[dict(zip(FIELDS,['backyard-node-01',stamp,2900,0,25,50,990,i])) for i,stamp in enumerate([
            '2026-10-13T03:59:59+00:00','2026-10-13T04:00:00+00:00','2026-10-13T05:00:00+00:00','2026-10-14T04:59:59+00:00','2026-10-14T05:00:00+00:00'])]
        self.assertEqual([r['id'] for r in select_day(rows,start,end)],[1,2,3])
        with tempfile.TemporaryDirectory() as temp:
            result=daily(temp,datetime(2026,10,14,5,10,tzinfo=timezone.utc),lambda:rows)
            self.assertEqual(result['actual_day_rows'],2)
            self.assertTrue(Path(result['report']).exists())
            self.assertIn('Daily review: 2026-10-13',Path(result['report']).read_text())

    def test_failure_produces_no_success_report(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):daily(temp,fetch=lambda:[{'id':1}])
            self.assertEqual(list(Path(temp).iterdir()),[])
