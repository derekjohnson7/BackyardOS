import copy
import unittest
from datetime import datetime, timedelta
from .__main__ import analyze


def fixture():
    return [dict(device_id='backyard-node-02', timestamp=(datetime(2026,9,1)+timedelta(seconds=603*i)).isoformat(), id=str(i),
        soil_moisture_pct=str(p), soil_moisture_raw=str(round(2800-p*17.1)), temperature_c=str(25+i/10),
        humidity_pct=str(50+i/10), pressure_hpa=str(990+i/10)) for i,p in enumerate([40,41,55,56,55,54])]


class DiagnosticsTests(unittest.TestCase):
    def test_evidence_preservation(self):
        rows = fixture()
        before = copy.deepcopy(rows)
        r = analyze(rows)
        self.assertEqual(rows, before)
        self.assertEqual(len(r['candidates']), 1)
        self.assertEqual(r['candidates'][0]['evidence']['source_rows'], [1,2,3,4,5])
        self.assertEqual(r['devices']['backyard-node-02']['median_positive_interval_seconds'],603)
        self.assertEqual(r['observations'][0]['source'],rows[0])

    def test_barriers(self):
        for field,value in [('timestamp','bad'),('timestamp','2026-09-02T00:00:00'),('timestamp','2026-09-01T00:10:03'),
            ('timestamp','2026-09-01T00:11:00'),('soil_moisture_pct','100'),('soil_moisture_raw','0'),
            ('temperature_c','184.13'),('pressure_hpa','-1'),('humidity_pct','NaN'),('soil_moisture_raw','2500')]:
            with self.subTest(field=field,value=value):
                rows = fixture()
                rows[2][field] = value
                self.assertEqual(analyze(rows)['candidates'],[])

    def test_followup_and_spike(self):
        self.assertEqual(analyze(fixture()[:3])['candidates'],[])
        rows=fixture()
        rows[3].update(soil_moisture_pct='41',soil_moisture_raw='2099')
        self.assertEqual(analyze(rows)['candidates'],[])

    def test_frozen_channels_and_exclusion(self):
        rows=fixture()
        for row in rows: row.update(temperature_c='25',humidity_pct='50',pressure_hpa='990')
        r=analyze(rows+[dict(rows[0],device_id='backyard-node-03')])
        self.assertEqual(r['candidates'],[])
        self.assertIn('frozen_bme_tuple',r['observations'][0]['flags']['temperature_c'])
        self.assertFalse(r['observations'][0]['flags'].get('soil_moisture_raw'))
        self.assertNotIn('backyard-node-03',r['devices'])

    def test_device_independence_and_unsorted_input(self):
        rows=fixture()
        r=analyze(list(reversed(rows+[dict(x,id='other-'+x['id'],device_id='backyard-node-01',temperature_c='184.13') for x in rows])))
        self.assertEqual(len(r['candidates']),1)
        self.assertEqual(r['candidates'][0]['device_id'],'backyard-node-02')

    def test_freeze_does_not_bridge_gap(self):
        rows=fixture()
        for i,r in enumerate(rows):
            r['temperature_c']='25'
            if i>=3: r['timestamp']=(datetime(2026,9,2)+timedelta(seconds=603*i)).isoformat()
        self.assertTrue(all('unchanged_run' not in r['flags']['temperature_c'] for r in analyze(rows)['observations']))

    def test_clipped_watering_preserves_flags(self):
        rows=fixture()
        for r,raw in zip(rows,[2991,2981,1072,1023,1040,1039]):
            r['soil_moisture_raw']=str(raw)
            r['soil_moisture_pct']=str(max(0,min(100,(2800-raw)/17.1)))
        report=analyze(rows)
        self.assertEqual(len(report['candidates']),1)
        self.assertIn('calibration_clipped',report['observations'][2]['flags']['soil_moisture_pct'])
        self.assertIn('abrupt_step',report['observations'][2]['flags']['soil_moisture_raw'])
        self.assertEqual(report['candidates'][0]['confidence'],'low')
        rows[2]['soil_moisture_raw']='0'
        self.assertEqual(analyze(rows)['candidates'],[])

    def test_flat_clipping_is_not_watering(self):
        rows=fixture()
        for i,r in enumerate(rows):
            r.update(soil_moisture_pct='100',soil_moisture_raw=str(1000+i))
        self.assertEqual(analyze(rows)['candidates'],[])

    def test_utc_central_and_aware_equivalence(self):
        rows=fixture()
        report=analyze(rows)
        self.assertEqual(report['observations'][0]['timestamp_central'],'2026-08-31T19:00:00-05:00')
        for r in rows: r['timestamp'] += '+00:00'
        self.assertEqual(report['candidates'],analyze(rows)['candidates'])

    def test_dry_glitch_then_recovery_is_withheld(self):
        rows=fixture()
        for r,raw in zip(rows,[1344,3099,2928,1362,1142,1147]):
            r.update(soil_moisture_raw=str(raw),soil_moisture_pct=str(max(0,min(100,(2800-raw)/17.1))))
        report=analyze(rows)
        self.assertEqual(report['candidates'],[])
        self.assertTrue(any('soil_moisture_raw:abrupt_step' in w['reasons'] for w in report['withheld_transitions']))

    def test_fast_sampling_has_explicit_reason(self):
        rows=fixture()
        for i,r in enumerate(rows):r['timestamp']=(datetime(2026,9,1)+timedelta(seconds=8*i)).isoformat()
        report=analyze(rows)
        self.assertEqual(report['candidates'],[])
        self.assertIn('record:short_interval',report['withheld_transitions'][0]['reasons'])

    def test_frozen_raw_after_rise_blocks_candidate(self):
        rows=fixture()
        for i in range(3):
            r=dict(rows[-1],id='extra'+str(i),timestamp=(datetime(2026,9,1)+timedelta(seconds=603*(6+i))).isoformat())
            rows.append(r)
        for r in rows[2:]:r.update(soil_moisture_pct='55',soil_moisture_raw='1859')
        self.assertEqual(analyze(rows)['candidates'],[])

    def test_duplicate_ids_block_candidate(self):
        rows=fixture();rows[2]['id']=rows[1]['id']
        r=analyze(rows)
        self.assertEqual(r['candidates'],[])
        self.assertIn('record:duplicate_id',r['withheld_transitions'][0]['reasons'])

    def test_missing_pct_is_flagged_without_crashing(self):
        rows=fixture();rows[2]['soil_moisture_pct']=''
        self.assertEqual(analyze(rows)['candidates'],[])

class DisturbanceReviewTests(unittest.TestCase):
    def setUp(self):
        import csv,json
        from pathlib import Path
        root=Path(__file__).resolve().parent/'fixtures'
        with (root/'node01_oct13_screenshot.csv').open(newline='') as f:self.rows=list(csv.DictReader(f))
        self.annotations=json.loads((root/'node01_oct13_annotations.json').read_text())

    def review(self):
        from .disturbance_review import review_with_exclusions
        return review_with_exclusions(self.rows,self.annotations)

    def test_explicit_exclusion_yields_warned_response(self):
        before=copy.deepcopy(self.rows)
        r=self.review()
        self.assertEqual(self.rows,before)
        self.assertEqual(r['candidates'],[])
        self.assertEqual(len(r['assisted_candidates']),1)
        c=r['assisted_candidates'][0]
        self.assertEqual(c['classification'],'possible_watering_with_disturbance_warning')
        self.assertNotIn('13812',c['evidence']['record_ids'])
        self.assertEqual(c['evidence']['excluded_records'][0]['source']['id'],'13812')
        self.assertIn('record:short_interval',r['withheld_transitions'][0]['reasons'])

    def test_no_annotation_no_assisted_detection(self):
        self.annotations={}
        self.assertEqual(self.review()['assisted_candidates'],[])

    def test_wrong_timestamp_rejected(self):
        self.annotations['excluded_from_watering_interpretation'][0]['timestamp_utc']='2026-10-13T19:01:29+00:00'
        with self.assertRaises(ValueError):self.review()

    def test_long_gap_not_bridged(self):
        self.rows=[r for r in self.rows if r['id']!='13814']
        self.assertEqual(self.review()['assisted_candidates'],[])

    def test_environment_fault_after_exclusion_still_blocks(self):
        self.rows[10]['temperature_c']='184.13'
        self.assertEqual(self.review()['assisted_candidates'],[])

    def test_clipped_dry_baseline_hides_recovery(self):
        # All percentages remain 0, but raw values expose a recent dry glitch.
        self.rows[7]['soil_moisture_raw']='4000'
        self.assertEqual(self.review()['assisted_candidates'],[])

    def test_reported_watering_label_does_not_drive_result(self):
        self.annotations.pop('reported_watering')
        self.assertEqual(len(self.review()['assisted_candidates']),1)
