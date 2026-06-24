import logging
from datetime import UTC, date, datetime
from typing import Any, cast

import httpx

from app.core.exceptions import ConfigurationError, ProviderError
from app.domain.models import HourlyForecastPoint, Point

logger = logging.getLogger(__name__)


def _precip_mm(value: Any) -> float:
    return float(value.get("1h", 0)) if isinstance(value, dict) else 0.0


class OpenWeatherProvider:
    """Fallback weather provider; requires an API key."""

    BASE_URL = "https://api.openweathermap.org/data/3.0/onecall"

    def __init__(self, api_key: str | None) -> None:
        if not api_key:
            raise ConfigurationError(
                "OPEN_WEATHER_API_KEY is required for OpenWeatherProvider"
            )
        self.api_key = api_key

    def get_hourly_forecast(
        self, point: Point, target_date: date
    ) -> list[HourlyForecastPoint]:
        with httpx.Client(timeout=30.0) as client:
            data = self._fetch(client, point)
        return self._parse(data, target_date)

    async def get_hourly_forecast_async(
        self, point: Point, target_date: date
    ) -> list[HourlyForecastPoint]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            data = await self._fetch_async(client, point)
        return self._parse(data, target_date)

    def _params(self, point: Point) -> dict[str, Any]:
        return {
            "lat": point.lat,
            "lon": point.lon,
            "appid": self.api_key,
            "units": "metric",
            "exclude": "current,minutely,daily,alerts",
        }

    def _fetch(self, client: httpx.Client, point: Point) -> dict[str, Any]:
        try:
            response = client.get(self.BASE_URL, params=self._params(point))
            response.raise_for_status()
            return cast(dict[str, Any], response.json())
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"OpenWeather request failed: {exc}") from exc

    async def _fetch_async(
        self, client: httpx.AsyncClient, point: Point
    ) -> dict[str, Any]:
        try:
            response = await client.get(self.BASE_URL, params=self._params(point))
            response.raise_for_status()
            return cast(dict[str, Any], response.json())
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"OpenWeather request failed: {exc}") from exc

    def _parse(
        self, data: dict[str, Any], target_date: date
    ) -> list[HourlyForecastPoint]:
        hourly = data.get("hourly", [])
        if not isinstance(hourly, list):
            raise ProviderError("OpenWeather response missing valid hourly data")

        points: list[HourlyForecastPoint] = []
        for h in hourly:
            if not isinstance(h, dict):
                raise ProviderError("OpenWeather hourly item is not an object")
            for required_key in ("dt", "temp", "wind_speed"):
                if required_key not in h:
                    raise ProviderError(
                        f"OpenWeather hourly item missing required key: {required_key}"
                    )

            time = datetime.fromtimestamp(h["dt"], tz=UTC)
            if time.date() != target_date:
                continue

            try:
                points.append(
                    HourlyForecastPoint(
                        time=time,
                        temp_c=float(h["temp"]),
                        wind_kmh=float(h["wind_speed"]) * 3.6,
                        precip_mm=_precip_mm(h.get("rain")) + _precip_mm(h.get("snow")),
                        precip_probability=float(h["pop"]) * 100
                        if "pop" in h
                        else None,
                        cloud_cover=float(h.get("clouds", 0)),
                    )
                )
            except (AttributeError, TypeError, ValueError) as exc:
                raise ProviderError(
                    f"OpenWeather response parsing failed: {exc}"
                ) from exc

        return points
