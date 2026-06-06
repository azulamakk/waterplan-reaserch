from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

import diskcache

from waterplan.config import get_settings


class CacheStore:
    def __init__(self):
        settings = get_settings()
        settings.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = diskcache.Cache(
            directory=str(settings.cache_dir),
            size_limit=500_000_000,  # 500MB
        )
        self._ttl = settings.cache_ttl_hours * 3600

    def _key(self, *parts: str) -> str:
        combined = ":".join(parts)
        return hashlib.sha256(combined.encode()).hexdigest()

    def get_search(self, location: str, query: str) -> Optional[list]:
        return self._cache.get(self._key("search", location, query))

    def set_search(self, location: str, query: str, results: list) -> None:
        self._cache.set(self._key("search", location, query), results, expire=self._ttl)

    def get_page(self, url: str) -> Optional[str]:
        return self._cache.get(self._key("page", url))

    def set_page(self, url: str, content: str) -> None:
        self._cache.set(self._key("page", url), content, expire=self._ttl)

    def get_critique(self, url: str, dimension: str) -> Optional[dict]:
        return self._cache.get(self._key("critique", dimension, url))

    def set_critique(self, url: str, dimension: str, result: dict) -> None:
        self._cache.set(self._key("critique", dimension, url), result, expire=self._ttl)

    def stats(self) -> dict:
        return {
            "size_mb": round(self._cache.volume() / 1_000_000, 2),
            "count": len(self._cache),
        }

    def clear(self) -> None:
        self._cache.clear()

    def close(self) -> None:
        self._cache.close()


_store: Optional[CacheStore] = None


def get_cache() -> CacheStore:
    global _store
    if _store is None:
        _store = CacheStore()
    return _store
