import re
import time
from threading import Lock
from typing import Any


class ResponseCache:
    """Simple in-memory TTL cache for approved assistant responses."""

    def __init__(self, ttl_seconds: int = 300, max_entries: int = 500):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._store: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def get(self, key: str) -> dict[str, Any] | None:
        now = time.time()
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            if item["expires_at"] < now:
                del self._store[key]
                return None
            return item

    def set(self, key: str, response: str, metadata: dict[str, Any] | None = None):
        now = time.time()
        payload = {
            "response": response,
            "metadata": metadata or {},
            "expires_at": now + self.ttl_seconds,
        }
        with self._lock:
            if len(self._store) >= self.max_entries:
                # Remove oldest expiring item to keep memory bounded.
                oldest_key = min(self._store, key=lambda k: self._store[k]["expires_at"])
                del self._store[oldest_key]
            self._store[key] = payload

    def clear(self):
        with self._lock:
            self._store.clear()


_order_id_regex = re.compile(r"(SE-\d{4})", re.IGNORECASE)
_ws_regex = re.compile(r"\s+")


def make_cache_key(user_text: str) -> str:
    """
    Build a stable cache key.
    If an order id is present, preserve it exactly; otherwise normalize whitespace.
    """
    raw = (user_text or "").strip()
    order_match = _order_id_regex.search(raw)
    if order_match:
        order_id = order_match.group(1).upper()
        normalized = _ws_regex.sub(" ", raw.lower())
        return f"order:{order_id}|q:{normalized}"
    return f"q:{_ws_regex.sub(' ', raw.lower())}"


response_cache = ResponseCache(ttl_seconds=300, max_entries=500)
