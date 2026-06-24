from datetime import date

from app.domain.models import EnrichedPlaceScore, Point, ReportPayload
from app.providers.maps.base import MapBuilder


class ReportService:
    def __init__(self, map_builder: MapBuilder) -> None:
        self.map_builder = map_builder

    def build_report(
        self,
        enriched: list[EnrichedPlaceScore],
        report_date: date,
        home: Point,
        radius_km: float,
    ) -> ReportPayload:
        ranked = [item.score for item in enriched]
        text = self.build_text(enriched, report_date)
        image_path = self.map_builder.build_map(ranked, home, radius_km)
        return ReportPayload(text=text, image_path=image_path)

    def build_text(self, enriched: list[EnrichedPlaceScore], report_date: date) -> str:
        header = f"🌤 Weather trip scout for {report_date.isoformat()}"
        if not enriched:
            return f"{header}\n\nNo good destinations today. Try again tomorrow!"

        lines = [header, "", f"Top {len(enriched)} destinations within radius:", ""]
        for i, item in enumerate(enriched, start=1):
            ps = item.score
            lines.append(f"{i}. {ps.place.name} — score {ps.final_score:.0f}")
            lines.append(f"   Best window: {ps.best_time_start}–{ps.best_time_end}")
            lines.append(f"   {ps.summary}")

            if item.route is not None:
                lines.append(
                    f"   Route: {item.route.distance_km} km, "
                    f"~{item.route.duration_minutes} min"
                )
                lines.append(f"   Maps: {item.route.google_maps_url}")

            if item.infrastructure is not None:
                infra_lines = self._format_infrastructure(item.infrastructure)
                lines.extend(infra_lines)

            if item.previous_visit is not None:
                visit = item.previous_visit
                visit_line = f"   Visited before ({visit.visit_date.isoformat()})"
                if visit.rating is not None:
                    visit_line += f", your rating: {visit.rating}/5"
                lines.append(visit_line)
                if visit.note:
                    lines.append(f"   Note: {visit.note}")

        return "\n".join(lines)

    @staticmethod
    def _format_infrastructure(infra: object) -> list[str]:
        from app.domain.models import PlaceInfrastructure

        if not isinstance(infra, PlaceInfrastructure):
            return []

        parts: list[str] = []
        if infra.hotels:
            parts.append(f"hotels: {', '.join(infra.hotels)}")
        if infra.cafes:
            parts.append(f"cafes: {', '.join(infra.cafes)}")
        if infra.attractions:
            parts.append(f"sights: {', '.join(infra.attractions)}")
        if not parts:
            return []
        return [f"   Nearby: {'; '.join(parts)}"]
