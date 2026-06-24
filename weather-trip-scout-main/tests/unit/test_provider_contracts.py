from datetime import UTC, date, datetime
from json import JSONDecodeError
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import ConfigurationError, ProviderError
from app.domain.models import Place, PlaceScore, Point
from app.providers.geo.base import GeoProvider
from app.providers.geo.cache import OverpassCache
from app.providers.geo.overpass import OverpassProvider
from app.providers.maps.base import MapBuilder
from app.providers.maps.mapbox import MapboxBuilder
from app.providers.maps.staticmap_osm import StaticMapOSMBuilder
from app.providers.routing.base import RouteProvider
from app.providers.routing.osrm import OsrmRouteProvider
from app.providers.weather.base import WeatherProvider
from app.providers.weather.open_meteo import OpenMeteoProvider
from app.providers.weather.open_weather import OpenWeatherProvider

OPEN_METEO_CLIENT = "app.providers.weather.open_meteo.httpx.Client"


def _mock_httpx_client(method: str, response_data: object) -> MagicMock:
    mock_response = MagicMock()
    mock_response.json.return_value = response_data
    mock_response.raise_for_status = MagicMock()
    mock_response.content = b"pngdata"

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    getattr(mock_client, method).return_value = mock_response
    return mock_client


def test_open_meteo_is_weather_provider() -> None:
    provider = OpenMeteoProvider()
    assert isinstance(provider, WeatherProvider)


def test_open_weather_requires_key() -> None:
    with pytest.raises(ConfigurationError):
        OpenWeatherProvider(api_key=None)


def test_open_weather_accepts_key() -> None:
    provider = OpenWeatherProvider(api_key="dummy")
    assert provider.api_key == "dummy"


def test_open_meteo_get_hourly_forecast_mocked() -> None:
    provider = OpenMeteoProvider()
    target = date(2024, 6, 1)
    response = {
        "hourly": {
            "time": [
                "2024-06-01T00:00",
                "2024-06-01T01:00",
                "2024-06-01T02:00",
            ],
            "temperature_2m": [15.0, 16.0, 17.0],
            "windspeed_10m": [5.0, 6.0, 7.0],
            "precipitation": [0.0, 0.1, 0.0],
            "precipitation_probability": [10, 20, 30],
            "cloudcover": [20, 25, 30],
        }
    }
    mock_client = _mock_httpx_client("get", response)
    with patch(OPEN_METEO_CLIENT, return_value=mock_client):
        forecast = provider.get_hourly_forecast(Point(lat=48.0, lon=11.0), target)

    assert len(forecast) == 3
    assert forecast[0].temp_c == 15.0
    assert forecast[0].wind_kmh == 5.0
    assert forecast[0].precip_mm == 0.0
    assert forecast[0].precip_probability == 10.0
    assert forecast[0].cloud_cover == 20.0
    assert forecast[0].time == datetime(2024, 6, 1, 0, 0, tzinfo=UTC)


def test_open_weather_get_hourly_forecast_mocked() -> None:
    provider = OpenWeatherProvider(api_key="dummy")
    target = date(2024, 6, 1)
    response = {
        "hourly": [
            {
                "dt": 1717200000,
                "temp": 15.0,
                "wind_speed": 2.0,
                "pop": 0.1,
                "clouds": 20,
            },
            {
                "dt": 1717286400,
                "temp": 16.0,
                "wind_speed": 3.0,
            },
        ]
    }
    mock_client = _mock_httpx_client("get", response)
    with patch(
        "app.providers.weather.open_weather.httpx.Client", return_value=mock_client
    ):
        forecast = provider.get_hourly_forecast(Point(lat=48.0, lon=11.0), target)

    assert len(forecast) == 1
    assert forecast[0].temp_c == 15.0
    assert forecast[0].time.date() == target


def test_provider_raises_provider_error_on_http_error() -> None:
    provider = OpenMeteoProvider()
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.get.side_effect = httpx.HTTPError("boom")
    with patch(OPEN_METEO_CLIENT, return_value=mock_client):
        with pytest.raises(ProviderError):
            provider.get_hourly_forecast(Point(lat=48.0, lon=11.0), date(2024, 6, 1))


def test_overpass_is_geo_provider() -> None:
    provider = OverpassProvider()
    assert isinstance(provider, GeoProvider)


def test_overpass_get_candidate_places_mocked(tmp_path) -> None:
    provider = OverpassProvider(cache=OverpassCache(cache_dir=tmp_path))
    response = {
        "elements": [
            {
                "id": 123,
                "lat": 48.0,
                "lon": 11.0,
                "tags": {"name": "Test Town", "place": "town"},
            },
            {
                "id": 124,
                "lat": 48.1,
                "lon": 11.1,
                "tags": {"name:en": "No Name Peak", "natural": "peak"},
            },
            {
                "id": 125,
                "lat": 48.2,
                "lon": 11.2,
                "tags": {"place": "village"},
            },
        ]
    }
    mock_client = _mock_httpx_client("post", response)
    with patch("app.providers.geo.overpass.httpx.Client", return_value=mock_client):
        towns = provider.get_candidate_places(Point(lat=48.0, lon=11.0), 10.0, "towns")
        nature = provider.get_candidate_places(Point(lat=48.0, lon=11.0), 5.0, "nature")

    assert len(towns) == 2
    assert towns[0].name == "Test Town"
    assert towns[0].place_id == "123"
    assert towns[1].name == "No Name Peak"
    assert isinstance(nature, list)


def test_overpass_infrastructure_mocked(tmp_path) -> None:
    provider = OverpassProvider(cache=OverpassCache(cache_dir=tmp_path))
    response = {
        "elements": [
            {
                "id": 1,
                "lat": 48.0,
                "lon": 11.0,
                "tags": {"name": "Hotel Alpha", "tourism": "hotel"},
            },
            {
                "id": 2,
                "lat": 48.0,
                "lon": 11.0,
                "tags": {"name": "Cafe Beta", "amenity": "cafe"},
            },
        ]
    }
    mock_client = _mock_httpx_client("post", response)
    with patch("app.providers.geo.overpass.httpx.Client", return_value=mock_client):
        infra = provider.get_place_infrastructure(
            Place("Test Town", Point(48.0, 11.0)), radius_m=1000
        )

    assert infra.hotels == ["Hotel Alpha"]
    assert infra.cafes == ["Cafe Beta"]


def test_overpass_query_contains_radius_center_and_tags(tmp_path) -> None:
    provider = OverpassProvider(cache=OverpassCache(cache_dir=tmp_path))
    response = {
        "elements": [
            {
                "id": 1,
                "lat": 48.0,
                "lon": 11.0,
                "tags": {"name": "Test"},
            }
        ]
    }
    mock_client = _mock_httpx_client("post", response)
    with patch(
        "app.providers.geo.overpass.httpx.Client", return_value=mock_client
    ) as mock_cls:
        provider.get_candidate_places(Point(lat=48.0, lon=11.0), 10.0, "towns")

    mock_client.post.assert_called_once()
    query = mock_client.post.call_args.kwargs["data"]["data"]
    assert "around:10000,48.0,11.0" in query
    assert "place~'town|city|village'" in query
    mock_cls.assert_called_once()


def test_overpass_request_uses_identity_accept_encoding(tmp_path) -> None:
    provider = OverpassProvider(cache=OverpassCache(cache_dir=tmp_path))
    mock_client = _mock_httpx_client("post", {"elements": []})
    with patch("app.providers.geo.overpass.httpx.Client", return_value=mock_client):
        provider.get_candidate_places(Point(lat=48.0, lon=11.0), 1.0, "towns")

    headers = mock_client.post.call_args.kwargs["headers"]
    assert headers["Accept-Encoding"] == "identity"
    assert "weather-trip-scout" in headers["User-Agent"]


def test_overpass_unknown_mode_defaults_to_towns(tmp_path) -> None:
    provider = OverpassProvider(cache=OverpassCache(cache_dir=tmp_path))
    mock_client = _mock_httpx_client("post", {"elements": []})
    with patch("app.providers.geo.overpass.httpx.Client", return_value=mock_client):
        provider.get_candidate_places(Point(lat=48.0, lon=11.0), 1.0, "unknown")

    query = mock_client.post.call_args.kwargs["data"]["data"]
    assert "place~'town|city|village'" in query


def test_overpass_request_exception_converted_to_provider_error(tmp_path) -> None:
    provider = OverpassProvider(cache=OverpassCache(cache_dir=tmp_path))
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.side_effect = httpx.HTTPError("network error")
    with patch("app.providers.geo.overpass.httpx.Client", return_value=mock_client):
        with pytest.raises(ProviderError):
            provider.get_candidate_places(Point(lat=48.0, lon=11.0), 1.0, "towns")


def test_overpass_json_decode_error_converted_to_provider_error(tmp_path) -> None:
    provider = OverpassProvider(cache=OverpassCache(cache_dir=tmp_path))
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("not json")
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.return_value = mock_response
    with patch("app.providers.geo.overpass.httpx.Client", return_value=mock_client):
        with pytest.raises(ProviderError):
            provider.get_candidate_places(Point(lat=48.0, lon=11.0), 1.0, "towns")


def test_overpass_zero_radius_raises_provider_error() -> None:
    provider = OverpassProvider()
    with pytest.raises(ProviderError):
        provider.get_candidate_places(Point(lat=48.0, lon=11.0), 0.0, "towns")


def test_overpass_cache_hit_skips_http(tmp_path) -> None:
    cache = OverpassCache(cache_dir=tmp_path)
    query = "test-query"
    cache.set(query, {"elements": []})

    provider = OverpassProvider(cache=cache)
    with patch("app.providers.geo.overpass.httpx.Client") as mock_client_cls:
        data = provider._execute_query(query)

    assert data == {"elements": []}
    mock_client_cls.assert_not_called()


def test_open_meteo_json_decode_error_converted_to_provider_error() -> None:
    provider = OpenMeteoProvider()
    mock_response = MagicMock()
    mock_response.json.side_effect = JSONDecodeError("decode error", "doc", 0)
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.get.return_value = mock_response
    with patch(OPEN_METEO_CLIENT, return_value=mock_client):
        with pytest.raises(ProviderError):
            provider.get_hourly_forecast(Point(lat=48.0, lon=11.0), date(2024, 6, 1))


def test_open_weather_json_decode_error_converted_to_provider_error() -> None:
    provider = OpenWeatherProvider(api_key="dummy")
    mock_response = MagicMock()
    mock_response.json.side_effect = JSONDecodeError("decode error", "doc", 0)
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.get.return_value = mock_response
    with patch(
        "app.providers.weather.open_weather.httpx.Client", return_value=mock_client
    ):
        with pytest.raises(ProviderError):
            provider.get_hourly_forecast(Point(lat=48.0, lon=11.0), date(2024, 6, 1))


def test_open_meteo_missing_required_key_raises_provider_error() -> None:
    provider = OpenMeteoProvider()
    mock_client = _mock_httpx_client("get", {"hourly": {"time": ["2024-06-01T00:00"]}})
    with patch(OPEN_METEO_CLIENT, return_value=mock_client):
        with pytest.raises(ProviderError):
            provider.get_hourly_forecast(Point(lat=48.0, lon=11.0), date(2024, 6, 1))


def test_open_weather_missing_required_key_raises_provider_error() -> None:
    provider = OpenWeatherProvider(api_key="dummy")
    mock_client = _mock_httpx_client(
        "get", {"hourly": [{"dt": 1717200000, "temp": 15.0}]}
    )
    with patch(
        "app.providers.weather.open_weather.httpx.Client", return_value=mock_client
    ):
        with pytest.raises(ProviderError):
            provider.get_hourly_forecast(Point(lat=48.0, lon=11.0), date(2024, 6, 1))


def test_open_meteo_array_length_mismatch_raises_provider_error() -> None:
    provider = OpenMeteoProvider()
    response = {
        "hourly": {
            "time": ["2024-06-01T00:00", "2024-06-01T01:00"],
            "temperature_2m": [15.0],
            "windspeed_10m": [5.0, 6.0],
            "precipitation": [0.0, 0.0],
            "precipitation_probability": [0, 0],
            "cloudcover": [0, 0],
        }
    }
    mock_client = _mock_httpx_client("get", response)
    with patch(OPEN_METEO_CLIENT, return_value=mock_client):
        with pytest.raises(ProviderError):
            provider.get_hourly_forecast(Point(lat=48.0, lon=11.0), date(2024, 6, 1))


def test_open_meteo_request_params() -> None:
    provider = OpenMeteoProvider()
    target = date(2024, 6, 1)
    response = {
        "hourly": {
            "time": ["2024-06-01T00:00"],
            "temperature_2m": [15.0],
            "windspeed_10m": [5.0],
            "precipitation": [0.0],
            "precipitation_probability": [10],
            "cloudcover": [20],
        }
    }
    mock_client = _mock_httpx_client("get", response)
    with patch(OPEN_METEO_CLIENT, return_value=mock_client) as mock_cls:
        provider.get_hourly_forecast(Point(lat=48.0, lon=11.0), target)

    params = mock_client.get.call_args.kwargs["params"]
    assert params["latitude"] == 48.0
    assert params["longitude"] == 11.0
    assert params["start_date"] == "2024-06-01"
    assert params["end_date"] == "2024-06-01"
    assert params["timezone"] == "UTC"
    assert "temperature_2m" in params["hourly"]
    mock_cls.assert_called_once()


def test_open_weather_request_params() -> None:
    provider = OpenWeatherProvider(api_key="dummy")
    target = date(2024, 6, 1)
    response = {
        "hourly": [
            {
                "dt": 1717200000,
                "temp": 15.0,
                "wind_speed": 2.0,
            }
        ]
    }
    mock_client = _mock_httpx_client("get", response)
    with patch(
        "app.providers.weather.open_weather.httpx.Client", return_value=mock_client
    ):
        provider.get_hourly_forecast(Point(lat=48.0, lon=11.0), target)

    params = mock_client.get.call_args.kwargs["params"]
    assert params["lat"] == 48.0
    assert params["lon"] == 11.0
    assert params["appid"] == "dummy"
    assert params["units"] == "metric"
    assert "current,minutely,daily,alerts" in params["exclude"]


def test_osrm_is_route_provider() -> None:
    provider = OsrmRouteProvider()
    assert isinstance(provider, RouteProvider)


def test_osrm_get_route_mocked() -> None:
    provider = OsrmRouteProvider()
    response = {
        "code": "Ok",
        "routes": [{"distance": 42000, "duration": 2700}],
    }
    mock_client = _mock_httpx_client("get", response)
    with patch("app.providers.routing.osrm.httpx.Client", return_value=mock_client):
        route = provider.get_route(Point(48.0, 11.0), Point(48.1, 11.1))

    assert route is not None
    assert route.distance_km == 42.0
    assert route.duration_minutes == 45
    assert "google.com/maps/dir" in route.google_maps_url


async def test_osrm_get_route_async_mocked() -> None:
    provider = OsrmRouteProvider()
    response = {
        "code": "Ok",
        "routes": [{"distance": 1000, "duration": 120}],
    }
    mock_response = MagicMock()
    mock_response.json.return_value = response
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch(
        "app.providers.routing.osrm.httpx.AsyncClient", return_value=mock_client
    ):
        route = await provider.get_route_async(Point(48.0, 11.0), Point(48.1, 11.1))

    assert route is not None
    assert route.distance_km == 1.0
    assert route.duration_minutes == 2


def test_staticmap_osm_is_map_builder() -> None:
    builder = StaticMapOSMBuilder()
    assert isinstance(builder, MapBuilder)


def test_mapbox_requires_token() -> None:
    with pytest.raises(ConfigurationError):
        MapboxBuilder(token=None)


def _sample_ranked() -> list[PlaceScore]:
    from datetime import time

    return [
        PlaceScore(
            place=Place(name="Test Spot", point=Point(lat=48.0, lon=11.0)),
            final_score=75.0,
            best_time_start=time(8, 0),
            best_time_end=time(14, 0),
            summary="Nice",
            breakdown={},
        )
    ]


def test_staticmap_osm_build_map_returns_path() -> None:
    fake_image = MagicMock()
    mock_map = MagicMock()
    mock_map.return_value.render.return_value = fake_image
    with patch("app.providers.maps.staticmap_osm.StaticMap", mock_map):
        result = StaticMapOSMBuilder().build_map(
            _sample_ranked(), Point(lat=48.0, lon=11.0), 10.0
        )
    assert result is not None
    assert result.endswith(".png")
    fake_image.save.assert_called_once_with(result)


def test_staticmap_osm_build_map_empty_ranked_returns_none() -> None:
    assert StaticMapOSMBuilder().build_map([], Point(lat=48.0, lon=11.0), 10.0) is None


def test_staticmap_osm_build_map_render_error_returns_none() -> None:
    mock_map = MagicMock()
    mock_map.return_value.render.side_effect = OSError("render failed")
    with patch("app.providers.maps.staticmap_osm.StaticMap", mock_map):
        result = StaticMapOSMBuilder().build_map(
            _sample_ranked(), Point(lat=48.0, lon=11.0), 10.0
        )
    assert result is None


def test_mapbox_build_map_returns_path() -> None:
    mock_client = _mock_httpx_client("get", {})
    with patch("app.providers.maps.mapbox.httpx.Client", return_value=mock_client):
        result = MapboxBuilder(token="dummy").build_map(
            _sample_ranked(), Point(lat=48.0, lon=11.0), 10.0
        )
    assert result is not None
    assert result.endswith(".png")
    mock_client.get.assert_called_once()


def test_mapbox_build_map_request_error_returns_none() -> None:
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.get.side_effect = httpx.HTTPError("boom")
    with patch("app.providers.maps.mapbox.httpx.Client", return_value=mock_client):
        result = MapboxBuilder(token="dummy").build_map(
            _sample_ranked(), Point(lat=48.0, lon=11.0), 10.0
        )
    assert result is None


def test_mapbox_build_map_empty_ranked_returns_none() -> None:
    assert (
        MapboxBuilder(token="dummy").build_map([], Point(lat=48.0, lon=11.0), 10.0)
        is None
    )
