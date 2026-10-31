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
from advisor_worker import attach_verified_evidence, run_advisor_cycle, response_schema
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
        model_reply = self.reply if reply is None else reply
        with patch("advisor_worker.request_json", side_effect=[self.analysis, model_reply, model_reply]):
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
        schema = received[1]["format"]
        self.assertEqual(schema, response_schema(len(analysis["findings"])))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["interpretations"]["minItems"], len(analysis["findings"]))
        self.assertEqual(schema["properties"]["interpretations"]["maxItems"], len(analysis["findings"]))
        self.assertNotIn("evidence", schema["properties"]["interpretations"]["items"]["properties"])
        self.assertEqual(schema["properties"]["confidence"]["properties"]["level"]["enum"], ["low"])

    def test_rejected_evidence_preserves_previous_output(self):
        self.output.write_text("previous result")
        bad = response_fixture(self.analysis)
        bad["interpretations"][0]["finding_ids"] = ["invented"]
        with self.assertRaisesRegex(ValueError, "Unknown evidence ID"):
            self.run_mocked({"done": True, "message": {"content": json.dumps(bad)}})
        self.assertEqual(self.output.read_text(), "previous result")

    def test_wrong_trend_duration_is_replaced(self):
        bad = response_fixture(self.analysis)
        bad["interpretations"][0]["explanation"] = "Moisture declined over 99 days."
        result = self.run_mocked({"done": True, "message": {"content": json.dumps(bad)}})
        explanation = result["response"]["interpretations"][0]["explanation"]
        self.assertNotIn("99 days", explanation)
        self.assertIn("last qualifying daily average", explanation)

    def test_worker_replaces_model_evidence_with_verified_evidence(self):
        for key, value in (("daily_analysis_start", "2099-01-01"),
                           ("first_to_last_daily_average_change_percentage_points", 999),
                           ("daily_days_analyzed", True)):
            with self.subTest(key=key):
                bad = response_fixture(self.analysis)
                bad["interpretations"][0]["evidence"][key] = value
                result = self.run_mocked({"done": True, "message": {"content": json.dumps(bad)}})
                expected = evidence_for_finding(self.analysis["findings"][0])
                self.assertEqual(result["response"]["interpretations"][0]["evidence"], expected)

    def test_worker_attaches_missing_evidence(self):
        bad = response_fixture(self.analysis)
        del bad["interpretations"][0]["evidence"]
        result = self.run_mocked({"done": True, "message": {"content": json.dumps(bad)}})
        expected = evidence_for_finding(self.analysis["findings"][0])
        self.assertEqual(result["response"]["interpretations"][0]["evidence"], expected)

    def test_worker_restores_complete_correlation_evidence(self):
        bad = response_fixture(self.analysis)
        del bad["interpretations"][1]["evidence"]["consecutive_change_correlation"]
        result = self.run_mocked({"done": True, "message": {"content": json.dumps(bad)}})
        expected = evidence_for_finding(self.analysis["findings"][1])
        self.assertEqual(result["response"]["interpretations"][1]["evidence"], expected)

    def test_relative_dates_replaced_with_verified_dates(self):
        bad = response_fixture(self.analysis)
        bad["interpretations"][0]["explanation"] = "Over the past two days, moisture was mixed."
        result = self.run_mocked({"done": True, "message": {"content": json.dumps(bad)}})
        explanation = result["response"]["interpretations"][0]["explanation"]
        evidence = result["response"]["interpretations"][0]["evidence"]
        self.assertNotIn("past two days", explanation.lower())
        self.assertIn(evidence["daily_analysis_start"], explanation)
        self.assertIn(evidence["daily_analysis_end"], explanation)

    def test_daily_change_matches_daily_trend_basis(self):
        trend = self.analysis["findings"][0]
        self.assertEqual(trend["daily_direction"], "consistently_decreasing")
        self.assertLess(trend["first_to_last_daily_average_change_percentage_points"], 0)

    def test_per_day_and_gap_claims_are_replaced(self):
        bad = response_fixture(self.analysis)
        bad["interpretations"][0]["explanation"] = (
            "Moisture had an average daily decline of 4 points over the same two-day period."
        )
        result = self.run_mocked({"done": True, "message": {"content": json.dumps(bad)}})
        explanation = result["response"]["interpretations"][0]["explanation"]
        self.assertNotIn("average daily decline", explanation.lower())
        self.assertNotIn("same two-day period", explanation.lower())
        self.assertIn("last qualifying daily average", explanation)

    def test_unsupported_correlation_labels_are_replaced(self):
        bad = response_fixture(self.analysis)
        bad["interpretations"][1]["explanation"] = (
            "The correlation was weak and statistically insignificant."
        )
        result = self.run_mocked({"done": True, "message": {"content": json.dumps(bad)}})
        explanation = result["response"]["interpretations"][1]["explanation"]
        self.assertNotIn("weak", explanation.lower())
        self.assertNotIn("insignificant", explanation.lower())
        self.assertIn("significance was not tested", explanation.lower())

    def test_empty_unknowns_rejected(self):
        bad = response_fixture(self.analysis)
        bad["unknowns"] = []
        with self.assertRaisesRegex(ValueError, "Unknowns must identify"):
            self.run_mocked({"done": True, "message": {"content": json.dumps(bad)}})

    def test_overstated_confidence_rejected(self):
        bad = response_fixture(self.analysis)
        bad["confidence"] = {"level": "medium", "reason": "Many observations"}
        with self.assertRaisesRegex(ValueError, "Confidence must remain low"):
            self.run_mocked({"done": True, "message": {"content": json.dumps(bad)}})

    def test_validation_failure_gets_one_successful_repair(self):
        bad = response_fixture(self.analysis)
        bad["unknowns"] = []
        first_reply = {"done": True, "message": {"content": json.dumps(bad)}}
        with patch("advisor_worker.request_json", side_effect=[self.analysis, first_reply, self.reply]) as request:
            result = run_advisor_cycle(backend_url="http://example.test", output_path=self.output)
        self.assertEqual(result["status"], "validated")
        self.assertEqual(request.call_count, 3)
        repair_payload = request.call_args_list[2].kwargs["payload"]
        self.assertIn("failed deterministic validation", repair_payload["messages"][-1]["content"])
        self.assertIn("Field calibration is incomplete", repair_payload["messages"][-1]["content"])

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
