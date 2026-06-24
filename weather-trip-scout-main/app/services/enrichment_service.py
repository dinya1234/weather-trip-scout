import asyncio
from datetime import date

from app.clients.trip_history import TripHistoryClient
from app.domain.models import EnrichedPlaceScore, PlaceScore, Point, TripVisit
from app.providers.geo.base import GeoProvider
from app.providers.routing.base import RouteProvider


class EnrichmentService:
    """Adds route, infrastructure and trip history to ranked places."""

    def __init__(
        self,
        geo_provider: GeoProvider,
        route_provider: RouteProvider,
        trip_history: TripHistoryClient | None = None,
        infrastructure_radius_m: float = 2000,
    ) -> None:
        self.geo_provider = geo_provider
        self.route_provider = route_provider
        self.trip_history = trip_history
        self.infrastructure_radius_m = infrastructure_radius_m

    async def enrich_places(
        self,
        ranked: list[PlaceScore],
        home: Point,
        report_date: date,
        user_id: str | None = None,
    ) -> list[EnrichedPlaceScore]:
        tasks = [
            self._enrich_one(score, home, report_date, user_id) for score in ranked
        ]
        return list(await asyncio.gather(*tasks))

    async def _enrich_one(
        self,
        score: PlaceScore,
        home: Point,
        report_date: date,
        user_id: str | None,
    ) -> EnrichedPlaceScore:
        route_task = self.route_provider.get_route_async(home, score.place.point)
        infra_task = self.geo_provider.get_place_infrastructure_async(
            score.place, self.infrastructure_radius_m
        )
        history_task = self._fetch_history(user_id, score.place.place_id, report_date)

        route, infrastructure, previous_visit = await asyncio.gather(
            route_task, infra_task, history_task
        )
        return EnrichedPlaceScore(
            score=score,
            route=route,
            infrastructure=infrastructure,
            previous_visit=previous_visit,
        )

    async def _fetch_history(
        self, user_id: str | None, place_id: str | None, report_date: date
    ) -> TripVisit | None:
        if not user_id or not place_id or self.trip_history is None:
            return None
        return await self.trip_history.get_recent_visit(
            user_id, place_id, before_date=report_date
        )
