import logging
from typing import Any, cast

import httpx

from app.core.exceptions import ProviderError
from app.domain.models import Place, PlaceInfrastructure, Point
from app.providers.geo.cache import OverpassCache

logger = logging.getLogger(__name__)


class OverpassProvider:
    """OSM-based candidate places and local infrastructure via Overpass API."""

    BASE_URL = "https://overpass-api.de/api/interpreter"
    USER_AGENT = (
        "weather-trip-scout/0.1 (+https://github.com/Shugar86/weather-trip-scout)"
    )
    MAX_INFRA_NAMES = 3

    def __init__(self, cache: OverpassCache | None = None) -> None:
        self.cache = cache or OverpassCache()

    def get_candidate_places(
        self, center: Point, radius_km: float, mode: str
    ) -> list[Place]:
        if radius_km <= 0:
            raise ProviderError("radius_km must be greater than 0")

        tag = self._tag_for_mode(mode)
        query = f"""
        [out:json][timeout:25];
        (
          node[{tag}](around:{radius_km * 1000:.0f},{center.lat},{center.lon});
        );
        out body;
        """
        data = self._execute_query(query)
        return self._parse_places(data)

    def get_place_infrastructure(
        self, place: Place, radius_m: float = 2000
    ) -> PlaceInfrastructure:
        query = self._infrastructure_query(place, radius_m)
        data = self._execute_query(query)
        return self._parse_infrastructure(data)

    async def get_place_infrastructure_async(
        self, place: Place, radius_m: float = 2000
    ) -> PlaceInfrastructure:
        query = self._infrastructure_query(place, radius_m)
        data = await self._execute_query_async(query)
        return self._parse_infrastructure(data)

    def _execute_query(self, query: str) -> dict[str, Any]:
        cached = self.cache.get(query)
        if cached is not None:
            return cached

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.BASE_URL,
                    data={"data": query},
                    headers={
                        "Accept-Encoding": "identity",
                        "User-Agent": self.USER_AGENT,
                    },
                )
                response.raise_for_status()
                data = cast(dict[str, Any], response.json())
        except httpx.HTTPError as exc:
            raise ProviderError(f"Overpass request failed: {exc}") from exc
        except ValueError as exc:
            raise ProviderError(f"Overpass response is not valid JSON: {exc}") from exc

        if isinstance(data, dict):
            self.cache.set(query, data)
        return data

    async def _execute_query_async(self, query: str) -> dict[str, Any]:
        cached = self.cache.get(query)
        if cached is not None:
            return cached

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.BASE_URL,
                    data={"data": query},
                    headers={
                        "Accept-Encoding": "identity",
                        "User-Agent": self.USER_AGENT,
                    },
                )
                response.raise_for_status()
                data = cast(dict[str, Any], response.json())
        except httpx.HTTPError as exc:
            raise ProviderError(f"Overpass request failed: {exc}") from exc
        except ValueError as exc:
            raise ProviderError(f"Overpass response is not valid JSON: {exc}") from exc

        if isinstance(data, dict):
            self.cache.set(query, data)
        return data

    def _infrastructure_query(self, place: Place, radius_m: float) -> str:
        lat = place.point.lat
        lon = place.point.lon
        return f"""
        [out:json][timeout:25];
        (
          node["tourism"~"hotel|hostel|guest_house|attraction|museum"](around:{radius_m:.0f},{lat},{lon});
          node["amenity"~"cafe|restaurant|fast_food"](around:{radius_m:.0f},{lat},{lon});
        );
        out body;
        """

    def _parse_places(self, data: dict[str, Any]) -> list[Place]:
        elements = data.get("elements", [])
        places: list[Place] = []
        for el in elements:
            lat = el.get("lat")
            lon = el.get("lon")
            if lat is None or lon is None:
                continue
            tags = el.get("tags", {})
            name = tags.get("name") or tags.get("name:en")
            if not name:
                continue
            places.append(
                Place(
                    name=name,
                    point=Point(lat=lat, lon=lon),
                    place_id=str(el.get("id")),
                    tags=tags,
                )
            )
        return places

    def _parse_infrastructure(self, data: dict[str, Any]) -> PlaceInfrastructure:
        hotels: list[str] = []
        cafes: list[str] = []
        attractions: list[str] = []

        for el in data.get("elements", []):
            tags = el.get("tags", {})
            name = tags.get("name") or tags.get("name:en")
            if not name:
                continue

            tourism = tags.get("tourism", "")
            amenity = tags.get("amenity", "")

            if (
                tourism in {"hotel", "hostel", "guest_house"}
                and len(hotels) < self.MAX_INFRA_NAMES
            ):
                hotels.append(name)
            elif (
                amenity in {"cafe", "restaurant", "fast_food"}
                and len(cafes) < self.MAX_INFRA_NAMES
            ):
                cafes.append(name)
            elif (
                tourism in {"attraction", "museum", "viewpoint"}
                and len(attractions) < self.MAX_INFRA_NAMES
            ):
                attractions.append(name)

        return PlaceInfrastructure(hotels=hotels, cafes=cafes, attractions=attractions)

    def _tag_for_mode(self, mode: str) -> str:
        if mode == "towns":
            return "place~'town|city|village'"
        if mode == "nature":
            return "tourism~'viewpoint|picnic_site'|natural~'peak|lake|forest'"
        return "place~'town|city|village'"
