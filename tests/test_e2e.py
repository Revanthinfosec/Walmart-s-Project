import io
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "backend"))

import db
import main

TEST_DB = Path(__file__).parent / "test_e2e.db"
UPLOADS = Path(__file__).parent / "uploads"


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


def test_upload_classify_filter_and_annotate():
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
