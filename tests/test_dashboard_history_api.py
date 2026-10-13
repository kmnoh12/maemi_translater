"""Dashboard HTTP integration tests using a fake predictor (no model required)."""

from __future__ import annotations

import http.client
import importlib
import io
import json
import sys
import tempfile
import threading
import types
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

# The main project targets Python 3.12; cgi was removed in 3.13.
# Upload parsing is unchanged and does not run in these API integration tests.
if sys.version_info >= (3, 13):
    sys.modules.setdefault("cgi", types.ModuleType("cgi"))

stub_predictor = types.ModuleType("predict_audio_with_baseline")
stub_predictor.predict_audio = lambda path, model: {
    "duration_sec": 4.5,
    "aggregate_ranking": [{"label": "malmaemi", "mean_probability": 0.93}],
    "final_recommendation": {"status": "accepted", "source_model": "test_cnn"},
}
with patch.dict(sys.modules, {"predict_audio_with_baseline": stub_predictor}):
    dashboard = importlib.import_module("run_dashboard_app")


class DashboardHistoryApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / "one.wav").write_bytes(b"test audio placeholder")
        self.db = self.root / "private" / "history.sqlite3"
        self.root_patch = patch.object(dashboard, "ROOT", self.root)
        self.db_patch = patch.object(dashboard, "DB_PATH", self.db)
        self.upload_patch = patch.object(dashboard, "UPLOAD_DIR", self.root / "uploads")
        self.upload_patch.start()
        self.addCleanup(self.upload_patch.stop)
        self.root_patch.start()
        self.db_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.addCleanup(self.db_patch.stop)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), dashboard.DashboardHandler)
        self.addCleanup(self.server.server_close)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._stop_server)

    def _stop_server(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=2)

    def request_json(self, method: str, path: str, data: dict | None = None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=4)
        headers = {"Content-Type": "application/json"} if data is not None else {}
        connection.request(method, path, body=json.dumps(data) if data is not None else None,
                           headers=headers)
        response = connection.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        status = response.status
        connection.close()
        return status, body

    def test_prediction_is_persisted_and_can_be_queried(self) -> None:
        code, result = self.request_json("POST", "/api/predict-path", {"audio_path": "one.wav"})
        self.assertEqual(code, 200)
        self.assertTrue(result["history_saved"])
        self.assertEqual(result["history_id"], 1)
        code, history = self.request_json("GET", "/api/history?limit=5")
        self.assertEqual(code, 200)
        self.assertEqual(history["count"], 1)
        self.assertEqual(history["items"][0]["predicted_species"], "malmaemi")
        self.assertEqual(history["items"][0]["audio_name"], "one.wav")
        self.assertEqual(history["items"][0]["source_type"], "library")

    def test_bad_history_limit_and_failed_prediction_do_not_write(self) -> None:
        for value in ("bad", "0", "101"):
            code, body = self.request_json("GET", "/api/history?limit=" + value)
            self.assertEqual(code, 400)
            self.assertIn("error", body)
        code, _ = self.request_json("POST", "/api/predict-path", {"audio_path": "missing.wav"})
        self.assertEqual(code, 404)
        code, history = self.request_json("GET", "/api/history")
        self.assertEqual(code, 200)
        self.assertEqual(history["count"], 0)

    def test_uploaded_prediction_is_persisted(self) -> None:
        fake_form = {
            "audio": types.SimpleNamespace(file=io.BytesIO(b"sample"), filename="field.wav")
        }
        with patch.object(dashboard.cgi, "FieldStorage", return_value=fake_form, create=True):
            connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=4)
            connection.request("POST", "/api/predict", body=b"multipart-placeholder",
                               headers={"Content-Type": "multipart/form-data; boundary=test"})
            response = connection.getresponse()
            result = json.loads(response.read().decode("utf-8"))
            status = response.status
            connection.close()
        self.assertEqual(status, 200)
        self.assertTrue(result["history_saved"])
        _, history = self.request_json("GET", "/api/history")
        self.assertEqual(history["items"][0]["source_type"], "upload")
        self.assertEqual(history["items"][0]["audio_name"], "field.wav")

    def test_inference_failure_does_not_save_a_row(self) -> None:
        with patch.object(dashboard, "predict_audio", side_effect=RuntimeError("model unavailable")):
            code, response = self.request_json("POST", "/api/predict-path", {"audio_path": "one.wav"})
        self.assertEqual(code, 400)
        self.assertIn("error", response)
        _, history = self.request_json("GET", "/api/history")
        self.assertEqual(history["count"], 0)


if __name__ == "__main__":
    unittest.main()
