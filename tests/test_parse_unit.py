import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "backend"))

from classifier import normalize_classification, parse_model_json
from models import GarmentType, Season


def test_json_inside_code_fence():
    raw = """```json
{"garment_type": "dress", "colors": ["red"], "materials": ["silk"], "patterns": [], "style_tags": ["elegant"], "season": "summer", "occasion": ["evening"], "consumer_profile": "adult women", "trend_notes": ["minimal"], "location": {"continent": "Europe", "country": "France", "city": "Paris"}, "description": "Red dress"}
```"""
    payload = parse_model_json(raw)
    assert payload["garment_type"] == "dress"


def test_normalizes_full_attribute_set():
    result = normalize_classification(
        {
            "garment_type": "TOP",
            "style": "minimalist",
            "material": "linen, cotton",
            "colors": "white, cream",
            "patterns": ["solid"],
            "season": "spring",
            "occasion": "casual, office",
            "consumer_profile": "young professional",
            "trend_notes": "relaxed tailoring",
            "location": {"continent": "Asia", "country": "Japan", "city": "Tokyo"},
            "description": "White linen blouse",
        }
    )
    assert result.garment_type == GarmentType.TOP
    assert result.materials == ["linen", "cotton"]
    assert result.occasion == ["casual", "office"]
    assert result.location.city == "Tokyo"
    assert result.season == Season.SPRING


def test_unknown_values_get_safe_defaults():
    result = normalize_classification({"garment_type": "jumpsuit", "season": "monsoon"})
    assert result.garment_type == GarmentType.OTHER
    assert result.season == Season.ALL_SEASON
