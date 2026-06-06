from __future__ import annotations

import re
from typing import List

from waterplan.models.schemas import LocationReport, ModelScore, ValidationStatus


def score_report(report: LocationReport) -> ModelScore:
    dims = [report.water_stress, report.incidents, report.regulations]
    all_sources = [s for d in dims for s in d.sources]

    # 1. Validation pass rate (35%)
    if all_sources:
        passed = sum(1 for s in all_sources if s.validation_status == ValidationStatus.MATCH)
        pass_rate = passed / len(all_sources)
    else:
        pass_rate = 0.0

    # 2. Avg source relevance from self-critique (25%)
    relevance_scores = []
    for dim in dims:
        if dim.self_critique:
            m = re.search(r"(\d+\.?\d+)/10", dim.self_critique)
            if m:
                relevance_scores.append(float(m.group(1)) / 10)
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.5

    # 3. Source count (15%) — reward having more than minimum (2 per dim = 6 total)
    source_count_score = min(len(all_sources) / 6, 1.5) / 1.5  # normalized, capped at 1.0

    # 4. Data freshness (15%) — sources mentioning 2020+ years
    if all_sources:
        recent = sum(
            1 for s in all_sources
            if any(str(y) in s.excerpt + s.title for y in range(2020, 2026))
        )
        freshness = recent / len(all_sources)
    else:
        freshness = 0.0

    # 5. Completeness (10%) — all 3 dimensions have a non-empty summary
    complete_dims = sum(1 for d in dims if d.summary and d.summary != "No summary available.")
    completeness = complete_dims / 3

    overall = (
        0.35 * pass_rate
        + 0.25 * avg_relevance
        + 0.15 * source_count_score
        + 0.15 * freshness
        + 0.10 * completeness
    ) * 100

    return ModelScore(
        model_id=report.model_used,
        validation_pass_rate=round(pass_rate * 100, 1),
        avg_source_relevance=round(avg_relevance * 10, 2),
        source_count=len(all_sources),
        latency_ms=report.latency_ms,
        cost_usd=report.cost_usd,
        overall_score=round(overall, 1),
    )
