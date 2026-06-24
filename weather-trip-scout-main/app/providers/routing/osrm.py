import logging
from typing import cast
from urllib.parse import quote

import httpx

from app.core.exceptions import ProviderError
from app.domain.models import Point, RouteInfo

logger = logging.getLogger(__name__)


class OsrmRouteProvider:
    """Free OSRM routing API — distance and duration between two points."""

    BASE_URL = "https://router.project-osrm.org/route/v1/driving"
    USER_AGENT = (
        "weather-trip-scout/0.1 (+https://github.com/Shugar86/weather-trip-scout)"
    )

    def get_route(self, origin: Point, destination: Point) -> RouteInfo | None:
        try:
            with httpx.Client(
                timeout=30.0, headers={"User-Agent": self.USER_AGENT}
            ) as client:
                return self._parse_response(
                    self._fetch(client, origin, destination),
                    origin,
                    destination,
                )
        except (httpx.HTTPError, ProviderError) as exc:
            logger.warning("OSRM route request failed: %s", exc)
            return None

    async def get_route_async(
        self, origin: Point, destination: Point
    ) -> RouteInfo | None:
        try:
            async with httpx.AsyncClient(
                timeout=30.0, headers={"User-Agent": self.USER_AGENT}
            ) as client:
                return self._parse_response(
                    await self._fetch_async(client, origin, destination),
                    origin,
                    destination,
                )
        except (httpx.HTTPError, ProviderError) as exc:
            logger.warning("OSRM route request failed: %s", exc)
            return None

    def _url(self, origin: Point, destination: Point) -> str:
        coords = f"{origin.lon},{origin.lat};{destination.lon},{destination.lat}"
        return f"{self.BASE_URL}/{coords}?overview=false"

    def _fetch(
        self, client: httpx.Client, origin: Point, destination: Point
    ) -> dict[str, object]:
        response = client.get(self._url(origin, destination))
        response.raise_for_status()
        return cast(dict[str, object], response.json())

    async def _fetch_async(
        self, client: httpx.AsyncClient, origin: Point, destination: Point
    ) -> dict[str, object]:
        response = await client.get(self._url(origin, destination))
        response.raise_for_status()
        return cast(dict[str, object], response.json())

    def _parse_response(
        self,
        data: dict[str, object],
        origin: Point,
        destination: Point,
    ) -> RouteInfo | None:
        if data.get("code") != "Ok":
            raise ProviderError(f"OSRM returned code: {data.get('code')!r}")

        routes = data.get("routes")
        if not isinstance(routes, list) or not routes:
            return None

        route = routes[0]
        if not isinstance(route, dict):
            return None

        distance_m = float(route.get("distance", 0))
        duration_s = float(route.get("duration", 0))
        google_url = self._google_maps_url(origin, destination)

        return RouteInfo(
            distance_km=round(distance_m / 1000, 1),
            duration_minutes=max(1, round(duration_s / 60)),
            google_maps_url=google_url,
        )

    @staticmethod
    def _google_maps_url(origin: Point, destination: Point) -> str:
        origin_str = f"{origin.lat},{origin.lon}"
        dest_str = f"{destination.lat},{destination.lon}"
        return (
            "https://www.google.com/maps/dir/?api=1"
            f"&origin={quote(origin_str)}"
            f"&destination={quote(dest_str)}"
        )
