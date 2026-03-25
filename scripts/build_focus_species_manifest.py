from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_csv", type=Path)
    parser.add_argument("--species", required=True, help="Comma-separated focus species codes")
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=ROOT / "ml-workspace" / "experiments" / "focus_species" / "focus_manifest.csv",
    )
    args = parser.parse_args()

    focus_species = {part.strip() for part in args.species.split(",") if part.strip()}
    rows = load_rows(args.manifest_csv.resolve())
    selected = [row for row in rows if row["species_code"] in focus_species]
    if not selected:
        raise SystemExit("No rows matched the requested focus species")

    args.out_csv = args.out_csv.resolve()
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(selected[0].keys()))
        writer.writeheader()
        writer.writerows(selected)

    print(f"Wrote {len(selected)} rows to {args.out_csv}")
    print("Focus species:", ", ".join(sorted(focus_species)))


if __name__ == "__main__":
    main()
