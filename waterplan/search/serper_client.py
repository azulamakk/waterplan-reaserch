from __future__ import annotations

import time
from typing import List

import httpx

from waterplan.cache.store import get_cache
from waterplan.models.schemas import SearchResult

_API_URL = "https://google.serper.dev/search"


class SerperClient:
    """
    Serper.dev Google Search API.
    2,500 free queries on signup, then $0.001/query. https://serper.dev
    Set SERPER_API_KEY in .env
    """

    def __init__(self, api_key: str, max_results: int = 5, use_cache: bool = True):
        self._api_key = api_key
        self._max_results = max_results
        self._use_cache = use_cache

    def search(self, query: str, location: str = "") -> List[SearchResult]:
        cache = get_cache()
        cache_key = location or query

        if self._use_cache:
            cached = cache.get_search(cache_key, query)
            if cached is not None:
                return [SearchResult(**r) for r in cached]

        results = self._do_search(query)

        if self._use_cache and results:
            cache.set_search(cache_key, query, [r.model_dump() for r in results])

        return results

    def _do_search(self, query: str) -> List[SearchResult]:
        headers = {"X-API-KEY": self._api_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": self._max_results, "hl": "en"}

        for attempt in range(3):
            try:
                r = httpx.post(_API_URL, headers=headers, json=payload, timeout=15)
                r.raise_for_status()
                data = r.json()
                organic = data.get("organic", [])
                return [
                    SearchResult(
                        url=item.get("link", ""),
                        title=item.get("title", ""),
                        snippet=item.get("snippet", ""),
                    )
                    for item in organic
                    if item.get("link")
                ]
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise RuntimeError(f"Serper error: {e}") from e
            except Exception as e:
                if attempt < 2:
                    time.sleep(1.0)
                else:
                    raise RuntimeError(f"Serper search failed: {e}") from e

        return []
