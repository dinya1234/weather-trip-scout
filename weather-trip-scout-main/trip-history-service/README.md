# trip-history-service

Spring Boot микросервис для хранения истории поездок и рейтингов мест Weather Trip Scout.

## API

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/trips` | Сохранить поездку |
| GET | `/api/trips/recent` | Недавние поездки (`userId`, опционально `placeId`, `beforeDate`, `limit`) |
| POST | `/api/ratings` | Сохранить оценку места (1–5) |
| GET | `/api/ratings` | Получить оценку (`userId`, `placeId`) |

## Локальный запуск (H2 in-memory)

```bash
cd trip-history-service
mvn spring-boot:run
```

Сервис слушает `http://localhost:8080`.

## Docker

```bash
docker compose up trip-history postgres
```

PostgreSQL поднимается автоматически через `docker-compose.yml` в корне проекта.

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `PORT` | `8080` | HTTP-порт |
| `DATABASE_URL` | H2 in-memory | JDBC URL |
| `DATABASE_USERNAME` | `sa` | Пользователь БД |
| `DATABASE_PASSWORD` | `` | Пароль БД |
| `DATABASE_DRIVER` | `org.h2.Driver` | JDBC driver |

## Тесты

```bash
mvn test
```
