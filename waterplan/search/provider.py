from __future__ import annotations

import os
from typing import List, Protocol

from waterplan.models.schemas import SearchResult


class SearchProvider(Protocol):
    def search(self, query: str, location: str = "") -> List[SearchResult]: ...


def get_search_provider(use_cache: bool = True, max_results: int = 5) -> SearchProvider:
    """
    Returns the best available search provider based on environment config.

    Priority order:
      1. SEARXNG_URL set → SearXNG (self-hosted, unlimited, free)
      2. SEARXNG_URL=auto and Docker SearXNG running → SearXNG auto-detected
      3. BRAVE_SEARCH_API_KEY set → Brave Search (2,000 free/mo)
      4. SERPER_API_KEY set → Serper (2,500 free then $0.001/q)
      5. Default → DuckDuckGo (free, rate-limited)
    """
    searxng_url = os.getenv("SEARXNG_URL", "").strip()

    # Explicit SearXNG URL configured
    if searxng_url and searxng_url != "auto":
        from waterplan.search.searxng_client import SearXNGClient
        return SearXNGClient(base_url=searxng_url, max_results=max_results, use_cache=use_cache)

    # Auto-detect local SearXNG (Docker default port)
    if searxng_url == "auto" or not searxng_url:
        from waterplan.search.searxng_client import SearXNGClient
        candidate = SearXNGClient(base_url="http://localhost:8080", max_results=max_results, use_cache=use_cache)
        if candidate.is_available():
            return candidate

    # Brave Search API
    brave_key = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
    if brave_key:
        from waterplan.search.brave_client import BraveSearchClient
        return BraveSearchClient(api_key=brave_key, max_results=max_results, use_cache=use_cache)

    # Serper.dev
    serper_key = os.getenv("SERPER_API_KEY", "").strip()
    if serper_key:
        from waterplan.search.serper_client import SerperClient
        return SerperClient(api_key=serper_key, max_results=max_results, use_cache=use_cache)

    # Fallback: DuckDuckGo
    from waterplan.search.ddg_client import DDGSearchClient
    return DDGSearchClient(max_results=max_results, use_cache=use_cache)


def provider_name() -> str:
    """Return which provider will be used (for display in CLI)."""
    searxng_url = os.getenv("SEARXNG_URL", "").strip()
    if searxng_url and searxng_url != "auto":
        return f"SearXNG ({searxng_url})"
    if not searxng_url:
        from waterplan.search.searxng_client import SearXNGClient
        if SearXNGClient().is_available():
            return "SearXNG (localhost:8080, auto-detected)"
    if os.getenv("BRAVE_SEARCH_API_KEY"):
        return "Brave Search"
    if os.getenv("SERPER_API_KEY"):
        return "Serper.dev"
    return "DuckDuckGo"
