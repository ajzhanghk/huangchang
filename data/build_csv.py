#!/usr/bin/env python3
"""Derive huangshang_essays.csv from huangshang_essays.json.

The JSON file is the single source of truth. Run this after editing the JSON
so the CSV stays in sync:

    python data/build_csv.py
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "huangshang_essays.json"
OUT = HERE / "huangshang_essays.csv"

# Column order: the fields requested in the brief, plus a few helpers.
COLUMNS = [
    "id",
    "title",
    "original_collection",
    "approximate_year",
    "place",
    "region",
    "scene_type",
    "themes",
    "summary",
    "editorial_note",
    "proposed_section",
    "source_reference",
    "copyright_status_note",
    "confidence",
    "inclusion",
]


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    rows = data.get("essays", [])
    with OUT.open("w", encoding="utf-8-sig", newline="") as fh:  # BOM for Excel
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            flat = dict(row)
            themes = flat.get("themes")
            if isinstance(themes, list):
                flat["themes"] = "；".join(themes)
            writer.writerow(flat)
    print(f"Wrote {len(rows)} rows to {OUT.name}")


if __name__ == "__main__":
    main()
