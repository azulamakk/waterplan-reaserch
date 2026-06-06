from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from langchain_core.tools import tool

from waterplan.models.schemas import Source, ValidationStatus
from waterplan.search.provider import get_search_provider
from waterplan.validation.fetcher import fetch_page
from waterplan.validation.validator import validate_excerpt


def make_tools(findings: Dict[str, List[Source]], use_cache: bool = True):
    """
    Returns a list of LangChain tools bound to the shared `findings` dict.
    Each call to record_finding accumulates into this dict.
    """
    searcher = get_search_provider(use_cache=use_cache, max_results=5)

    @tool
    def search_water_risk(query: str, dimension: str) -> str:
        """Search the web for water risk information about a location and dimension.

        Returns a numbered list of results with URL, title, and content snippet.
        Use the returned snippets as candidates for excerpt — pick verbatim text.

        Args:
            query: Search query string (include location name)
            dimension: One of: water_stress, incidents, regulations
        """
        valid_dims = {"water_stress", "incidents", "regulations"}
        if dimension not in valid_dims:
            return f"ERROR: dimension must be one of {valid_dims}"

        try:
            results = searcher.search(query, location=query)
        except Exception as e:
            return f"ERROR: Search failed — {e}"

        if not results:
            return "No results found. Try a different query."

        lines = [f"Found {len(results)} results for query: '{query}'\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] Title: {r.title}")
            lines.append(f"    URL: {r.url}")
            lines.append(f"    Snippet: {r.snippet[:400]}")
            lines.append("")
        return "\n".join(lines)

    @tool
    def fetch_and_validate(url: str, excerpt: str) -> str:
        """Fetch a URL and verify that the given excerpt appears in the page content.

        The excerpt MUST be copied verbatim from what search_water_risk returned.
        Never paraphrase or modify the excerpt before calling this tool.

        Args:
            url: The URL to fetch and validate
            excerpt: The exact text from the search snippet to verify in the page
        """
        if not url.startswith(("http://", "https://")):
            return "FAILED_VALIDATION: Not a valid URL"

        if len(excerpt.strip()) < 10:
            return "FAILED_VALIDATION: Excerpt too short to validate meaningfully"

        fetch_result = fetch_page(url, use_cache=use_cache)
        validation = validate_excerpt(excerpt, fetch_result)

        status_str = "MATCH_FOUND" if validation.status == ValidationStatus.MATCH else "FAILED_VALIDATION"
        return (
            f"{status_str}\n"
            f"Detail: {validation.detail}\n"
            f"Fetch method: {fetch_result.method_used}\n"
            f"Final URL: {fetch_result.final_url}"
        )

    @tool
    def record_finding(
        dimension: str,
        url: str,
        title: str,
        excerpt: str,
        summary: str,
        validation_status: str,
    ) -> str:
        """Record a validated finding into the research report.

        Only call this AFTER fetch_and_validate has confirmed the excerpt.
        The excerpt must be verbatim from the source.

        Args:
            dimension: One of: water_stress, incidents, regulations
            url: Source URL (must have been validated)
            title: Source title
            excerpt: Verbatim text from the source (verified by fetch_and_validate)
            summary: 1-2 sentence finding summary in your own words
            validation_status: Copy the status from fetch_and_validate output
        """
        valid_dims = {"water_stress", "incidents", "regulations"}
        if dimension not in valid_dims:
            return f"ERROR: dimension must be one of {valid_dims}"

        status = (
            ValidationStatus.MATCH
            if "MATCH_FOUND" in validation_status
            else ValidationStatus.FAILED
        )

        if dimension not in findings:
            findings[dimension] = []

        # Deduplicate by URL — reject if this URL is already recorded for this dimension
        existing_urls = {s.url for s in findings[dimension]}
        if url in existing_urls:
            count = len(findings[dimension])
            return (
                f"Source already recorded for {dimension}. "
                f"Total sources: {count}. Search for a DIFFERENT source URL."
            )

        source = Source(
            url=url,
            title=title,
            excerpt=excerpt,
            validation_status=status,
            validation_detail=validation_status,
            fetched_at=datetime.now(timezone.utc),
        )
        findings[dimension].append(source)

        count = len(findings[dimension])
        return (
            f"Finding recorded for {dimension}. "
            f"Total sources for this dimension: {count}. "
            f"{'✅ You have enough sources for this dimension.' if count >= 2 else '⚠️ You need at least 1 more source for this dimension.'}"
        )

    @tool
    def finish_research(
        water_stress_summary: str,
        incidents_summary: str,
        regulations_summary: str,
        overall_confidence: float,
    ) -> str:
        """Signal that research is complete with final summaries for each dimension.

        Only call this when ALL three dimensions have at least 2 recorded findings.

        Args:
            water_stress_summary: 2-3 sentence synthesis of water stress findings
            incidents_summary: 2-3 sentence synthesis of incidents/conflicts findings
            regulations_summary: 2-3 sentence synthesis of regulations findings
            overall_confidence: Confidence score 0.0-1.0 based on source quality
        """
        missing = []
        for dim in ["water_stress", "incidents", "regulations"]:
            count = len(findings.get(dim, []))
            if count < 2:
                missing.append(f"{dim} (has {count}, needs 2)")

        if missing:
            return (
                f"NOT READY: Missing sources for: {', '.join(missing)}. "
                "Keep searching before calling finish_research."
            )

        # Store summaries for the caller to extract
        findings["__summaries__"] = {  # type: ignore[assignment]
            "water_stress": water_stress_summary,
            "incidents": incidents_summary,
            "regulations": regulations_summary,
            "confidence": overall_confidence,
        }

        total = sum(len(findings.get(d, [])) for d in ["water_stress", "incidents", "regulations"])
        return (
            f"Research complete. {total} sources recorded across 3 dimensions. "
            f"Confidence: {overall_confidence:.2f}"
        )

    return [search_water_risk, fetch_and_validate, record_finding, finish_research]
