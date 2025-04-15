import threading
from datetime import datetime, timezone
from typing import Any, Callable, Tuple


class TimeCacheItem:
    def __init__(self, value: Any, created_at: float, ttl_seconds: float) -> None:
        self.value = value
        self.created_at = created_at
        self.ttl_seconds = ttl_seconds

    def is_expired(self, now: float):
        return now > self.created_at + self.ttl_seconds


class TimeCache:
    def __init__(self) -> None:
        self.data: dict[str, TimeCacheItem] = {}
        self._lock = threading.Lock()

    def get(self, key: str, value_provider: Callable[[], Tuple[Any, float]]) -> Any:
        now = datetime.now(timezone.utc).timestamp()

        with self._lock:
            item = self.data.get(key, None)

            if item is None or item.is_expired(now):
                item = self._create_item(now, value_provider)
                self.data[key] = item

            return item.value

    def _create_item(self, now: float, value_provider: Callable[[], Tuple[Any, float]]) -> TimeCacheItem:
        value, ttl_seconds = value_provider()

        return TimeCacheItem(
            value=value,
            created_at=now,
            ttl_seconds=ttl_seconds
        )
