from __future__ import annotations

import threading
import time
from typing import List, Optional

import httpx

from waterplan.cache.store import get_cache
from waterplan.models.schemas import SearchResult

_DEFAULT_URL = "http://localhost:8080"

# Limit concurrent SearXNG requests across all threads to avoid triggering
# rate limits / CAPTCHAs on the underlying engines (Google, Bing, DDG).
_SEARCH_SEMAPHORE = threading.Semaphore(2)

_SEARXNG_PARAMS = {
    "format": "json",
    "language": "en",
    "safesearch": "0",
    "categories": "general",
}


class SearXNGClient:
    """
    Client for a self-hosted SearXNG instance.
    Run locally: docker run -d -p 8080:8080 searxng/searxng
    No API key, no rate limits, aggregates Google/Bing/DDG/Wikipedia.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_URL,
        max_results: int = 5,
        use_cache: bool = True,
        timeout: int = 15,
    ):
        self._base_url = base_url.rstrip("/")
        self._max_results = max_results
        self._use_cache = use_cache
        self._timeout = timeout

    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{self._base_url}/healthz", timeout=3)
            return r.status_code == 200
        except Exception:
            try:
                # Some SearXNG versions don't have /healthz — try the root
                r = httpx.get(self._base_url, timeout=3)
                return r.status_code == 200
            except Exception:
                return False

    def search(self, query: str, location: str = "") -> List[SearchResult]:
        cache = get_cache()
        cache_key = location or query

        if self._use_cache:
            cached = cache.get_search(cache_key, query)
            if cached is not None:
                return [SearchResult(**r) for r in cached]

        results = self._do_search(query)

        # If SearXNG returns nothing (all engines suspended/CAPTCHAd), fall back to DDG
        if not results:
            results = self._ddg_fallback(query)

        if self._use_cache and results:
            cache.set_search(cache_key, query, [r.model_dump() for r in results])

        return results

    def _ddg_fallback(self, query: str) -> List[SearchResult]:
        try:
            from waterplan.search.ddg_client import DDGSearchClient
            return DDGSearchClient(max_results=self._max_results, use_cache=False).search(query)
        except Exception:
            return []

    def _do_search(self, query: str) -> List[SearchResult]:
        post_data = {**_SEARXNG_PARAMS, "q": query}
        url = f"{self._base_url}/search"

        for attempt in range(3):
            try:
                with _SEARCH_SEMAPHORE:
                    response = httpx.post(url, data=post_data, timeout=self._timeout)
                    time.sleep(0.5)  # brief pause after each request to avoid engine bans
                response.raise_for_status()
                raw = response.json()
                raw_results = raw.get("results", [])

                # If every result comes only from Bing, all other engines are suspended —
                # the results will be low-quality. Signal empty so DDG fallback triggers.
                active_engines = {e for r in raw_results for e in r.get("engines", [])}
                if active_engines and active_engines <= {"bing"}:
                    return []

                return [
                    SearchResult(
                        url=r.get("url", ""),
                        title=r.get("title", ""),
                        snippet=r.get("content", r.get("snippet", "")),
                    )
                    for r in raw_results[: self._max_results]
                    if r.get("url")
                ]
            except httpx.HTTPStatusError as e:
                if attempt < 2:
                    time.sleep(1.0 * (attempt + 1))
                else:
                    raise RuntimeError(
                        f"SearXNG returned HTTP {e.response.status_code}. "
                        "Is your SearXNG instance running? "
                        f"docker run -d -p 8080:8080 searxng/searxng"
                    ) from e
            except httpx.ConnectError:
                raise RuntimeError(
                    f"Cannot connect to SearXNG at {self._base_url}. "
                    "Start it with: docker run -d -p 8080:8080 searxng/searxng"
                )
            except Exception as e:
                if attempt < 2:
                    time.sleep(1.0)
                else:
                    raise RuntimeError(f"SearXNG search failed: {e}") from e

        return []
