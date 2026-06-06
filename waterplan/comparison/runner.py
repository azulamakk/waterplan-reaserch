from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Dict, List, Optional

from waterplan.agent.research_agent import research_location
from waterplan.comparison.scorer import score_report
from waterplan.config import get_model, get_settings
from waterplan.models.schemas import LocationReport, ModelComparisonResult, ModelScore
from waterplan.search.provider import get_search_provider
from waterplan.search.query_builder import all_queries


def _prewarm_cache(location: str) -> None:
    """Pre-warm search cache before model comparison so all models see identical results."""
    searcher = get_search_provider(use_cache=True, max_results=5)
    queries = all_queries(location)
    for dim_queries in queries.values():
        for q in dim_queries:
            try:
                searcher.search(q, location=location)
            except Exception:
                pass


def _run_single(
    location: str,
    model_id: str,
    use_cache: bool,
    verbose: bool,
) -> tuple[str, Optional[LocationReport], Optional[str]]:
    try:
        model = get_model(model_id, temperature=0.0)
        report = research_location(
            location=location,
            model=model,
            model_id=model_id,
            use_cache=use_cache,
            verbose=verbose,
        )
        return model_id, report, None
    except Exception as e:
        return model_id, None, str(e)


def compare_models(
    location: str,
    models: Optional[List[str]] = None,
    use_cache: bool = True,
    verbose: bool = False,
    max_workers: int = 2,
) -> ModelComparisonResult:
    settings = get_settings()
    model_ids = models or settings.models_to_compare

    # Pre-warm cache so all models get identical search results
    if use_cache:
        _prewarm_cache(location)

    results: Dict[str, LocationReport] = {}
    scores: Dict[str, ModelScore] = {}
    errors: Dict[str, str] = {}

    # Run models in parallel threads (LangChain agents are sync)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_run_single, location, mid, use_cache, verbose): mid
            for mid in model_ids
        }
        for future in concurrent.futures.as_completed(futures):
            model_id, report, error = future.result()
            if report is not None:
                results[model_id] = report
                scores[model_id] = score_report(report)
            else:
                errors[model_id] = error or "Unknown error"

    if errors:
        import sys
        from rich.console import Console
        console = Console(stderr=True)
        for mid, err in errors.items():
            console.print(f"[yellow]Warning: {mid} failed — {err}[/yellow]")

    return ModelComparisonResult(
        location=location,
        results=results,
        scores=scores,
    )
