from __future__ import annotations

import time
from typing import List, Optional

from waterplan.cache.store import get_cache
from waterplan.models.schemas import SearchResult


class DDGSearchClient:
    """DuckDuckGo search client via the `ddgs` package — free, no API key required."""

    def __init__(self, max_results: int = 5, use_cache: bool = True):
        self._max_results = max_results
        self._use_cache = use_cache

    def search(self, query: str, location: str = "") -> List[SearchResult]:
        cache = get_cache()
        cache_key_loc = location or query

        if self._use_cache:
            cached = cache.get_search(cache_key_loc, query)
            if cached is not None:
                return [SearchResult(**r) for r in cached]

        results = self._do_search(query)

        if self._use_cache and results:
            cache.set_search(cache_key_loc, query, [r.model_dump() for r in results])

        return results

    def _do_search(self, query: str) -> List[SearchResult]:
        # Try `ddgs` first (new package name), fall back to `duckduckgo_search` (old name)
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS  # type: ignore[no-redef]
            except ImportError:
                raise RuntimeError(
                    "No DuckDuckGo search package found. "
                    "Install with: pip install ddgs"
                )

        for attempt in range(3):
            try:
                with DDGS() as ddgs:
                    raw = list(
                        ddgs.text(
                            query,
                            max_results=self._max_results,
                            region="wt-wt",   # worldwide results in English
                        )
                    )
                results = [
                    SearchResult(
                        url=r.get("href", ""),
                        title=r.get("title", ""),
                        snippet=r.get("body", ""),
                    )
                    for r in raw
                    if r.get("href")
                ]
                if results:
                    return results
                # Empty but no error — brief pause then retry
                time.sleep(1.0 + attempt)
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise RuntimeError(f"DuckDuckGo search failed after 3 attempts: {e}") from e

        return []
