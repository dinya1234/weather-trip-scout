from datetime import date, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.config.loader import AppConfig
from app.config.settings import Settings
from app.core.exceptions import ConfigurationError
from app.domain.models import (
    EnrichedPlaceScore,
    HourlyForecastPoint,
    Place,
    PlaceScore,
    Point,
    ReportPayload,
)
from app.jobs.morning_report import MorningReportJob
from app.providers.geo.base import GeoProvider
from app.providers.maps.base import MapBuilder
from app.providers.weather.base import WeatherProvider


def _make_config() -> AppConfig:
    return AppConfig(
        home={"lat": 48.0, "lon": 11.0},
        search={
            "radius_km": 100,
            "top_n_places": 2,
            "min_acceptable_score": 0,
            "mode": "towns",
        },
        time={
            "send_at_local": "07:30",
            "analyze_from": "10:00",
            "analyze_to": "18:00",
        },
        weather_preferences={
            "min_temp_c": 14,
            "max_temp_c": 24,
            "max_wind_kmh": 18,
            "max_precip_mm_per_hour": 0.3,
            "max_precip_probability": 30,
            "max_cloud_cover": 70,
            "min_good_window_hours": 3,
        },
        scoring_weights={
            "precip": 35,
            "wind": 20,
            "temp": 20,
            "cloud": 10,
            "distance": 5,
            "good_window": 10,
        },
        providers={
            "weather_primary": "open_meteo",
            "weather_fallback": "open_weather",
            "geo": "overpass",
            "map": "staticmap_osm",
            "route": "osrm",
        },
    )


def _make_home() -> Point:
    return Point(48.0, 11.0)


def _make_place() -> Place:
    return Place("Test Town", Point(48.1, 11.1), place_id="123")


class FakeGeoProvider(GeoProvider):
    def get_candidate_places(
        self, center: Point, radius_km: float, mode: str
    ) -> list[Place]:
        return [_make_place()]

    def get_place_infrastructure(self, place: Place, radius_m: float = 2000) -> object:
        from app.domain.models import PlaceInfrastructure

        return PlaceInfrastructure()

    async def get_place_infrastructure_async(
        self, place: Place, radius_m: float = 2000
    ) -> object:
        return self.get_place_infrastructure(place, radius_m)


class FakeWeatherProvider(WeatherProvider):
    def get_hourly_forecast(
        self, point: Point, target_date: date
    ) -> list[HourlyForecastPoint]:
        return [
            HourlyForecastPoint(
                time=datetime(2026, 6, 15, h, 0),
                temp_c=20.0,
                wind_kmh=10.0,
                precip_mm=0.0,
                precip_probability=0.0,
                cloud_cover=20.0,
            )
            for h in range(10, 19)
        ]

    async def get_hourly_forecast_async(
        self, point: Point, target_date: date
    ) -> list[HourlyForecastPoint]:
        return self.get_hourly_forecast(point, target_date)


class FakeMapBuilder(MapBuilder):
    def build_map(
        self,
        ranked: list[PlaceScore],
        home: Point,
        radius_km: float,
    ) -> str | None:
        return None


class FakeCandidateService:
    def find_candidates(
        self,
        home: Point,
        radius_km: float,
        mode: str,
        max_candidates: int | None = None,
    ) -> list[Place]:
        return FakeGeoProvider().get_candidate_places(home, radius_km, mode)


class FakeForecastService:
    def get_forecast(
        self, place: Place, target_date: date
    ) -> list[HourlyForecastPoint]:
        return FakeWeatherProvider().get_hourly_forecast(place.point, target_date)

    async def get_forecast_async(
        self, place: Place, target_date: date
    ) -> list[HourlyForecastPoint]:
        return await FakeWeatherProvider().get_hourly_forecast_async(
            place.point, target_date
        )


class FakeEnrichmentService:
    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    async def enrich_places(
        self,
        ranked: list[PlaceScore],
        home: Point,
        report_date: date,
        user_id: str | None = None,
    ) -> list[EnrichedPlaceScore]:
        return [EnrichedPlaceScore(score=score) for score in ranked]


class FakeTelegramService:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.sent_text: str | None = None

    async def send_report(self, payload: ReportPayload) -> None:
        self.sent_text = payload.text


async def test_job_end_to_end() -> None:
    config = _make_config()
    settings = Settings.model_construct(
        telegram_bot_token="token",
        telegram_chat_id="123",
        open_weather_api_key=None,
        mapbox_token=None,
        trip_history_url=None,
    )

    job = MorningReportJob(settings, config)
    fake_telegram = FakeTelegramService("token", "123")

    with (
        patch(
            "app.jobs.morning_report.build_geo_provider",
            return_value=FakeGeoProvider(),
        ),
        patch(
            "app.jobs.morning_report.build_weather_provider",
            return_value=FakeWeatherProvider(),
        ),
        patch(
            "app.jobs.morning_report.build_map_builder",
            return_value=FakeMapBuilder(),
        ),
        patch(
            "app.jobs.morning_report.build_route_provider",
            return_value=AsyncMock(),
        ),
        patch(
            "app.jobs.morning_report.CandidateService",
            return_value=FakeCandidateService(),
        ),
        patch(
            "app.jobs.morning_report.ForecastService",
            return_value=FakeForecastService(),
        ),
        patch(
            "app.jobs.morning_report.EnrichmentService",
            FakeEnrichmentService,
        ),
        patch(
            "app.jobs.morning_report.TelegramService",
            return_value=fake_telegram,
        ),
    ):
        await job.run()

    assert fake_telegram.sent_text is not None
    assert "Weather trip scout for" in fake_telegram.sent_text
    assert "Test Town — score" in fake_telegram.sent_text


async def test_job_dry_run_does_not_send(capsys: object) -> None:
    config = _make_config()
    settings = Settings.model_construct(
        telegram_bot_token=None,
        telegram_chat_id=None,
        open_weather_api_key=None,
        mapbox_token=None,
        trip_history_url=None,
    )

    job = MorningReportJob(settings, config)

    with (
        patch(
            "app.jobs.morning_report.build_geo_provider",
            return_value=FakeGeoProvider(),
        ),
        patch(
            "app.jobs.morning_report.build_weather_provider",
            return_value=FakeWeatherProvider(),
        ),
        patch(
            "app.jobs.morning_report.build_map_builder",
            return_value=FakeMapBuilder(),
        ),
        patch(
            "app.jobs.morning_report.build_route_provider",
            return_value=AsyncMock(),
        ),
        patch(
            "app.jobs.morning_report.CandidateService",
            return_value=FakeCandidateService(),
        ),
        patch(
            "app.jobs.morning_report.ForecastService",
            return_value=FakeForecastService(),
        ),
        patch(
            "app.jobs.morning_report.EnrichmentService",
            FakeEnrichmentService,
        ),
        patch("app.jobs.morning_report.TelegramService") as telegram_cls,
    ):
        await job.run(dry_run=True)

    telegram_cls.assert_not_called()
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "Test Town — score" in out


async def test_job_raises_without_credentials() -> None:
    config = _make_config()
    settings = Settings.model_construct(
        telegram_bot_token=None,
        telegram_chat_id=None,
        open_weather_api_key=None,
        mapbox_token=None,
        trip_history_url=None,
    )

    job = MorningReportJob(settings, config)

    with (
        patch(
            "app.jobs.morning_report.build_geo_provider",
            return_value=FakeGeoProvider(),
        ),
        patch(
            "app.jobs.morning_report.build_weather_provider",
            return_value=FakeWeatherProvider(),
        ),
        patch(
            "app.jobs.morning_report.build_map_builder",
            return_value=FakeMapBuilder(),
        ),
        patch(
            "app.jobs.morning_report.build_route_provider",
            return_value=AsyncMock(),
        ),
        patch(
            "app.jobs.morning_report.CandidateService",
            return_value=FakeCandidateService(),
        ),
        patch(
            "app.jobs.morning_report.ForecastService",
            return_value=FakeForecastService(),
        ),
        patch(
            "app.jobs.morning_report.EnrichmentService",
            FakeEnrichmentService,
        ),
    ):
        with pytest.raises(ConfigurationError):
            await job.run()


async def test_job_skips_unavailable_fallback() -> None:
    config = _make_config()
    settings = Settings.model_construct(
        telegram_bot_token="token",
        telegram_chat_id="123",
        open_weather_api_key=None,
        mapbox_token=None,
        trip_history_url=None,
    )

    job = MorningReportJob(settings, config)
    fake_telegram = FakeTelegramService("token", "123")

    def _build_weather(name: str, _settings: Settings) -> WeatherProvider:
        if name == "open_weather":
            raise ConfigurationError("OPEN_WEATHER_API_KEY is required")
        return FakeWeatherProvider()

    with (
        patch(
            "app.jobs.morning_report.build_geo_provider",
            return_value=FakeGeoProvider(),
        ),
        patch(
            "app.jobs.morning_report.build_weather_provider",
            side_effect=_build_weather,
        ),
        patch(
            "app.jobs.morning_report.build_map_builder",
            return_value=FakeMapBuilder(),
        ),
        patch(
            "app.jobs.morning_report.build_route_provider",
            return_value=AsyncMock(),
        ),
        patch(
            "app.jobs.morning_report.CandidateService",
            return_value=FakeCandidateService(),
        ),
        patch(
            "app.jobs.morning_report.EnrichmentService",
            FakeEnrichmentService,
        ),
        patch(
            "app.jobs.morning_report.TelegramService",
            return_value=fake_telegram,
        ),
    ):
        await job.run()

    assert fake_telegram.sent_text is not None
