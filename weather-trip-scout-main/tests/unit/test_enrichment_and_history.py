from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.clients.trip_history import TripHistoryClient
from app.domain.models import (
    Place,
    PlaceInfrastructure,
    PlaceScore,
    Point,
    RouteInfo,
    TripVisit,
)
from app.providers.geo.cache import OverpassCache
from app.services.enrichment_service import EnrichmentService


def _place_score(name: str = "Test Town") -> PlaceScore:
    return PlaceScore(
        place=Place(name, Point(48.1, 11.1), place_id="123"),
        final_score=80.0,
        best_time_start=time(10, 0),
        best_time_end=time(16, 0),
        summary="Good",
        breakdown={},
    )


class FakeRouteProvider:
    async def get_route_async(
        self, origin: Point, destination: Point
    ) -> RouteInfo | None:
        return RouteInfo(
            distance_km=10.0,
            duration_minutes=15,
            google_maps_url="https://maps.example/route",
        )


class FakeGeoProvider:
    async def get_place_infrastructure_async(
        self, place: Place, radius_m: float = 2000
    ) -> PlaceInfrastructure:
        return PlaceInfrastructure(hotels=["Hotel A"], cafes=["Cafe B"])


async def test_enrichment_service_combines_route_infra_and_history() -> None:
    trip_history = AsyncMock(spec=TripHistoryClient)
    trip_history.get_recent_visit = AsyncMock(
        return_value=TripVisit(
            place_id="123",
            place_name="Test Town",
            visit_date=date(2026, 5, 1),
            rating=4,
        )
    )

    service = EnrichmentService(
        geo_provider=FakeGeoProvider(),  # type: ignore[arg-type]
        route_provider=FakeRouteProvider(),  # type: ignore[arg-type]
        trip_history=trip_history,
    )
    home = Point(48.0, 11.0)
    result = await service.enrich_places(
        [_place_score()], home, date(2026, 6, 19), user_id="user1"
    )

    assert len(result) == 1
    item = result[0]
    assert item.route is not None
    assert item.route.distance_km == 10.0
    assert item.infrastructure is not None
    assert item.infrastructure.hotels == ["Hotel A"]
    assert item.previous_visit is not None
    assert item.previous_visit.rating == 4
    trip_history.get_recent_visit.assert_awaited_once_with(
        "user1", "123", before_date=date(2026, 6, 19)
    )


async def test_enrichment_service_skips_history_without_user_id() -> None:
    trip_history = AsyncMock(spec=TripHistoryClient)
    trip_history.get_recent_visit = AsyncMock()

    service = EnrichmentService(
        geo_provider=FakeGeoProvider(),  # type: ignore[arg-type]
        route_provider=FakeRouteProvider(),  # type: ignore[arg-type]
        trip_history=trip_history,
    )
    result = await service.enrich_places(
        [_place_score()], Point(48.0, 11.0), date(2026, 6, 19), user_id=None
    )

    assert result[0].previous_visit is None
    trip_history.get_recent_visit.assert_not_awaited()


def test_overpass_cache_set_and_get(tmp_path: Path) -> None:
    cache = OverpassCache(cache_dir=tmp_path)
    query = "[out:json]; node(1); out;"
    data = {"elements": [{"id": 1}]}

    assert cache.get(query) is None
    cache.set(query, data)
    assert cache.get(query) == data


def test_overpass_cache_expires_after_ttl(tmp_path: Path) -> None:
    cache = OverpassCache(cache_dir=tmp_path, ttl=timedelta(hours=1))
    query = "expired-query"
    cache.set(query, {"elements": []})

    key_path = cache._key_path(query)
    payload = __import__("json").loads(key_path.read_text(encoding="utf-8"))
    payload["created_at"] = (datetime.now(tz=UTC) - timedelta(hours=2)).isoformat()
    key_path.write_text(__import__("json").dumps(payload), encoding="utf-8")

    assert cache.get(query) is None


async def test_trip_history_client_disabled_when_url_empty() -> None:
    client = TripHistoryClient("")
    assert client.enabled is False

    with patch("httpx.AsyncClient") as mock_cls:
        await client.save_trip(
            user_id="u1",
            place_id="p1",
            place_name="Place",
            place_lat=48.0,
            place_lon=11.0,
            report_date=date(2026, 6, 19),
            score=80.0,
        )
        mock_cls.assert_not_called()


async def test_trip_history_client_save_trip_posts_payload() -> None:
    client = TripHistoryClient("http://history:8080")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_response)
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_http):
        await client.save_trip(
            user_id="u1",
            place_id="p1",
            place_name="Starnberg",
            place_lat=48.0,
            place_lon=11.0,
            report_date=date(2026, 6, 19),
            score=87.0,
            note="nice",
        )

    mock_http.post.assert_awaited_once()
    call = mock_http.post.await_args
    assert call.args[0] == "http://history:8080/api/trips"
    assert call.kwargs["json"]["placeName"] == "Starnberg"
    assert call.kwargs["json"]["note"] == "nice"


async def test_trip_history_client_get_recent_visit() -> None:
    client = TripHistoryClient("http://history:8080")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = [
        {
            "placeId": "123",
            "placeName": "Starnberg",
            "visitDate": "2026-05-01",
            "score": 85.0,
            "rating": 5,
            "note": "great",
        }
    ]

    mock_http = AsyncMock()
    mock_http.get = AsyncMock(return_value=mock_response)
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_http):
        visit = await client.get_recent_visit(
            "u1", "123", before_date=date(2026, 6, 19)
        )

    assert visit is not None
    assert visit.place_name == "Starnberg"
    assert visit.rating == 5
    params = mock_http.get.await_args.kwargs["params"]
    assert params["beforeDate"] == "2026-06-19"


async def test_trip_history_client_handles_http_error() -> None:
    client = TripHistoryClient("http://history:8080")
    mock_http = AsyncMock()
    mock_http.get = AsyncMock(side_effect=httpx.HTTPError("down"))
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_http):
        visit = await client.get_recent_visit("u1", "123")

    assert visit is None
