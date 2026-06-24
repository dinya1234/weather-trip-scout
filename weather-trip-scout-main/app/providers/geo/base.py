from typing import Protocol, runtime_checkable

from app.domain.models import Place, PlaceInfrastructure, Point


@runtime_checkable
class GeoProvider(Protocol):
    def get_candidate_places(
        self, center: Point, radius_km: float, mode: str
    ) -> list[Place]: ...

    def get_place_infrastructure(
        self, place: Place, radius_m: float = 2000
    ) -> PlaceInfrastructure: ...

    async def get_place_infrastructure_async(
        self, place: Place, radius_m: float = 2000
    ) -> PlaceInfrastructure: ...
