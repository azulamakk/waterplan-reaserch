from __future__ import annotations

import time
from typing import List

import httpx

from waterplan.cache.store import get_cache
from waterplan.models.schemas import SearchResult

_API_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveSearchClient:
    """
    Brave Search API client.
    Free tier: 2,000 queries/month. Sign up at https://api.search.brave.com/
    Set BRAVE_SEARCH_API_KEY in .env
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
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self._api_key,
        }
        params = {"q": query, "count": self._max_results, "search_lang": "en"}

        for attempt in range(3):
            try:
                r = httpx.get(_API_URL, headers=headers, params=params, timeout=15)
                r.raise_for_status()
                data = r.json()
                web = data.get("web", {}).get("results", [])
                return [
                    SearchResult(
                        url=item.get("url", ""),
                        title=item.get("title", ""),
                        snippet=item.get("description", ""),
                    )
                    for item in web
                    if item.get("url")
                ]
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise RuntimeError(f"Brave Search error: {e}") from e
            except Exception as e:
                if attempt < 2:
                    time.sleep(1.0)
                else:
                    raise RuntimeError(f"Brave Search failed: {e}") from e

        return []
