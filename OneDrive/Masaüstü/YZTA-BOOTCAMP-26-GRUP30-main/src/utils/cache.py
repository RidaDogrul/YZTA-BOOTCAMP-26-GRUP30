"""
In-memory TTL cache utilities.

Sprint 2 - S2-L2 scope:
- Cache repeated query/chat results for a short period.
- Provide a deterministic cache key builder.
- Keep the MVP lightweight without external services such as Redis.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """Single cache entry with expiration metadata."""

    value: T
    created_at: float
    expires_at: float

    def is_expired(self, now: float) -> bool:
        return now >= self.expires_at


class TTLCache(Generic[T]):
    """Simple in-memory TTL cache for Sprint 2 MVP."""

    def __init__(
        self,
        *,
        default_ttl_seconds: float = 300.0,
        max_size: int = 256,
        time_provider: Callable[[], float] | None = None,
    ) -> None:
        if default_ttl_seconds <= 0:
            raise ValueError("default_ttl_seconds pozitif olmalıdır.")

        if max_size < 1:
            raise ValueError("max_size en az 1 olmalıdır.")

        self.default_ttl_seconds = default_ttl_seconds
        self.max_size = max_size
        self._time_provider = time_provider or time.monotonic
        self._store: dict[str, CacheEntry[T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._store.get(key)
        if entry is None:
            return None

        now = self._time_provider()
        if entry.is_expired(now):
            self._store.pop(key, None)
            return None

        return entry.value

    def set(self, key: str, value: T, *, ttl_seconds: float | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds

        if ttl <= 0:
            raise ValueError("ttl_seconds pozitif olmalıdır.")

        self._evict_expired()

        if len(self._store) >= self.max_size and key not in self._store:
            self._evict_oldest()

        now = self._time_provider()
        self._store[key] = CacheEntry(
            value=value,
            created_at=now,
            expires_at=now + ttl,
        )

    def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def clear(self) -> None:
        self._store.clear()

    def stats(self) -> dict[str, int]:
        self._evict_expired()
        return {
            "size": len(self._store),
            "max_size": self.max_size,
        }

    def __len__(self) -> int:
        self._evict_expired()
        return len(self._store)

    def _evict_expired(self) -> None:
        now = self._time_provider()
        expired_keys = [
            key for key, entry in self._store.items() if entry.is_expired(now)
        ]

        for key in expired_keys:
            self._store.pop(key, None)

    def _evict_oldest(self) -> None:
        if not self._store:
            return

        oldest_key = min(
            self._store,
            key=lambda key: self._store[key].created_at,
        )
        self._store.pop(oldest_key, None)


def make_cache_key(*parts: object, **params: object) -> str:
    """
    Build a deterministic cache key from request/query parameters.

    Example:
        make_cache_key("chat", session_id, question, include_sql=True)
    """
    payload = {
        "parts": parts,
        "params": params,
    }
    normalized = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


query_cache: TTLCache[Any] = TTLCache(default_ttl_seconds=300.0, max_size=256)