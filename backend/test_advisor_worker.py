"""Worker integration checks with real local HTTP and simulated model output."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from advisor_data import prepare_sensor_readings, prepare_moisture_inputs
from advisor_analysis import build_moisture_findings, build_temperature_findings
from advisor_worker import run_advisor_cycle
from advisor_validation import evidence_for_finding


def analysis_fixture():
    readings = [{
        "device_id": "bench-node", "timestamp": f"2026-10-0{day}T{minute // 60:02d}:{minute % 60:02d}:00",
        "soil_moisture_pct": 60 - day + minute / 10000,
        "temperature_c": 23 + minute / 1000,
    } for day in (1, 2) for minute in range(0, 1440, 10)]
    prepared = prepare_sensor_readings(readings)
    summaries, histories = prepare_moisture_inputs(prepared)
    return {"status": "ok", "analysis_window_days": 7, "reading_count": len(prepared),
            "findings": build_moisture_findings(summaries, histories) + build_temperature_findings(prepared)}


def response_fixture(analysis):
    return {"interpretations": [{"finding_ids": [f["id"]], "evidence": evidence_for_finding(f), "explanation": f["observation"]} for f in analysis["findings"]],
            "hypotheses_to_test": [], "unknowns": ["Plant assignments and calibration validation"],
            "confidence": {"level": "low", "reason": "Prototype calibration"}}


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "latest.json"
        self.analysis = analysis_fixture()
        self.reply = {"done": True, "message": {"content": json.dumps(response_fixture(self.analysis))}}

    def run_mocked(self, reply=None):
        with patch("advisor_worker.request_json", side_effect=[self.analysis, self.reply if reply is None else reply]):
            return run_advisor_cycle(backend_url="http://example.test", output_path=self.output)

    def test_complete_http_cycle(self):
        analysis, reply = self.analysis, self.reply
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def send_json(self, value):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(value).encode())
            def do_GET(self):
                received.append(self.path)
                self.send_json(analysis)
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_json(reply)
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}"
            result = run_advisor_cycle(backend_url=url, ollama_url=url, output_path=self.output)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        self.assertEqual(result, json.loads(self.output.read_text()))
        self.assertEqual(result["status"], "validated")
        self.assertEqual(result["analysis"]["reading_count"], 288)
        self.assertEqual(received[0], "/advisor/analysis?days=7")
        self.assertEqual(received[1]["model"], "mistral-nemo")
        self.assertFalse(received[1]["stream"])
        self.assertEqual(received[1]["format"], "json")

    def test_rejected_evidence_preserves_previous_output(self):
        self.output.write_text("previous result")
        bad = response_fixture(self.analysis)
        bad["interpretations"][0]["finding_ids"] = ["invented"]
        with self.assertRaisesRegex(ValueError, "Unknown evidence ID"):
            self.run_mocked({"done": True, "message": {"content": json.dumps(bad)}})
        self.assertEqual(self.output.read_text(), "previous result")

    def test_wrong_duration_rejected(self):
        bad = response_fixture(self.analysis)
        bad["interpretations"][0]["explanation"] = "Moisture declined over 99 days."
        with self.assertRaisesRegex(ValueError, "Duration mismatch"):
            self.run_mocked({"done": True, "message": {"content": json.dumps(bad)}})
        self.assertFalse(self.output.exists())

    def test_wrong_evidence_rejected(self):
        for key, value in (("daily_analysis_start", "2099-01-01"),
                           ("net_change_percentage_points", 999),
                           ("daily_days_analyzed", True)):
            with self.subTest(key=key):
                bad = response_fixture(self.analysis)
                bad["interpretations"][0]["evidence"][key] = value
                with self.assertRaisesRegex(ValueError, "Evidence mismatch"):
                    self.run_mocked({"done": True, "message": {"content": json.dumps(bad)}})
                self.assertFalse(self.output.exists())

    def test_missing_evidence_rejected(self):
        bad = response_fixture(self.analysis)
        del bad["interpretations"][0]["evidence"]
        with self.assertRaisesRegex(ValueError, "Missing structured evidence"):
            self.run_mocked({"done": True, "message": {"content": json.dumps(bad)}})

    def test_missing_correlation_rejected(self):
        bad = response_fixture(self.analysis)
        del bad["interpretations"][1]["evidence"]["consecutive_change_correlation"]
        with self.assertRaisesRegex(ValueError, "Evidence fields mismatch"):
            self.run_mocked({"done": True, "message": {"content": json.dumps(bad)}})

    def test_relative_dates_rejected(self):
        bad = response_fixture(self.analysis)
        bad["interpretations"][0]["explanation"] = "Over the past two days, moisture was mixed."
        with self.assertRaisesRegex(ValueError, "explicit historical dates"):
            self.run_mocked({"done": True, "message": {"content": json.dumps(bad)}})

    def test_malformed_json_rejected(self):
        with self.assertRaises(json.JSONDecodeError):
            self.run_mocked({"done": True, "message": {"content": "not JSON"}})
        self.assertFalse(self.output.exists())

    def test_incomplete_model_response_rejected(self):
        with self.assertRaisesRegex(ValueError, "did not complete"):
            self.run_mocked({"done": False})
        self.assertFalse(self.output.exists())

    def test_no_data_skips_model(self):
        with patch("advisor_worker.request_json", return_value={"status": "insufficient_data", "findings": []}) as request:
            result = run_advisor_cycle(backend_url="http://example.test", output_path=self.output)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(request.call_count, 1)
        self.assertFalse(self.output.exists())

    def test_network_failure_preserves_previous_output(self):
        self.output.write_text("previous result")
        with patch("advisor_worker.request_json", side_effect=TimeoutError("offline")):
            with self.assertRaises(TimeoutError):
                run_advisor_cycle(backend_url="http://example.test", output_path=self.output)
        self.assertEqual(self.output.read_text(), "previous result")


if __name__ == "__main__":
    unittest.main()
