import io
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "backend"))

import classifier
import db
import main
from models import ClassificationResult, GarmentType, LocationContext, Season

TEST_DB = Path(__file__).parent / "test_e2e.db"
UPLOADS = Path(__file__).parent / "uploads"


def _fake_classification(image_path: Path) -> ClassificationResult:
    """Deterministic stand-in for the model so the e2e test never hits the network."""
    return ClassificationResult(
        garment_type=GarmentType.DRESS,
        style_tags=["summer"],
        materials=["cotton"],
        colors=["yellow"],
        patterns=["floral"],
        season=Season.SUMMER,
        occasion=["casual"],
        consumer_profile="young adult",
        trend_notes=["bright colors"],
        location=LocationContext(continent="unknown", country="unknown", city="unknown"),
        description="A light summer dress with a floral pattern.",
    )


def setup_module():
    db.DB_PATH = TEST_DB
    main.UPLOAD_DIR = UPLOADS
    UPLOADS.mkdir(exist_ok=True)
    if TEST_DB.exists():
        TEST_DB.unlink()
    db.init_db()


def teardown_module():
    if TEST_DB.exists():
        TEST_DB.unlink()


def test_upload_classify_filter_and_annotate(monkeypatch):
    # Mock the model call: the e2e flow is what we're testing, not the live API.
    monkeypatch.setattr(classifier, "classify_image", _fake_classification)

    client = TestClient(main.app)

    assert client.get("/health").json()["status"] == "ok"

    upload = client.post(
        "/images/upload",
        files={"file": ("summer-dress.jpg", io.BytesIO(b"fake"), "image/jpeg")},
        data={"designer": "Jordan"},
    )
    assert upload.status_code == 200

    created = upload.json()
    image_id = created["id"]
    assert created["designer"] == "Jordan"
    assert created["classification"]["garment_type"] == "dress"
    assert "materials" in created["classification"]

    filtered = client.get("/images", params={"garment_type": "dress", "designer": "Jordan"})
    assert any(item["id"] == image_id for item in filtered.json())

    filters = client.get("/filters")
    assert filters.status_code == 200
    assert "dress" in filters.json()["garment_type"]

    saved = client.patch(
        f"/images/{image_id}",
        json={"designer_tags": ["resort", "reference"], "designer_notes": "Great sleeve shape"},
    )
    body = saved.json()
    assert body["designer_tags"] == ["resort", "reference"]
    assert body["designer_notes"] == "Great sleeve shape"

    search = client.get("/images", params={"query": "sleeve"})
    assert any(item["id"] == image_id for item in search.json())
