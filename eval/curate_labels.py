"""
Build labels.csv by reviewing each eval image with the vision classifier.

For submission: spot-check rows and edit labels.csv where the model is wrong.
This is faster than typing 50+ rows from scratch while keeping you in the loop.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "app" / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND / ".env")

from classifier import classify_image  # noqa: E402

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


def row_from_image(path: Path) -> dict[str, str]:
    result = classify_image(path)
    loc = result.location
    return {
        "filename": path.name,
        "garment_type": result.garment_type.value,
        "style_tags": ", ".join(result.style_tags),
        "materials": ", ".join(result.materials),
        "colors": ", ".join(result.colors),
        "patterns": ", ".join(result.patterns),
        "season": result.season.value,
        "occasion": ", ".join(result.occasion),
        "consumer_profile": result.consumer_profile,
        "trend_notes": ", ".join(result.trend_notes),
        "continent": loc.continent,
        "country": loc.country,
        "city": loc.city,
        "description": result.description.replace("\n", " ").strip(),
    }


def main() -> None:
    images = sorted(IMAGES.glob("*.jpg"))
    if not images:
        raise SystemExit("No images in eval/images — run python eval/download_images.py first")

    rows = []
    for path in images:
        print(f"labeling {path.name}...")
        rows.append(row_from_image(path))

    with LABELS.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} rows to {LABELS}")


if __name__ == "__main__":
    main()
