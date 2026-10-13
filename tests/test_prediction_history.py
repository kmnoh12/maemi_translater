"""Fast SQLite tests with no ML dependencies or external services."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prediction_history import initialize_database, list_predictions, save_prediction


class PredictionHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.db_path = Path(self.tmpdir.name) / "nested" / "history.sqlite3"
        self.result = {
            "aggregate_ranking": [
                {"label": "chammaemi", "mean_probability": 0.87},
                {"label": "malmaemi", "mean_probability": 0.12},
            ],
            "duration_sec": 5.2,
            "final_recommendation": {
                "status": "accepted",
                "source_model": "top200_gpu_cnn",
            },
        }

    def test_creates_database_and_stores_history(self) -> None:
        initialize_database(self.db_path)
        self.assertTrue(self.db_path.exists())
        record_id = save_prediction(
            self.result,
            source_type="upload",
            audio_name="recording.wav",
            db_path=self.db_path,
        )
        self.assertEqual(record_id, 1)
        items = list_predictions(self.db_path)
        self.assertEqual(len(items), 1)
        row = items[0]
        self.assertTrue(row["created_at"].endswith("Z"))
        self.assertEqual(row["source_type"], "upload")
        self.assertEqual(row["audio_name"], "recording.wav")
        self.assertEqual(row["predicted_species"], "chammaemi")
        self.assertEqual(row["confidence"], 0.87)
        self.assertEqual(row["decision_status"], "accepted")
        self.assertEqual(row["duration_sec"], 5.2)
        self.assertEqual(row["source_model"], "top200_gpu_cnn")

    def test_recent_first_and_limit(self) -> None:
        for n in range(3):
            save_prediction(
                self.result, source_type="library", audio_name=f"audio-{n}.wav",
                db_path=self.db_path,
            )
        self.assertEqual([r["audio_name"] for r in list_predictions(self.db_path, limit=2)],
                         ["audio-2.wav", "audio-1.wav"])

    def test_uncertain_prediction_and_untrusted_name(self) -> None:
        result = {
            "aggregate_ranking": [],
            "recommendation": {"status": "no_result"},
        }
        save_prediction(result, source_type="upload", audio_name="/private/folder/a.wav",
                        db_path=self.db_path)
        row = list_predictions(self.db_path)[0]
        self.assertEqual(row["audio_name"], "a.wav")
        self.assertIsNone(row["predicted_species"])
        self.assertIsNone(row["confidence"])
        self.assertEqual(row["decision_status"], "no_result")

    def test_rejects_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            save_prediction(self.result, source_type="bad", audio_name="a.wav",
                            db_path=self.db_path)
        for limit in (0, 101, -1):
            with self.assertRaises(ValueError):
                list_predictions(self.db_path, limit=limit)


if __name__ == "__main__":
    unittest.main()
