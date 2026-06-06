from __future__ import annotations

import json
import os
from typing import List, Optional

from waterplan.cache.store import get_cache
from waterplan.config import get_settings, get_model
from waterplan.models.schemas import CritiqueResult, Source
from waterplan.agent.prompts import SELF_CRITIQUE_PROMPT


def _pick_judge_model() -> str:
    """Pick the cheapest available judge model based on configured API keys.

    Cost order (cheapest first, as of 2025):
      gpt-4o-mini   $0.15/$0.60 per MTok  in/out
      claude-haiku  $0.80/$4.00 per MTok  in/out
    """
    settings = get_settings()
    if settings.openai_api_key:
        return "gpt-4o-mini"
    if settings.anthropic_api_key:
        return "claude-haiku-4-5-20251001"
    # Fall back to config default — will fail gracefully if unavailable
    return settings.judge_model


def critique_sources(
    location: str,
    dimension: str,
    sources: List[Source],
    use_cache: bool = True,
) -> List[CritiqueResult]:
    """Run the self-critique judge on a list of sources using the cheapest available model."""
    cache = get_cache()
    results = []

    judge_model_id = _pick_judge_model()
    try:
        judge = get_model(judge_model_id, temperature=0.0)
    except Exception:
        # No model available — return neutral scores
        return [_neutral_critique() for _ in sources]

    for source in sources:
        if use_cache:
            cached = cache.get_critique(source.url, dimension)
            if cached:
                suggestion = cached.get("suggestion", "")
                # Skip stale entries that stored error messages
                if not ("Could not critique" in suggestion or "Error code" in suggestion):
                    results.append(CritiqueResult(**cached))
                    continue

        prompt = SELF_CRITIQUE_PROMPT.format(
            location=location,
            dimension=dimension,
            url=source.url,
            title=source.title,
            excerpt=source.excerpt[:500],
            summary=source.validation_detail[:300],
        )

        try:
            response = judge.invoke(prompt)
            raw = response.content if hasattr(response, "content") else str(response)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            critique = CritiqueResult(
                relevance=float(data.get("relevance", 5)),
                recency=str(data.get("recency", "unknown")),
                authority=str(data.get("authority", "other")),
                suggestion=str(data.get("suggestion", "")),
                overall_score=float(data.get("overall_score", 5)),
            )
        except Exception:
            results.append(_neutral_critique())
            continue  # don't cache failures — retry next time

        cache.set_critique(source.url, dimension, critique.model_dump())
        results.append(critique)

    return results


def _neutral_critique() -> CritiqueResult:
    return CritiqueResult(
        relevance=5.0,
        recency="unknown",
        authority="other",
        suggestion="",
        overall_score=5.0,
    )


def avg_relevance(critiques: List[CritiqueResult]) -> float:
    if not critiques:
        return 0.0
    return sum(c.overall_score for c in critiques) / len(critiques)
