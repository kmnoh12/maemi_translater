from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "data-workspace" / "metadata" / "session_metadata_template.csv"

REQUIRED_COLUMNS = [
    "session_id",
    "recorded_at",
    "location_name",
    "latitude",
    "longitude",
    "device_model",
    "distance_estimate_m",
    "habitat_type",
    "background_noise",
    "weather_note",
    "species_label",
    "label_confidence",
    "label_evidence",
    "mixture_flag",
    "acoustic_quality",
    "notes",
    "raw_audio_path",
    "derived_audio_path",
    "review_status",
    "reviewer",
]

ALLOWED = {
    "species_label": {"chammaemi", "malmaemi", "yujimaemi", "unknown"},
    "label_confidence": {"confirmed", "probable", "uncertain"},
    "label_evidence": {
        "adult_photo",
        "exuvia_photo",
        "expert_verified",
        "repeated_field_observation",
    },
    "mixture_flag": {"single_species", "possible_multiple_species", "no_cicada_detected"},
    "acoustic_quality": {"good", "fair", "poor"},
    "review_status": {"pending", "approved", "needs_revision", "rejected"},
}


def validate(path: Path) -> int:
    errors = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing_columns:
            print("Missing columns:", ", ".join(missing_columns))
            return 1

        for line_no, row in enumerate(reader, start=2):
            for field, allowed in ALLOWED.items():
                value = (row.get(field) or "").strip()
                if not value:
                    print(f"{path}:{line_no} missing value for {field}")
                    errors += 1
                    continue
                if value not in allowed:
                    print(f"{path}:{line_no} invalid {field}={value}")
                    errors += 1

    if errors == 0:
        print(f"Validation passed: {path}")
    return errors


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    exit_code = 1 if validate(path) else 0
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
