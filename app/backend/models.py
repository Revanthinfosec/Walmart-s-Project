from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GarmentType(str, Enum):
    DRESS = "dress"
    TOP = "top"
    BOTTOM = "bottom"
    OUTERWEAR = "outerwear"
    FOOTWEAR = "footwear"
    ACCESSORY = "accessory"
    OTHER = "other"


class Season(str, Enum):
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"
    ALL_SEASON = "all_season"


class LocationContext(BaseModel):
    continent: str = ""
    country: str = ""
    city: str = ""


class ClassificationResult(BaseModel):
    garment_type: GarmentType = GarmentType.OTHER
    style_tags: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    season: Season = Season.ALL_SEASON
    occasion: list[str] = Field(default_factory=list)
    consumer_profile: str = ""
    trend_notes: list[str] = Field(default_factory=list)
    location: LocationContext = Field(default_factory=LocationContext)
    description: str = ""


class ImageRecord(BaseModel):
    id: int
    filename: str
    file_path: str
    classification: ClassificationResult
    designer: Optional[str] = None
    designer_tags: list[str] = Field(default_factory=list)
    designer_notes: Optional[str] = None
    created_at: datetime


class ImageUpdate(BaseModel):
    designer: Optional[str] = None
    designer_tags: Optional[list[str]] = None
    designer_notes: Optional[str] = None


class SearchFilters(BaseModel):
    query: Optional[str] = None
    garment_type: Optional[GarmentType] = None
    season: Optional[Season] = None
    color: Optional[str] = None
    style: Optional[str] = None
    material: Optional[str] = None
    pattern: Optional[str] = None
    occasion: Optional[str] = None
    consumer_profile: Optional[str] = None
    trend_note: Optional[str] = None
    continent: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    year: Optional[str] = None
    month: Optional[str] = None
    designer: Optional[str] = None


class FilterOptions(BaseModel):
    garment_type: list[str] = Field(default_factory=list)
    season: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    occasions: list[str] = Field(default_factory=list)
    consumer_profiles: list[str] = Field(default_factory=list)
    trend_notes: list[str] = Field(default_factory=list)
    continents: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    years: list[str] = Field(default_factory=list)
    months: list[str] = Field(default_factory=list)
    designers: list[str] = Field(default_factory=list)
