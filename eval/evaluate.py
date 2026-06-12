import csv
import sys
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "app" / "backend"
sys.path.insert(0, str(BACKEND))

from classifier import classify_image  # noqa: E402

ROOT = Path(__file__).parent
IMAGES = ROOT / "images"
LABELS = ROOT / "labels.csv"

FIELDS = [
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
]


def read_labels():
    with LABELS.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def as_set(value: str) -> set[str]:
    return {part.strip().lower() for part in value.split(",") if part.strip()}


def predicted_value(result: dict, field: str) -> object:
    if field in ("continent", "country", "city"):
        return result.get("location", {}).get(field, "")
    if field == "style_tags":
        return result.get("style_tags") or result.get("style", [])
    if field == "materials":
        return result.get("materials") or result.get("material", [])
    return result.get(field)


def matches(predicted, expected: str, field: str) -> bool:
    if not expected.strip():
        return True

    if field in ("garment_type", "season", "consumer_profile", "continent", "country", "city"):
        return str(predicted).strip().lower() == expected.strip().lower()

    if field in ("style_tags", "materials", "colors", "patterns", "occasion", "trend_notes"):
        got = {str(v).lower() for v in predicted} if isinstance(predicted, list) else as_set(str(predicted))
        want = as_set(expected)
        if not want:
            return True
        return len(got & want) / len(want) >= 0.5

    return str(predicted).strip().lower() == expected.strip().lower()


def main():
    rows = read_labels()
    totals = defaultdict(int)
    hits = defaultdict(int)
    missing = []

    for row in rows:
        path = IMAGES / row["filename"]
        if not path.exists():
            missing.append(row["filename"])
            continue

        result = classify_image(path).model_dump()
        for field in FIELDS:
            totals[field] += 1
            if matches(predicted_value(result, field), row.get(field, ""), field):
                hits[field] += 1

    print("Per-attribute accuracy")
    print("-" * 44)
    for field in FIELDS:
        total = totals[field]
        right = hits[field]
        pct = (right / total * 100) if total else 0
        print(f"{field:18} {right:3}/{total:3}  {pct:5.1f}%")

    if missing:
        print(f"\nMissing {len(missing)} images from eval/images/")
        for name in missing[:10]:
            print(f"  {name}")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")


if __name__ == "__main__":
    main()
