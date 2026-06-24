import logging
from datetime import date
from typing import Any

import httpx

from app.domain.models import TripVisit

logger = logging.getLogger(__name__)


class TripHistoryClient:
    """REST client for the Java trip-history microservice."""

    def __init__(self, base_url: str, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    async def save_trip(
        self,
        user_id: str,
        place_id: str,
        place_name: str,
        place_lat: float,
        place_lon: float,
        report_date: date,
        score: float,
        note: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        payload = {
            "userId": user_id,
            "placeId": place_id,
            "placeName": place_name,
            "placeLat": place_lat,
            "placeLon": place_lon,
            "reportDate": report_date.isoformat(),
            "score": score,
            "note": note,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/trips", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Failed to save trip to history service: %s", exc)

    async def get_recent_visit(
        self, user_id: str, place_id: str, before_date: date | None = None
    ) -> TripVisit | None:
        if not self.enabled:
            return None
        params: dict[str, str | int] = {
            "userId": user_id,
            "placeId": place_id,
            "limit": 1,
        }
        if before_date is not None:
            params["beforeDate"] = before_date.isoformat()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/trips/recent",
                    params=params,
                )
                response.raise_for_status()
                items = response.json()
        except httpx.HTTPError as exc:
            logger.warning("Failed to fetch trip history: %s", exc)
            return None

        if not isinstance(items, list) or not items:
            return None
        return self._parse_visit(items[0])

    @staticmethod
    def _parse_visit(item: dict[str, Any]) -> TripVisit | None:
        try:
            return TripVisit(
                place_id=str(item["placeId"]),
                place_name=str(item["placeName"]),
                visit_date=date.fromisoformat(str(item["visitDate"])),
                score=float(item["score"]) if item.get("score") is not None else None,
                rating=int(item["rating"]) if item.get("rating") is not None else None,
                note=str(item["note"]) if item.get("note") else None,
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Invalid trip history item: %s", exc)
            return None
