import csv
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "app" / "backend"
sys.path.insert(0, str(BACKEND))

from classifier import classify_image  # noqa: E402

try:  # only present when the OpenAI client is installed
    import openai

    RATE_LIMIT_ERRORS: tuple = (openai.RateLimitError,)
except Exception:  # pragma: no cover - stub/offline mode
    RATE_LIMIT_ERRORS = ()

# Pace requests so a low tokens-per-minute tier doesn't hard-fail the run.
REQUEST_DELAY = 1.0       # seconds between images
MAX_RETRIES = 8           # retries on a 429 rate-limit
MAX_BACKOFF = 60.0        # cap on the backoff wait


def classify_with_retry(path: Path):
    """Classify one image, backing off and retrying when rate-limited."""
    for attempt in range(MAX_RETRIES):
        try:
            return classify_image(path)
        except RATE_LIMIT_ERRORS:
            wait = min(MAX_BACKOFF, 8.0 * (2 ** attempt))
            print(f"    rate limited - waiting {wait:.0f}s ({attempt + 1}/{MAX_RETRIES})", flush=True)
            time.sleep(wait)
    # Last attempt: let any error surface instead of silently swallowing it.
    return classify_image(path)

ROOT = Path(__file__).parent
IMAGES = ROOT / "images"
LABELS = ROOT / "labels.csv"
# Cache raw model predictions so a re-score never re-pays for the API run.
CACHE = ROOT / "predictions_cache.json"

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

    cache: dict = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text())
        except Exception:
            cache = {}

    total_rows = len(rows)
    for index, row in enumerate(rows, start=1):
        filename = row["filename"]
        path = IMAGES / filename
        if not path.exists():
            missing.append(filename)
            continue

        if filename in cache:
            result = cache[filename]
            print(f"[{index}/{total_rows}] {filename} (cached)", flush=True)
        else:
            print(f"[{index}/{total_rows}] {filename}", flush=True)
            # mode="json" serializes enums to their values ("dress"), so scalar
            # comparisons work; the python-mode dump leaks "GarmentType.DRESS".
            result = classify_with_retry(path).model_dump(mode="json")
            cache[filename] = result
            CACHE.write_text(json.dumps(cache, indent=2))
            time.sleep(REQUEST_DELAY)

        for field in FIELDS:
            totals[field] += 1
            if matches(predicted_value(result, field), row.get(field, ""), field):
                hits[field] += 1

    print()
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
