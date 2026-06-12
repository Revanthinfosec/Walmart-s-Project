from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

from models import ClassificationResult, FilterOptions, ImageRecord, SearchFilters

DB_PATH = Path(__file__).parent / "fashion.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL UNIQUE,
                classification_json TEXT NOT NULL,
                designer TEXT,
                designer_tags_json TEXT NOT NULL DEFAULT '[]',
                designer_notes TEXT,
                created_at TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS images_fts USING fts5(
                filename,
                description,
                colors,
                patterns,
                style_tags,
                materials,
                occasions,
                trend_notes,
                consumer_profile,
                continent,
                country,
                city,
                garment_type,
                season,
                designer,
                designer_tags,
                designer_notes
            );
            """
        )
        cols = {row[1] for row in conn.execute("PRAGMA table_info(images)")}
        if "designer" not in cols:
            conn.execute("ALTER TABLE images ADD COLUMN designer TEXT")
        if "designer_tags_json" not in cols:
            conn.execute("ALTER TABLE images ADD COLUMN designer_tags_json TEXT NOT NULL DEFAULT '[]'")
        if "designer_notes" not in cols:
            conn.execute("ALTER TABLE images ADD COLUMN designer_notes TEXT")
            if "annotation" in cols:
                conn.execute("UPDATE images SET designer_notes = annotation WHERE designer_notes IS NULL")


def _to_record(row: sqlite3.Row) -> ImageRecord:
    tags = json.loads(row["designer_tags_json"] or "[]")
    return ImageRecord(
        id=row["id"],
        filename=row["filename"],
        file_path=row["file_path"],
        classification=ClassificationResult.model_validate_json(row["classification_json"]),
        designer=row["designer"],
        designer_tags=tags,
        designer_notes=row["designer_notes"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _fts_payload(record: ImageRecord) -> tuple:
    c = record.classification
    return (
        record.filename,
        c.description,
        " ".join(c.colors),
        " ".join(c.patterns),
        " ".join(c.style_tags),
        " ".join(c.materials),
        " ".join(c.occasion),
        " ".join(c.trend_notes),
        c.consumer_profile,
        c.location.continent,
        c.location.country,
        c.location.city,
        c.garment_type.value,
        c.season.value,
        record.designer or "",
        " ".join(record.designer_tags),
        record.designer_notes or "",
    )


def _sync_fts(conn: sqlite3.Connection, image_id: int, record: ImageRecord) -> None:
    conn.execute("DELETE FROM images_fts WHERE rowid = ?", (image_id,))
    conn.execute(
        """
        INSERT INTO images_fts (
            rowid, filename, description, colors, patterns, style_tags, materials,
            occasions, trend_notes, consumer_profile, continent, country, city,
            garment_type, season, designer, designer_tags, designer_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (image_id, *_fts_payload(record)),
    )


def insert_image(
    filename: str,
    file_path: str,
    classification: ClassificationResult,
    *,
    designer: Optional[str] = None,
    designer_tags: Optional[list[str]] = None,
    designer_notes: Optional[str] = None,
) -> ImageRecord:
    now = datetime.now(timezone.utc).isoformat()
    tags_json = json.dumps(designer_tags or [])

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO images (
                filename, file_path, classification_json,
                designer, designer_tags_json, designer_notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (filename, file_path, classification.model_dump_json(), designer, tags_json, designer_notes, now),
        )
        image_id = cursor.lastrowid
        record = ImageRecord(
            id=image_id,
            filename=filename,
            file_path=file_path,
            classification=classification,
            designer=designer,
            designer_tags=designer_tags or [],
            designer_notes=designer_notes,
            created_at=datetime.fromisoformat(now),
        )
        _sync_fts(conn, image_id, record)

    return get_image(image_id)


def get_image(image_id: int) -> ImageRecord:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
    if row is None:
        raise KeyError(f"Image {image_id} not found")
    return _to_record(row)


def list_images() -> list[ImageRecord]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM images ORDER BY created_at DESC").fetchall()
    return [_to_record(row) for row in rows]


def update_image(
    image_id: int,
    *,
    classification: Optional[ClassificationResult] = None,
    designer: Optional[str] = None,
    designer_tags: Optional[list[str]] = None,
    designer_notes: Optional[str] = None,
) -> ImageRecord:
    record = get_image(image_id)

    if classification is not None:
        record.classification = classification
    if designer is not None:
        record.designer = designer
    if designer_tags is not None:
        record.designer_tags = designer_tags
    if designer_notes is not None:
        record.designer_notes = designer_notes

    with get_db() as conn:
        conn.execute(
            """
            UPDATE images
            SET classification_json = ?, designer = ?, designer_tags_json = ?, designer_notes = ?
            WHERE id = ?
            """,
            (
                record.classification.model_dump_json(),
                record.designer,
                json.dumps(record.designer_tags),
                record.designer_notes,
                image_id,
            ),
        )
        _sync_fts(conn, image_id, record)

    return get_image(image_id)


def _json_list_like(field: str, value: str) -> tuple[str, str]:
    return (f"lower(json_extract(i.classification_json, '$.{field}')) LIKE ?", f"%{value.lower()}%")


def _fts_query(raw: str) -> str:
    # Quote each token so FTS5 treats user input as literal terms instead of
    # query syntax — otherwise a stray quote or bare AND/OR raises a syntax error.
    tokens = raw.split()
    return " ".join('"' + token.replace('"', '""') + '"' for token in tokens)


def search_images(filters: SearchFilters) -> list[ImageRecord]:
    where: list[str] = []
    params: list[str] = []

    fts_query = _fts_query(filters.query) if filters.query else ""
    if fts_query:
        where.append("images_fts MATCH ?")
        params.append(fts_query)
    if filters.garment_type:
        where.append("json_extract(i.classification_json, '$.garment_type') = ?")
        params.append(filters.garment_type.value)
    if filters.season:
        where.append("json_extract(i.classification_json, '$.season') = ?")
        params.append(filters.season.value)
    if filters.color:
        clause, param = _json_list_like("colors", filters.color)
        where.append(clause)
        params.append(param)
    if filters.style:
        clause, param = _json_list_like("style_tags", filters.style)
        where.append(clause)
        params.append(param)
    if filters.material:
        clause, param = _json_list_like("materials", filters.material)
        where.append(clause)
        params.append(param)
    if filters.pattern:
        clause, param = _json_list_like("patterns", filters.pattern)
        where.append(clause)
        params.append(param)
    if filters.occasion:
        clause, param = _json_list_like("occasion", filters.occasion)
        where.append(clause)
        params.append(param)
    if filters.trend_note:
        clause, param = _json_list_like("trend_notes", filters.trend_note)
        where.append(clause)
        params.append(param)
    if filters.consumer_profile:
        where.append("lower(json_extract(i.classification_json, '$.consumer_profile')) LIKE ?")
        params.append(f"%{filters.consumer_profile.lower()}%")
    if filters.continent:
        where.append("lower(json_extract(i.classification_json, '$.location.continent')) = ?")
        params.append(filters.continent.lower())
    if filters.country:
        where.append("lower(json_extract(i.classification_json, '$.location.country')) = ?")
        params.append(filters.country.lower())
    if filters.city:
        where.append("lower(json_extract(i.classification_json, '$.location.city')) = ?")
        params.append(filters.city.lower())
    if filters.year:
        where.append("strftime('%Y', i.created_at) = ?")
        params.append(filters.year)
    if filters.month:
        where.append("strftime('%m', i.created_at) = ?")
        params.append(filters.month.zfill(2))
    if filters.designer:
        where.append("lower(i.designer) = ?")
        params.append(filters.designer.lower())

    sql = "SELECT i.* FROM images i"
    if fts_query:
        sql += " JOIN images_fts fts ON fts.rowid = i.id"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY i.created_at DESC"

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [_to_record(row) for row in rows]


def _add_unique(bucket: set[str], value: str) -> None:
    cleaned = value.strip()
    if cleaned:
        bucket.add(cleaned)


def get_filter_options() -> FilterOptions:
    options = {
        "garment_type": set(),
        "season": set(),
        "colors": set(),
        "style_tags": set(),
        "materials": set(),
        "patterns": set(),
        "occasions": set(),
        "consumer_profiles": set(),
        "trend_notes": set(),
        "continents": set(),
        "countries": set(),
        "cities": set(),
        "years": set(),
        "months": set(),
        "designers": set(),
    }

    for record in list_images():
        c = record.classification
        _add_unique(options["garment_type"], c.garment_type.value)
        _add_unique(options["season"], c.season.value)
        for item in c.colors:
            _add_unique(options["colors"], item)
        for item in c.style_tags:
            _add_unique(options["style_tags"], item)
        for item in c.materials:
            _add_unique(options["materials"], item)
        for item in c.patterns:
            _add_unique(options["patterns"], item)
        for item in c.occasion:
            _add_unique(options["occasions"], item)
        for item in c.trend_notes:
            _add_unique(options["trend_notes"], item)
        _add_unique(options["consumer_profiles"], c.consumer_profile)
        _add_unique(options["continents"], c.location.continent)
        _add_unique(options["countries"], c.location.country)
        _add_unique(options["cities"], c.location.city)
        _add_unique(options["years"], str(record.created_at.year))
        _add_unique(options["months"], f"{record.created_at.month:02d}")
        if record.designer:
            _add_unique(options["designers"], record.designer)

    return FilterOptions(**{key: sorted(values) for key, values in options.items()})
