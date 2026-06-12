"""Merge hand-reviewed labels into labels.csv for remaining images via classifier draft."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "app" / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND / ".env")

from classifier import classify_image  # noqa: E402
from manual_labels import MANUAL_LABELS  # noqa: E402

ROOT = Path(__file__).parent
IMAGES = ROOT / "images"
LABELS = ROOT / "labels.csv"

FIELDS = [
    "filename",
    "garment_type",
    "style_tags",
    "materials",
    "colors",
    "patterns",
    "season",
    "occasion",
    "consumer_profile",
    "trend_notes",
    "continent",
    "country",
    "city",
    "description",
]


def from_classifier(path: Path) -> dict[str, str]:
    r = classify_image(path)
    loc = r.location
    return {
        "filename": path.name,
        "garment_type": r.garment_type.value,
        "style_tags": ", ".join(r.style_tags),
        "materials": ", ".join(r.materials),
        "colors": ", ".join(r.colors),
        "patterns": ", ".join(r.patterns),
        "season": r.season.value,
        "occasion": ", ".join(r.occasion),
        "consumer_profile": r.consumer_profile,
        "trend_notes": ", ".join(r.trend_notes),
        "continent": loc.continent,
        "country": loc.country,
        "city": loc.city,
        "description": r.description.replace("\n", " ").strip(),
    }


def main() -> None:
    rows = []
    for path in sorted(IMAGES.glob("*.jpg")):
        if path.name in MANUAL_LABELS:
            row = {"filename": path.name, **MANUAL_LABELS[path.name]}
        else:
            row = from_classifier(path)
        rows.append(row)

    with LABELS.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    manual = sum(1 for r in rows if r["filename"] in MANUAL_LABELS)
    print(f"wrote {len(rows)} rows ({manual} hand-reviewed, {len(rows) - manual} classifier-drafted)")


if __name__ == "__main__":
    main()
