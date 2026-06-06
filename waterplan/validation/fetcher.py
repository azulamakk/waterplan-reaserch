from __future__ import annotations

import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from waterplan.cache.store import get_cache
from waterplan.config import get_settings
from waterplan.models.schemas import FetchResult

_JS_MARKERS = [
    '<div id="root">',
    '<div id="app">',
    "__NEXT_DATA__",
    "window.React",
    "__nuxt",
    "ng-version",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _is_js_heavy(html: str) -> bool:
    text_content = BeautifulSoup(html, "lxml").get_text(separator=" ", strip=True)
    if len(text_content) < 200 and any(m in html for m in _JS_MARKERS):
        return True
    return False


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def fetch_page(url: str, use_cache: bool = True) -> FetchResult:
    settings = get_settings()
    cache = get_cache()

    if use_cache:
        cached = cache.get_page(url)
        if cached is not None:
            return FetchResult(
                text_content=cached,
                status_code=200,
                final_url=url,
                method_used="cache",
            )

    result = _fetch_httpx(url, settings.validation_timeout_s)

    if result.method_used == "httpx" and result.status_code == 200:
        if _is_js_heavy(result.text_content):
            result = _fetch_playwright(url, settings.playwright_timeout_ms)

    if result.text_content and use_cache:
        cache.set_page(url, result.text_content)

    return result


def _fetch_httpx(url: str, timeout: int) -> FetchResult:
    try:
        with httpx.Client(
            headers=_HEADERS,
            follow_redirects=True,
            timeout=timeout,
        ) as client:
            response = client.get(url)
            content_type = response.headers.get("content-type", "")
            if "html" in content_type or "text" in content_type:
                text = _extract_text(response.text)
            else:
                text = ""
            return FetchResult(
                text_content=text,
                status_code=response.status_code,
                final_url=str(response.url),
                method_used="httpx",
            )
    except httpx.TimeoutException:
        return FetchResult(
            text_content="",
            status_code=0,
            final_url=url,
            method_used="failed",
            error="Connection timeout",
        )
    except Exception as e:
        return FetchResult(
            text_content="",
            status_code=0,
            final_url=url,
            method_used="failed",
            error=str(e),
        )


def _fetch_playwright(url: str, timeout_ms: int) -> FetchResult:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(extra_http_headers=_HEADERS)
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            text = page.evaluate("() => document.body.innerText")
            final_url = page.url
            browser.close()
            return FetchResult(
                text_content=text or "",
                status_code=200,
                final_url=final_url,
                method_used="playwright",
            )
    except Exception as e:
        return FetchResult(
            text_content="",
            status_code=0,
            final_url=url,
            method_used="failed",
            error=f"Playwright error: {e}",
        )
