from __future__ import annotations

import json
import os
import re
from pathlib import Path

from models import ClassificationResult, GarmentType, LocationContext, Season

JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)

CLASSIFY_PROMPT = """
Look at this fashion inspiration photo and return JSON only with:
- garment_type (dress, top, bottom, outerwear, footwear, accessory, other)
- style_tags (array of style words)
- materials (array)
- colors (array)
- patterns (array)
- season (spring, summer, fall, winter, all_season)
- occasion (array, e.g. casual, evening, market)
- consumer_profile (short string)
- trend_notes (array)
- location (object with continent, country, city — infer from visual cues or say unknown)
- description (2-3 sentences, natural language)
""".strip()


def parse_model_json(raw: str) -> dict:
    text = raw.strip()
    match = JSON_FENCE.search(text)
    if match:
        text = match.group(1)
    return json.loads(text)


def clean_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        return [str(part).strip() for part in value if str(part).strip()]
    return []


def to_classification(data: dict) -> ClassificationResult:
    garment = str(data.get("garment_type", "other")).lower()
    season = str(data.get("season", "all_season")).lower()

    try:
        garment_type = GarmentType(garment)
    except ValueError:
        garment_type = GarmentType.OTHER

    try:
        season_type = Season(season)
    except ValueError:
        season_type = Season.ALL_SEASON

    loc = data.get("location") or {}
    if not isinstance(loc, dict):
        loc = {}

    return ClassificationResult(
        garment_type=garment_type,
        style_tags=clean_list(data.get("style_tags") or data.get("style")),
        materials=clean_list(data.get("materials") or data.get("material")),
        colors=clean_list(data.get("colors") or data.get("color_palette")),
        patterns=clean_list(data.get("patterns") or data.get("pattern")),
        season=season_type,
        occasion=clean_list(data.get("occasion")),
        consumer_profile=str(data.get("consumer_profile", "")).strip(),
        trend_notes=clean_list(data.get("trend_notes")),
        location=LocationContext(
            continent=str(loc.get("continent", "")).strip(),
            country=str(loc.get("country", "")).strip(),
            city=str(loc.get("city", "")).strip(),
        ),
        description=str(data.get("description", "")).strip(),
    )


def classify_image(image_path: Path) -> ClassificationResult:
    if not os.getenv("OPENAI_API_KEY"):
        return stub_result(image_path)

    from openai import OpenAI

    client = OpenAI()
    with image_path.open("rb") as f:
        image_data = f.read()

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini"),
        temperature=0.2,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": CLASSIFY_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{_b64(image_data)}"},
                    },
                ],
            }
        ],
    )

    raw = response.choices[0].message.content or "{}"
    return to_classification(parse_model_json(raw))


def _b64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode("utf-8")


def stub_result(image_path: Path) -> ClassificationResult:
    name = image_path.stem.lower()
    garment_type = GarmentType.OTHER
    for option in GarmentType:
        if option.value in name:
            garment_type = option
            break

    return ClassificationResult(
        garment_type=garment_type,
        style_tags=["streetwear"],
        materials=["cotton"],
        colors=["neutral"],
        patterns=["solid"],
        season=Season.ALL_SEASON,
        occasion=["casual"],
        consumer_profile="young adult",
        trend_notes=["minimal tailoring"],
        location=LocationContext(continent="unknown", country="unknown", city="unknown"),
        description=f"Stub tags for {image_path.name}. Add OPENAI_API_KEY for real classification.",
    )


extract_json_payload = parse_model_json
normalize_classification = to_classification
