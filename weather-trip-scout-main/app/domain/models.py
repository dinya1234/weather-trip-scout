from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any


@dataclass(frozen=True)
class Point:
    lat: float
    lon: float


@dataclass
class Place:
    name: str
    point: Point
    place_id: str | None = None
    tags: dict[str, Any] = field(default_factory=dict)


@dataclass
class HourlyForecastPoint:
    time: datetime
    temp_c: float
    wind_kmh: float
    precip_mm: float
    precip_probability: float | None
    cloud_cover: float | None


@dataclass
class PlaceScore:
    place: Place
    final_score: float
    best_time_start: time
    best_time_end: time
    summary: str
    breakdown: dict[str, float]


@dataclass(frozen=True)
class RouteInfo:
    distance_km: float
    duration_minutes: int
    google_maps_url: str


@dataclass
class PlaceInfrastructure:
    hotels: list[str] = field(default_factory=list)
    cafes: list[str] = field(default_factory=list)
    attractions: list[str] = field(default_factory=list)


@dataclass
class TripVisit:
    place_id: str
    place_name: str
    visit_date: date
    score: float | None = None
    rating: int | None = None
    note: str | None = None


@dataclass
class EnrichedPlaceScore:
    score: PlaceScore
    route: RouteInfo | None = None
    infrastructure: PlaceInfrastructure | None = None
    previous_visit: TripVisit | None = None


@dataclass
class ReportPayload:
    text: str
    image_path: str | None = None
