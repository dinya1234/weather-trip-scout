# Weather Trip Scout

```text
      ☁️        ☁️
  🌤️
        🚗 ──────> 🏞️
┌─────────────────────────┐
│   Weather Trip Scout    │
│  тихий утренний советчик │
└─────────────────────────┘
```

> Утренний Telegram-бот, который ищет лучшие направления для поездки в радиусе до 100 км и присылает прогноз с картой.

[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](./LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Ruff](https://img.shields.io/badge/linter-ruff-green.svg)](https://docs.astral.sh/ruff/)
[![Mypy](https://img.shields.io/badge/types-mypy-blue.svg)](https://mypy-lang.org/)
[![pytest](https://img.shields.io/badge/tests-pytest-blue.svg)](https://docs.pytest.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](./docker-compose.yml)

---

## Что это

**Weather Trip Scout** — это небольшой Python-агент, который берёт на себя рутину «а куда бы съездить сегодня?». Каждое утро он сам смотрит погоду вокруг домашней точки, оценивает города, деревни и природные объекты по температуре, осадкам, ветру и облачности, а затем присылает в Telegram короткий отчёт: куда стоит поехать, во сколько лучше выезжать и почему.

Если хороших направлений нет — он честно скажет об этом и не выдумает «почти хорошую» погоду.

### Для кого

- Для тех, кто живёт в городе и хочет выбираться на природу или в соседние города по выходным.
- Для владельцев дачи или дома, которым важен прогноз на день в радиусе поездки.
- Для любителей автоматизации, кому нравится получать один аккуратный отчёт вместо бесконечного свайпинга по погодным приложениям.

---

## Возможности

- 🗺️ **Поиск мест** в радиусе до 100 км через Overpass API / OpenStreetMap.
- 🌤️ **Прогноз погоды** на сегодня от Open-Meteo (без ключа) с fallback на OpenWeatherMap.
- 🧮 **Умный скоринг** мест по температуре, осадкам, ветру, облачности, расстоянию и длине «хорошего окна».
- 🛣️ **Маршрут до места** — дистанция и время в пути через OSRM + ссылка на Google Maps.
- 🏨 **Инфраструктура рядом** — отели, кафе и достопримечательности через Overpass.
- 📓 **История поездок и рейтинги** — Java-микросервис `trip-history-service` (Spring Boot + PostgreSQL).
- 🗾 **Статическая карта** PNG с домом, радиусом и маркерами топ-мест (OSM бесплатно; Mapbox — опционально).
- ✉️ **Telegram-отчёт** текстом + изображением карты.
- ⚙️ **Гибкая конфигурация** через `config.yaml`: координаты дома, пороги погоды, веса факторов, провайдеры.
- ⏰ **Запуск по расписанию** через cron / systemd timer или вручную.
- 🐳 **Docker-окружение** «из коробки» (Python-бот + trip-history + PostgreSQL).

---

## Быстрый старт

> Требуется **Python 3.12+**, `git` и `make`. Для Docker-варианта — Docker Compose.

### 1. Клонировать и настроить окружение

```bash
git clone git@github.com:Shugar86/weather-trip-scout.git
cd weather-trip-scout

# Создать и активировать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# Установить зависимости
make install
```

### 2. Секреты

```bash
cp .env.example .env
```

Открой `.env` и заполни обязательные поля:

| Переменная | Обязательная | Описание |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | да* | Токен бота от [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | да* | ID чата или канала для отчётов |
| `OPEN_WEATHER_API_KEY` | нет | Ключ [OpenWeatherMap](https://openweathermap.org/api) для fallback |
| `MAPBOX_TOKEN` | нет | Токен [Mapbox](https://docs.mapbox.com/help/getting-started/access-tokens/) для альтернативной карты |
| `TRIP_HISTORY_URL` | нет | URL Java-сервиса истории поездок, напр. `http://localhost:8080` |

\* Токены Telegram нужны только для реальной отправки. Для предпросмотра отчёта используй `--dry-run` (см. ниже) — он работает без бота.

### 3. Конфигурация

Отредактируй `config.yaml`. Минимальное изменение — координаты дома:

```yaml
home:
  lat: 48.1351   # твои координаты
  lon: 11.5820
```

Полный пример конфигурации см. в [`config.yaml`](./config.yaml).

### 4. Запуск

Разовый отчёт:

```bash
make run
# или: python -m app.main run
```

Алиас с тем же смыслом:

```bash
make report
# или: python -m app.main report
```

Предпросмотр без отправки в Telegram (отчёт печатается в консоль, токены не нужны):

```bash
python -m app.main report --dry-run
```

---

## Docker

```bash
docker compose up --build
```

Compose поднимает три сервиса:

| Сервис | Назначение |
|--------|------------|
| `weather-trip-scout` | Python-бот, утренний отчёт |
| `trip-history` | Java Spring Boot, история и рейтинги |
| `postgres` | БД для trip-history |

Для локального разового запуска с остановкой после выполнения:

```bash
docker compose up --build --abort-on-container-exit
```

Compose читает секреты из `.env` и монтирует `config.yaml` в режиме read-only. Переменная `TRIP_HISTORY_URL` в `.env` для standalone-запуска Python; в Compose она задаётся автоматически (`http://trip-history:8080`).

### Trip-history отдельно

```bash
cd trip-history-service
mvn spring-boot:run
```

Подробнее — в [`trip-history-service/README.md`](./trip-history-service/README.md).

---

## Расписание

### cron

```cron
30 7 * * * cd /path/to/weather-trip-scout && /path/to/.venv/bin/python -m app.main run >> /tmp/weather-trip-scout.log 2>&1
```

### systemd

```bash
sudo cp deploy/weather-trip-scout.service /etc/systemd/system/
sudo cp deploy/weather-trip-scout.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now weather-trip-scout.timer
```

---

## Архитектура и стек

### Поток данных

```text
config.yaml + .env
        │
        ▼
┌───────────────┐
│ MorningReport │
│     Job       │
└───────┬───────┘
        │
   asyncio.gather (параллельно)
        │
    ┌───┴───────────────────────────────┐
    ▼           ▼           ▼           ▼
 Overpass    Open-Meteo    OSRM     trip-history
   (geo)     (weather)   (route)   GET /recent
    │           │           │           │
    ▼           ▼           ▼           ▼
 Candidate   Forecast   Enrichment ◄───┘
  Service    Service     Service
    │           │           │
    └─────┬─────┘           │
          ▼                 │
    Scoring Service         │
          │                 │
          └────────┬────────┘
                   ▼
            Report Service ──► staticmap / Mapbox
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
  Telegram Service    POST /api/trips
                              │
                              ▼
                    trip-history-service
                         (Java)
                              │
                              ▼
                         PostgreSQL
```

### Технологии

| Область | Технология |
|---------|------------|
| Язык | Python 3.12+ |
| HTTP | httpx (sync + async) |
| Конфигурация | Pydantic v2, pydantic-settings, PyYAML |
| Погода | Open-Meteo (primary), OpenWeatherMap (fallback) |
| Гео-поиск | Overpass API / OpenStreetMap (+ JSON-кэш 24 ч) |
| Маршрут | OSRM (бесплатный) |
| Карты | `staticmap` + OSM; Mapbox — опционально |
| История поездок | Java Spring Boot + PostgreSQL |
| Telegram | `python-telegram-bot` |
| Качество кода | pytest, pytest-cov, pytest-asyncio, ruff, mypy |
| Автоматизация | Makefile, Docker, systemd |

### Структура проекта

```text
weather-trip-scout/
├── app/
│   ├── clients/          # REST-клиент к trip-history
│   ├── config/           # Pydantic-модели для config.yaml и .env
│   ├── core/             # Базовые исключения
│   ├── domain/           # Чистые dataclass-модели и scoring-конфиг
│   ├── jobs/             # Сценарии запуска
│   ├── providers/        # Protocol-based адаптеры
│   │   ├── geo/          # Overpass / OSM (+ кэш)
│   │   ├── maps/         # staticmap+OSM, Mapbox
│   │   ├── routing/      # OSRM
│   │   └── weather/      # Open-Meteo, OpenWeatherMap
│   ├── services/         # Stateless бизнес-логика
│   └── main.py           # CLI entrypoint
├── trip-history-service/ # Spring Boot: /api/trips, /api/ratings
├── deploy/               # systemd unit и timer
├── tests/                # unit + интеграционные тесты
├── config.yaml           # Пользовательская конфигурация
├── pyproject.toml        # Метаданные и настройки инструментов
├── Makefile              # Стандартные команды
├── Dockerfile
└── docker-compose.yml
```

### Принципы

- **Domain** не зависит от внешнего мира.
- **Providers** реализуют `Protocol` и легко заменяются.
- **Services** stateless, получают провайдеры через конструктор.
- **Jobs** связывают сервисы в единый сценарий.
- **Config** управляет поведением: провайдеры выбираются по имени через `app/providers/factory.py`.

---

## Провайдеры

| Провайдер | Назначение | Ключ API | Fallback |
|---|---|---|---|
| **Open-Meteo** | Почасовой прогноз | не нужен | — |
| **OpenWeatherMap** | Почасовой прогноз | `OPEN_WEATHER_API_KEY` | Open-Meteo |
| **Overpass / OSM** | Поиск городов и объектов | не нужен | — |
| **OSRM** | Маршрут, дистанция, время | не нужен | — |
| **staticmap + OSM** | Статическая карта | не нужен | — |
| **Mapbox** | Статическая карта | `MAPBOX_TOKEN` | staticmap+OSM |
| **trip-history-service** | История поездок, рейтинги | не нужен | отключён без `TRIP_HISTORY_URL` |

---

## 📍 С чего начать чтение

Чтобы разобраться в проекте за ~15 минут, читай в таком порядке:

1. **`app/main.py`** — точка входа: как собирается пайплайн «найти места → оценить → отправить отчёт».
2. **`app/services/scoring_service.py`** + **`app/domain/scoring.py`** — сердце логики: оценка мест по погоде. Чистое разделение слой-сервис / слой-домен.
3. **`config.yaml`** — координаты дома, пороги погоды, веса факторов, провайдеры. Меняешь поведение без правки кода.

## Примеры

### Пример отчёта в Telegram

```text
🌤 Weather trip scout for 2026-06-19

Top 3 destinations within radius:

1. Starnberg — score 87
   Best window: 10:00:00–16:00:00
   Excellent conditions, best window 10:00:00-16:00:00
   Route: 42.0 km, ~45 min
   Maps: https://www.google.com/maps/dir/?api=1&origin=...
   Nearby: hotels: Hotel Alpha; cafes: Cafe Beta
   Visited before (2026-05-01), your rating: 5/5
```

К отчёту прикрепляется статическая карта с домом и маркерами топ-мест.

### Минимальный конфиг

```yaml
home:
  lat: 55.7558
  lon: 37.6176

search:
  radius_km: 80
  top_n_places: 3
  min_acceptable_score: 60
  mode: towns
  infrastructure_radius_m: 2000

providers:
  weather_primary: open_meteo
  geo: overpass
  map: staticmap_osm
  route: osrm
```

Поля `route` и `infrastructure_radius_m` имеют значения по умолчанию (`osrm` и `2000`), но их лучше явно указать в конфиге.

---

## Тесты и качество кода

Все команды запускаются внутри активированного виртуального окружения.

```bash
make test        # pytest с coverage
make lint        # ruff + mypy
make format      # ruff format + auto-fix
make check       # lint + test
```

Состояние проекта:

- 100+ тестов, покрытие ~85%.
- `mypy --strict` — без ошибок.
- `ruff check app tests` — чисто.

---

## Характер проекта

**Вайб:** `calm` — «тихий утренний советчик».

1. **Честность прежде всего.** Нет хороших направлений — скажем об этом прямо.
2. **Никакого хайпа.** Никаких «ЛУЧШИЙ ДЕНЬ ДЛЯ ПОЕЗДКИ!!!» — только факты, оценки и карта.
3. **Бережное отношение к данным.** Работаем с бесплатными API по умолчанию; fallback включается только при наличии ключа.

---

## Дорожная карта и история изменений

- [CHANGELOG.md](./CHANGELOG.md) — что нового.
- [CONTRIBUTING.md](./CONTRIBUTING.md) — как поучаствовать.

## Лицензия

[MIT](./LICENSE) © 2026 Shugar86.

---

## Известные ограничения и roadmap

- Число кандидатов ограничено `search.max_candidates` (по умолчанию 40), чтобы не упереться в лимиты бесплатных API.
- `MapboxBuilder` показывает только центр карты без маркеров мест; полноценная карта доступна через `staticmap_osm`.
- `send_at_local` в конфиге задаёт целевое время, но реальный запуск управляется cron / systemd.
- Без `TRIP_HISTORY_URL` история поездок и рейтинги не сохраняются — бот работает, но блок «были тут» не появится.
