import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "backend"))

import db
from models import ClassificationResult, GarmentType, LocationContext, SearchFilters, Season

TEST_DB = Path(__file__).parent / "test_fashion.db"


def _classification(**overrides) -> ClassificationResult:
    base = ClassificationResult(
        garment_type=GarmentType.DRESS,
        style_tags=["bohemian"],
        materials=["cotton"],
        colors=["red"],
        patterns=["floral"],
        season=Season.SUMMER,
        occasion=["market"],
        consumer_profile="young adult",
        trend_notes=["artisan"],
        location=LocationContext(continent="Africa", country="Morocco", city="Marrakech"),
        description="Embroidered market dress",
    )
    return base.model_copy(update=overrides)


def _reset_db():
    db.DB_PATH = TEST_DB
    if TEST_DB.exists():
        TEST_DB.unlink()
    db.init_db()


def setup_function():
    _reset_db()


def teardown_module():
    if TEST_DB.exists():
        TEST_DB.unlink()


def add(filename, classification, designer=None, created_at=None):
    record = db.insert_image(
        filename,
        str(Path("/tmp") / filename),
        classification,
        designer=designer,
    )
    fixed = created_at or datetime(2024, 6, 15, tzinfo=timezone.utc).isoformat()
    with db.get_db() as conn:
        conn.execute(
            "UPDATE images SET created_at = ?, designer = ? WHERE id = ?",
            (fixed, designer, record.id),
        )
        updated = db.get_image(record.id)
        db._sync_fts(conn, record.id, updated)


def test_garment_and_material_filters():
    add("dress-a.jpg", _classification())
    add("top-b.jpg", _classification(garment_type=GarmentType.TOP, materials=["denim"]))

    by_garment = db.search_images(SearchFilters(garment_type=GarmentType.DRESS))
    assert len(by_garment) == 1

    by_material = db.search_images(SearchFilters(material="denim"))
    assert by_material[0].filename == "top-b.jpg"


def test_location_filters():
    add("dress-marrakech.jpg", _classification())
    add(
        "dress-paris.jpg",
        _classification(location=LocationContext(continent="Europe", country="France", city="Paris")),
    )

    in_morocco = db.search_images(SearchFilters(country="Morocco"))
    assert len(in_morocco) == 1
    assert in_morocco[0].filename == "dress-marrakech.jpg"

    in_africa = db.search_images(SearchFilters(continent="Africa"))
    assert any(img.filename == "dress-marrakech.jpg" for img in in_africa)


def test_time_and_designer_filters():
    add("june-look.jpg", _classification(), designer="Amina", created_at=datetime(2024, 6, 10, tzinfo=timezone.utc).isoformat())
    add("winter-look.jpg", _classification(season=Season.WINTER), designer="Leo", created_at=datetime(2023, 12, 5, tzinfo=timezone.utc).isoformat())

    june_2024 = db.search_images(SearchFilters(year="2024", month="06"))
    assert any(img.filename == "june-look.jpg" for img in june_2024)

    by_designer = db.search_images(SearchFilters(designer="Leo"))
    assert by_designer[0].filename == "winter-look.jpg"


def test_full_text_search_on_description():
    add("dress-search.jpg", _classification(description="embroidered neckline at artisan market"))
    results = db.search_images(SearchFilters(query="embroidered"))
    assert any(img.filename == "dress-search.jpg" for img in results)
