from typing import Protocol, runtime_checkable

from app.domain.models import Point, RouteInfo


@runtime_checkable
class RouteProvider(Protocol):
    def get_route(self, origin: Point, destination: Point) -> RouteInfo | None: ...

    async def get_route_async(
        self, origin: Point, destination: Point
    ) -> RouteInfo | None: ...
