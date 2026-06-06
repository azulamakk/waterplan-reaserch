from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

from waterplan.models.schemas import LocationReport


def reports_to_dataframe(reports: List[LocationReport]) -> pd.DataFrame:
    rows = []
    for report in reports:
        for dim_name in ["water_stress", "incidents", "regulations"]:
            dim = getattr(report, dim_name)
            for source in dim.sources:
                rows.append({
                    "location": report.location,
                    "model": report.model_used,
                    "dimension": dim_name,
                    "dimension_summary": dim.summary,
                    "risk_score": dim.risk_score,
                    "confidence": dim.confidence,
                    "source_title": source.title,
                    "source_url": source.url,
                    "excerpt": source.excerpt,
                    "validation_status": source.validation_status.value,
                    "validation_detail": source.validation_detail,
                    "fetched_at": source.fetched_at.isoformat() if source.fetched_at else "",
                    "self_critique": dim.self_critique,
                    "latency_ms": report.latency_ms,
                    "cost_usd": report.cost_usd,
                    "timestamp": report.timestamp.isoformat(),
                })
    return pd.DataFrame(rows)


def write_csv(reports: List[LocationReport], path: Path) -> None:
    df = reports_to_dataframe(reports)
    df.to_csv(path, index=False, encoding="utf-8")
