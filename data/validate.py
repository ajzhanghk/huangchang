#!/usr/bin/env python3
"""Validate huangshang_essays.json for data integrity.

Checks:
  - Unique IDs
  - Duplicate titles (warning, not error)
  - Controlled-vocabulary fields: confidence, inclusion, region
  - Presence of required fields

Usage:
  python data/validate.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

DATA_FILE = Path(__file__).parent / "huangshang_essays.json"

VALID_CONFIDENCE = {"确定", "待核", "推测"}
VALID_INCLUSION = {"必收", "可选", "资料库"}

# Canonical region values (slash-separated combos also accepted)
VALID_REGIONS = {
    "蜀中", "西南", "金陵", "江南", "江北", "北平", "上海", "海外",
    "关中", "西北",
    "待核", "—",
}

REQUIRED_FIELDS = [
    "id", "title", "original_collection", "place", "region",
    "scene_type", "themes", "summary", "editorial_note",
    "proposed_section", "source_reference", "copyright_status_note",
    "confidence", "inclusion",
]


def validate():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    essays = data.get("essays", [])
    errors = []
    warnings = []

    # --- ID uniqueness ---
    id_counts = Counter(e.get("id", "") for e in essays)
    for id_, count in id_counts.items():
        if count > 1:
            errors.append(f"Duplicate id: {id_!r} (x{count})")

    # --- Title duplicates ---
    title_counts = Counter(e.get("title", "") for e in essays)
    for title, count in title_counts.items():
        if count > 1:
            warnings.append(f"Duplicate title: {title!r} (x{count})")

    # --- Per-record checks ---
    for e in essays:
        eid = e.get("id", "?")

        # Required fields present
        for field in REQUIRED_FIELDS:
            if field not in e:
                errors.append(f"{eid}: missing required field '{field}'")

        # confidence
        conf = e.get("confidence")
        if conf not in VALID_CONFIDENCE:
            errors.append(f"{eid}: invalid confidence {conf!r} (must be 确定/待核/推测)")

        # inclusion
        incl = e.get("inclusion")
        if incl not in VALID_INCLUSION:
            errors.append(f"{eid}: invalid inclusion {incl!r} (must be 必收/可选/资料库)")

        # region: allow slash-separated combos
        region = e.get("region", "")
        parts = [r.strip() for r in region.replace("／", "/").split("/")]
        for part in parts:
            if part and part not in VALID_REGIONS:
                warnings.append(f"{eid}: unusual region segment {part!r}")

        # proposed_section must be 0–8
        sec = e.get("proposed_section")
        if sec is not None and not (0 <= int(sec) <= 8):
            errors.append(f"{eid}: proposed_section {sec!r} out of range 0–8")

        # themes must be a list
        themes = e.get("themes")
        if themes is not None and not isinstance(themes, list):
            errors.append(f"{eid}: themes must be a JSON array")

    # --- Summary length check (soft warning at >200 chars) ---
    for e in essays:
        summary = e.get("summary", "")
        if len(summary) > 200:
            warnings.append(
                f"{e.get('id', '?')}: summary length {len(summary)} > 200 chars"
            )

    # --- Print results ---
    for msg in sorted(errors):
        print(f"ERROR: {msg}")
    for msg in sorted(warnings):
        print(f"WARN:  {msg}")

    total = len(essays)
    print(
        f"\n{'FAIL' if errors else 'OK'}: {total} essays | "
        f"{len(errors)} error(s), {len(warnings)} warning(s)."
    )
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    validate()
