import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from .run import run


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.fixtures=Path(__file__).parent/'fixtures'
        self.source=self.fixtures/'node01_oct13_screenshot.csv'

    def test_one_command_outputs_match_input_and_keep_modes_separate(self):
        before=self.source.read_bytes()
        annotations=json.loads((self.fixtures/'node01_oct13_annotations.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            output=run(self.source,temp,annotations)
            report=json.loads((output/'audit.json').read_text())
            page=(output/'report.html').read_text()
            self.assertEqual(report['source_sha256'],hashlib.sha256(before).hexdigest())
            self.assertEqual(len(report['assisted_candidates']),1)
            self.assertEqual(report['candidates'],[])
            self.assertIn('Assisted: disturbance warning',page)
            self.assertIn('Readings arrived less than five minutes apart.',page)
            self.assertIn('2026-10-13',page)
            self.assertNotIn('August 22',page)
            self.assertTrue((output/'manifest.json').exists())
            self.assertNotIn('observations',json.loads((output/'summary.json').read_text()))
            other=run(self.source,temp)
            self.assertNotEqual(output,other)
        self.assertEqual(self.source.read_bytes(),before)

    def test_empty_export_and_invalid_measurements_render(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'empty.csv'
            source.write_text(self.source.read_text().splitlines()[0]+'\n')
            out=run(source,Path(temp)/'out')
            self.assertIn('0 source rows',(out/'report.html').read_text())
            with self.source.open(newline='') as f:rows=list(csv.DictReader(f))
            rows[0]['timestamp']='bad'
            rows[1]['soil_moisture_pct']='NaN'
            with source.open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
            out=run(source,Path(temp)/'out')
            self.assertTrue((out/'report.html').exists())

    def test_cli_rejects_bad_schema_without_output(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'bad.csv';source.write_text('id\n1\n')
            out=Path(temp)/'reports'
            process=subprocess.run([sys.executable,'-m','experiments.sensor_intelligence.run',str(source),'--output',str(out)],capture_output=True,text=True)
            self.assertEqual(process.returncode,2)
            self.assertIn('missing required columns',process.stderr)
            self.assertFalse(out.exists())

    def test_html_escapes_source_identifiers(self):
        from .build_report import render
        from .__main__ import analyze
        with self.source.open(newline='') as f:rows=list(csv.DictReader(f))
        rows[0]['id']='<script>alert(1)</script>'
        page=render(analyze(rows))
        self.assertNotIn('<script>',page)
        self.assertIn('&lt;script&gt;',page)
