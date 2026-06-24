import asyncio
import logging
import os
from datetime import date

from app.clients.trip_history import TripHistoryClient
from app.config.loader import AppConfig
from app.config.settings import Settings
from app.core.exceptions import ConfigurationError
from app.domain.models import EnrichedPlaceScore, Place, PlaceScore, Point
from app.providers.factory import (
    build_geo_provider,
    build_map_builder,
    build_route_provider,
    build_weather_provider,
)
from app.services.candidate_service import CandidateService
from app.services.enrichment_service import EnrichmentService
from app.services.forecast_service import ForecastService
from app.services.report_service import ReportService
from app.services.scoring_service import ScoringService
from app.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)


class MorningReportJob:
    def __init__(self, settings: Settings, config: AppConfig) -> None:
        self.settings = settings
        self.config = config

    async def run(self, dry_run: bool = False) -> None:
        today = date.today()
        home = Point(lat=self.config.home.lat, lon=self.config.home.lon)

        geo_provider = build_geo_provider(self.config.providers.geo)
        candidate_service = CandidateService(geo_provider)
        places = await asyncio.to_thread(
            candidate_service.find_candidates,
            home,
            self.config.search.radius_km,
            self.config.search.mode,
            self.config.search.max_candidates,
        )
        logger.info("Found %d candidate places", len(places))

        primary_weather = build_weather_provider(
            self.config.providers.weather_primary, self.settings
        )
        fallback_weather = None
        if self.config.providers.weather_fallback:
            try:
                fallback_weather = build_weather_provider(
                    self.config.providers.weather_fallback, self.settings
                )
            except ConfigurationError as exc:
                logger.warning("Weather fallback unavailable, skipping: %s", exc)
        forecast_service = ForecastService(primary_weather, fallback_weather)

        scoring_service = ScoringService(
            self.config.weather_preferences,
            self.config.scoring_weights,
        )

        ranked = await self._score_places(
            places,
            today,
            home,
            forecast_service,
            scoring_service,
        )
        ranked.sort(key=lambda x: x.final_score, reverse=True)
        ranked = ranked[: self.config.search.top_n_places]

        route_provider = build_route_provider(self.config.providers.route)
        trip_history = TripHistoryClient(self.settings.trip_history_url or "")
        user_id = self.settings.telegram_chat_id

        enrichment_service = EnrichmentService(
            geo_provider=geo_provider,
            route_provider=route_provider,
            trip_history=trip_history if trip_history.enabled else None,
            infrastructure_radius_m=self.config.search.infrastructure_radius_m,
        )
        enriched = await enrichment_service.enrich_places(ranked, home, today, user_id)

        map_builder = build_map_builder(self.config.providers.map, self.settings)
        report_service = ReportService(map_builder)
        report = await asyncio.to_thread(
            report_service.build_report,
            enriched,
            today,
            home,
            self.config.search.radius_km,
        )

        if dry_run:
            logger.info("Dry run: report not sent to Telegram")
            print(report.text)
            if report.image_path:
                print(f"\n[map image: {report.image_path}]")
                self._cleanup_image(report.image_path)
            return

        if not self.settings.telegram_bot_token or not self.settings.telegram_chat_id:
            raise ConfigurationError(
                "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required to send a report "
                "(use --dry-run to preview without sending)"
            )

        if trip_history.enabled and user_id:
            await self._save_trips(trip_history, user_id, enriched, today)

        telegram = TelegramService(
            self.settings.telegram_bot_token, self.settings.telegram_chat_id
        )
        await telegram.send_report(report)
        logger.info("Morning report finished")

    async def _score_places(
        self,
        places: list[Place],
        today: date,
        home: Point,
        forecast_service: ForecastService,
        scoring_service: ScoringService,
    ) -> list[PlaceScore]:
        async def _score_one(place: Place) -> PlaceScore | None:
            try:
                forecast = await forecast_service.get_forecast_async(place, today)
                return await asyncio.to_thread(
                    scoring_service.score_place,
                    place,
                    forecast,
                    home,
                    self.config.time.analyze_from,
                    self.config.time.analyze_to,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to process place %s: %s", place.name, exc, exc_info=True
                )
                return None

        results = await asyncio.gather(*[_score_one(p) for p in places])
        min_score = self.config.search.min_acceptable_score
        return [
            score
            for score in results
            if score is not None and score.final_score >= min_score
        ]

    async def _save_trips(
        self,
        trip_history: TripHistoryClient,
        user_id: str,
        enriched: list[EnrichedPlaceScore],
        today: date,
    ) -> None:
        tasks = []
        for item in enriched:
            place_id = item.score.place.place_id or item.score.place.name
            tasks.append(
                trip_history.save_trip(
                    user_id=user_id,
                    place_id=place_id,
                    place_name=item.score.place.name,
                    place_lat=item.score.place.point.lat,
                    place_lon=item.score.place.point.lon,
                    report_date=today,
                    score=item.score.final_score,
                )
            )
        if tasks:
            await asyncio.gather(*tasks)

    @staticmethod
    def _cleanup_image(image_path: str) -> None:
        try:
            os.unlink(image_path)
        except OSError:
            logger.warning("Failed to remove temp map file: %s", image_path)
