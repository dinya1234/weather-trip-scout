## [Unreleased]

### Added
- Маршрут до места через OSRM: дистанция, время в пути, ссылка на Google Maps в отчёте.
- Инфраструктура места (отели, кафе, достопримечательности) через расширенный Overpass-провайдер.
- Java-микросервис `trip-history-service` (Spring Boot + JPA): история поездок, заметки и рейтинги мест.
- Python-клиент к trip-history: POST `/api/trips` после отчёта, GET `/api/trips/recent` для блока «были тут».
- REST API рейтингов: POST/GET `/api/ratings` в Java-сервисе.
- Кэш Overpass-ответов в JSON-файлах с TTL 24 часа (`.cache/overpass/`).
- Параллельная обработка мест через `asyncio.gather` и async-провайдеры погоды/маршрута/инфраструктуры.
- Конфиг `providers.route` (по умолчанию `osrm`) и `search.infrastructure_radius_m`.
- Переменная окружения `TRIP_HISTORY_URL` для адреса Java-сервиса.

### Changed
- HTTP-клиент переведён с `requests` на `httpx` (sync + async).
- `ReportService` формирует расширенный отчёт с маршрутом, инфраструктурой и историей.
- `docker-compose.yml` поднимает PostgreSQL, trip-history-service и Python-бот.
- Временные PNG-карты удаляются после отправки в Telegram.

### Fixed
- Режим `--dry-run` для команд `run`/`report`: полный пайплайн с выводом отчёта в stdout без отправки в Telegram (и без необходимости в токене бота).
- Ограничение `search.max_candidates` (по умолчанию 40): берём ближайшие места, чтобы не делать сотни запросов погоды.
- Overpass возвращал `406 Not Acceptable` на дефолтный User-Agent — теперь шлём собственный User-Agent.
- Отсутствие ключа OpenWeatherMap больше не роняет запуск.

## [0.1.0] — 2026-06-13