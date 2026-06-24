import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(".cache/overpass")
DEFAULT_TTL = timedelta(hours=24)


class OverpassCache:
    """JSON file cache for Overpass API responses with a 24-hour TTL."""

    def __init__(
        self,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        ttl: timedelta = DEFAULT_TTL,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl

    def _key_path(self, query: str) -> Path:
        digest = hashlib.sha256(query.encode()).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def get(self, query: str) -> dict[str, Any] | None:
        path = self._key_path(query)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            created_at = datetime.fromisoformat(payload["created_at"])
            if datetime.now(tz=UTC) - created_at > self.ttl:
                path.unlink(missing_ok=True)
                return None
            data = payload.get("data")
            return data if isinstance(data, dict) else None
        except (OSError, ValueError, KeyError) as exc:
            logger.warning("Overpass cache read failed: %s", exc)
            path.unlink(missing_ok=True)
            return None

    def set(self, query: str, data: dict[str, Any]) -> None:
        path = self._key_path(query)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "created_at": datetime.now(tz=UTC).isoformat(),
                "data": data,
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError as exc:
            logger.warning("Overpass cache write failed: %s", exc)
