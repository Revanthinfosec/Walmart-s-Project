from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import classifier
import db
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from models import ClassificationResult, FilterOptions, GarmentType, ImageRecord, ImageUpdate, SearchFilters, Season

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Fashion Inspiration", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.on_event("startup")
def startup() -> None:
    db.init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/filters", response_model=FilterOptions)
def filter_options() -> FilterOptions:
    return db.get_filter_options()


def _build_filters(
    query: Optional[str] = None,
    garment_type: Optional[str] = None,
    season: Optional[str] = None,
    color: Optional[str] = None,
    style: Optional[str] = None,
    material: Optional[str] = None,
    pattern: Optional[str] = None,
    occasion: Optional[str] = None,
    consumer_profile: Optional[str] = None,
    trend_note: Optional[str] = None,
    continent: Optional[str] = None,
    country: Optional[str] = None,
    city: Optional[str] = None,
    year: Optional[str] = None,
    month: Optional[str] = None,
    designer: Optional[str] = None,
) -> SearchFilters:
    return SearchFilters(
        query=query,
        garment_type=GarmentType(garment_type) if garment_type else None,
        season=Season(season) if season else None,
        color=color,
        style=style,
        material=material,
        pattern=pattern,
        occasion=occasion,
        consumer_profile=consumer_profile,
        trend_note=trend_note,
        continent=continent,
        country=country,
        city=city,
        year=year,
        month=month,
        designer=designer,
    )


@app.get("/images", response_model=list[ImageRecord])
def list_images(
    query: Optional[str] = None,
    garment_type: Optional[str] = None,
    season: Optional[str] = None,
    color: Optional[str] = None,
    style: Optional[str] = None,
    material: Optional[str] = None,
    pattern: Optional[str] = None,
    occasion: Optional[str] = None,
    consumer_profile: Optional[str] = None,
    trend_note: Optional[str] = None,
    continent: Optional[str] = None,
    country: Optional[str] = None,
    city: Optional[str] = None,
    year: Optional[str] = None,
    month: Optional[str] = None,
    designer: Optional[str] = None,
) -> list[ImageRecord]:
    filters = _build_filters(
        query=query,
        garment_type=garment_type,
        season=season,
        color=color,
        style=style,
        material=material,
        pattern=pattern,
        occasion=occasion,
        consumer_profile=consumer_profile,
        trend_note=trend_note,
        continent=continent,
        country=country,
        city=city,
        year=year,
        month=month,
        designer=designer,
    )
    if any(vars(filters).values()):
        return db.search_images(filters)
    return db.list_images()


@app.get("/images/{image_id}", response_model=ImageRecord)
def get_image(image_id: int) -> ImageRecord:
    try:
        return db.get_image(image_id)
    except KeyError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@app.post("/images/upload", response_model=ImageRecord)
async def upload_image(
    file: UploadFile = File(...),
    designer: Optional[str] = Form(default=None),
    designer_notes: Optional[str] = Form(default=None),
) -> ImageRecord:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Need a filename")

    path = UPLOAD_DIR / file.filename
    with path.open("wb") as out:
        out.write(await file.read())

    tags = classifier.classify_image(path)
    return db.insert_image(
        file.filename,
        str(path),
        tags,
        designer=designer,
        designer_notes=designer_notes,
    )


@app.post("/images/{image_id}/classify", response_model=ImageRecord)
def reclassify(image_id: int) -> ImageRecord:
    try:
        record = db.get_image(image_id)
    except KeyError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err

    tags = classifier.classify_image(Path(record.file_path))
    return db.update_image(image_id, classification=tags)


@app.patch("/images/{image_id}", response_model=ImageRecord)
def patch_image(image_id: int, body: ImageUpdate) -> ImageRecord:
    try:
        return db.update_image(
            image_id,
            designer=body.designer,
            designer_tags=body.designer_tags,
            designer_notes=body.designer_notes,
        )
    except KeyError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@app.post("/classify/preview", response_model=ClassificationResult)
async def preview(file: UploadFile = File(...)) -> ClassificationResult:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Need a filename")

    path = UPLOAD_DIR / f"preview_{file.filename}"
    with path.open("wb") as out:
        out.write(await file.read())

    return classifier.classify_image(path)
