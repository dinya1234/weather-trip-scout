from datetime import date, datetime

from app.domain.models import HourlyForecastPoint, Place, Point
from app.providers.weather.open_meteo import OpenMeteoProvider
from app.providers.weather.open_weather import OpenWeatherProvider
from app.services.forecast_service import ForecastService


def _forecast() -> list[HourlyForecastPoint]:

    return [
        HourlyForecastPoint(
            time=datetime(2026, 6, 19, 12, 0),
            temp_c=20.0,
            wind_kmh=10.0,
            precip_mm=0.0,
            precip_probability=0.0,
            cloud_cover=20.0,
        )
    ]


class FailingPrimary(OpenMeteoProvider):
    async def get_hourly_forecast_async(
        self, point: Point, target_date: date
    ) -> list[HourlyForecastPoint]:
        raise RuntimeError("primary down")


class AsyncFallback(OpenWeatherProvider):
    def __init__(self) -> None:
        self.api_key = "dummy"

    async def get_hourly_forecast_async(
        self, point: Point, target_date: date
    ) -> list[HourlyForecastPoint]:
        return _forecast()


async def test_forecast_service_uses_async_fallback() -> None:
    service = ForecastService(FailingPrimary(), AsyncFallback())  # type: ignore[arg-type]
    place = Place("Town", Point(48.0, 11.0))
    result = await service.get_forecast_async(place, date(2026, 6, 19))
    assert len(result) == 1
    assert result[0].temp_c == 20.0
