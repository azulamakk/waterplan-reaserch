from __future__ import annotations

from typing import Dict, List, Optional

from waterplan.models.schemas import (
    DimensionResult,
    LocationReport,
    ModelComparisonResult,
    ModelScore,
    ValidationStatus,
)
from waterplan.search.query_builder import DIMENSION_EMOJIS, DIMENSION_LABELS


def _format_dimension(dim: DimensionResult) -> str:
    label = DIMENSION_LABELS.get(dim.dimension, dim.dimension.title())
    emoji = DIMENSION_EMOJIS.get(dim.dimension, "•")
    lines = [f"## {emoji} {label}\n"]
    lines.append(f"**Summary:** {dim.summary}\n")

    if dim.risk_score is not None:
        lines.append(f"**Risk Score:** {dim.risk_score:.1f} / 10\n")

    if dim.confidence:
        lines.append(f"**Confidence:** {dim.confidence:.0%}\n")

    lines.append("### Sources\n")
    for i, source in enumerate(dim.sources, 1):
        icon = source.status_icon()
        lines.append(f"**{i}. {icon}**")
        lines.append(f"- **Title:** {source.title}")
        lines.append(f"- **URL:** {source.url}")
        lines.append(f'- **Excerpt:** "{source.excerpt[:350]}"')
        lines.append(f"- **Validation:** {source.validation_detail}")
        if source.fetched_at:
            lines.append(f"- **Fetched at:** {source.fetched_at.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("")

    if dim.self_critique:
        lines.append(f"**Self-Critique:** {dim.self_critique}\n")

    return "\n".join(lines)


def format_report(report: LocationReport) -> str:
    cost_str = f"${report.cost_usd:.4f}" if report.cost_usd else "N/A (local model)"
    latency_str = f"{report.latency_ms / 1000:.1f}s"

    header = (
        f"# 📍 {report.location}\n\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| Model | `{report.model_used}` |\n"
        f"| Generated | {report.timestamp.strftime('%Y-%m-%d %H:%M UTC')} |\n"
        f"| Latency | {latency_str} |\n"
        f"| Cost | {cost_str} |\n"
        f"| Sources Validated | {report.total_sources()} |\n"
        f"| Overall Pass Rate | {report.overall_pass_rate():.0%} |\n\n"
        f"---\n"
    )

    body = "\n---\n\n".join([
        _format_dimension(report.water_stress),
        _format_dimension(report.incidents),
        _format_dimension(report.regulations),
    ])

    return header + "\n" + body


def format_comparison_table(comparison: ModelComparisonResult) -> str:
    scores = comparison.scores
    if not scores:
        return "_No model comparison data available._\n"

    lines = ["## 🤖 Model Comparison\n"]
    lines.append(
        "| Model | Pass Rate | Relevance | Sources | Latency | Cost | Score |"
    )
    lines.append(
        "|-------|-----------|-----------|---------|---------|------|-------|"
    )
    for model_id, s in sorted(scores.items(), key=lambda x: x[1].overall_score, reverse=True):
        cost = f"${s.cost_usd:.4f}" if s.cost_usd is not None else "free"
        lines.append(
            f"| `{model_id}` "
            f"| {s.validation_pass_rate:.1f}% "
            f"| {s.avg_source_relevance:.1f}/10 "
            f"| {int(s.source_count)} "
            f"| {s.latency_ms / 1000:.1f}s "
            f"| {cost} "
            f"| **{s.overall_score:.1f}** |"
        )
    return "\n".join(lines) + "\n"


def format_full_comparison(comparison: ModelComparisonResult) -> str:
    parts = [f"# 📍 {comparison.location} — Multi-Model Comparison\n\n"]
    parts.append(format_comparison_table(comparison))
    parts.append("\n---\n\n")
    for model_id, report in comparison.results.items():
        parts.append(f"## Results: `{model_id}`\n")
        parts.append(format_report(report))
        parts.append("\n---\n\n")
    return "".join(parts)
