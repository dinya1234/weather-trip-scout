from datetime import date, time

from app.domain.models import (
    EnrichedPlaceScore,
    Place,
    PlaceInfrastructure,
    PlaceScore,
    Point,
    RouteInfo,
    TripVisit,
)
from app.providers.maps.staticmap_osm import StaticMapOSMBuilder
from app.services.report_service import ReportService


def _sample_enriched() -> list[EnrichedPlaceScore]:
    score = PlaceScore(
        place=Place("Starnberg", Point(48.0, 11.0), place_id="123"),
        final_score=87.0,
        best_time_start=time(10, 0),
        best_time_end=time(16, 0),
        summary="Excellent conditions",
        breakdown={},
    )
    return [
        EnrichedPlaceScore(
            score=score,
            route=RouteInfo(
                distance_km=42.0,
                duration_minutes=45,
                google_maps_url="https://www.google.com/maps/dir/?api=1",
            ),
            infrastructure=PlaceInfrastructure(
                hotels=["Hotel Alpha"],
                cafes=["Cafe Beta"],
                attractions=["Lake View"],
            ),
            previous_visit=TripVisit(
                place_id="123",
                place_name="Starnberg",
                visit_date=date(2026, 5, 1),
                rating=5,
                note="Great day",
            ),
        )
    ]


def test_report_includes_route_infrastructure_and_history() -> None:
    service = ReportService(StaticMapOSMBuilder())
    text = service.build_text(_sample_enriched(), date(2026, 6, 19))

    assert "Route: 42.0 km" in text
    assert "google.com/maps/dir" in text
    assert "hotels: Hotel Alpha" in text
    assert "Visited before (2026-05-01)" in text
    assert "your rating: 5/5" in text
    assert "Note: Great day" in text
