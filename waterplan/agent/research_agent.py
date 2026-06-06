from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from waterplan.agent.prompts import SYSTEM_PROMPT
from waterplan.agent.self_critic import avg_relevance, critique_sources
from waterplan.agent.tools import make_tools
from waterplan.models.schemas import (
    DimensionResult,
    LocationReport,
    Source,
    ValidationStatus,
)

_COST_PER_1K = {
    "claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
    "claude-haiku-4-5-20251001": {"input": 0.00025, "output": 0.00125},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-5-mini": {"input": 0.00015, "output": 0.0006},
}


def _estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    rates = _COST_PER_1K.get(model_id)
    if not rates:
        return None
    return (input_tokens / 1000) * rates["input"] + (output_tokens / 1000) * rates["output"]


def _run_langgraph_agent(
    model: BaseChatModel,
    tools: list,
    user_message: str,
    verbose: bool = False,
) -> dict:
    """Run agent using LangGraph's create_react_agent (modern LangChain 0.3+ / 1.x approach)."""
    from langgraph.prebuilt import create_react_agent

    graph = create_react_agent(
        model,
        tools,
        prompt=SystemMessage(content=SYSTEM_PROMPT),
    )

    result = graph.invoke(
        {"messages": [HumanMessage(content=user_message)]},
        config={"recursion_limit": 60},
    )

    if verbose:
        for msg in result.get("messages", []):
            print(f"[{type(msg).__name__}] {getattr(msg, 'content', '')[:200]}")

    return result


def _build_dimension_result(
    dimension: str,
    sources: List[Source],
    summaries: Dict[str, Any],
    location: str,
    use_cache: bool = True,
) -> DimensionResult:
    summary = summaries.get(dimension, "No summary available.")
    confidence_base = summaries.get("confidence", 0.5)

    if sources:
        pass_rate = sum(
            1 for s in sources if s.validation_status == ValidationStatus.MATCH
        ) / len(sources)
        confidence = confidence_base * pass_rate
    else:
        confidence = 0.0

    critiques = critique_sources(location, dimension, sources, use_cache=use_cache)
    avg_score = avg_relevance(critiques)
    critique_text = (
        f"Avg source relevance: {avg_score:.1f}/10. "
        + "; ".join(c.suggestion for c in critiques[:2] if c.suggestion)
    ) if critiques else "No critique available."

    risk_score = None
    if dimension == "water_stress" and sources:
        for s in sources:
            m = re.search(r"(\d+\.?\d*)\s*/\s*5", s.excerpt)
            if m:
                risk_score = round(float(m.group(1)) * 2, 1)
                break

    return DimensionResult(
        dimension=dimension,
        summary=summary,
        risk_score=risk_score,
        sources=sources,
        self_critique=critique_text,
        confidence=round(confidence, 2),
    )


def _generate_summaries_fallback(
    model: BaseChatModel, location: str, findings: dict
) -> dict:
    """Synthesize dimension summaries directly when the agent skipped finish_research."""
    dim_labels = {
        "water_stress": "water stress, scarcity, and physical water availability",
        "incidents": "water-related incidents, crises, protests, and conflicts",
        "regulations": "water regulations, industrial permits, and compliance requirements",
    }
    result: dict = {"confidence": 0.6}
    for dim, label in dim_labels.items():
        sources = findings.get(dim, [])
        if not sources:
            result[dim] = "No data available for this dimension."
            continue
        excerpts = "\n".join(f"- {s.excerpt}" for s in sources[:3])
        prompt = (
            f"Based ONLY on these verified source excerpts about {label} for {location}, "
            f"write a 2-3 sentence factual summary. Do not speculate beyond the excerpts.\n\n"
            f"{excerpts}\n\nSummary:"
        )
        try:
            response = model.invoke([HumanMessage(content=prompt)])
            result[dim] = response.content.strip()
        except Exception:
            result[dim] = "No summary available."
    return result


def _count_tokens_from_messages(messages: list) -> tuple[int, int]:
    """Rough token count from LangGraph message list for cost estimation."""
    input_tokens = 0
    output_tokens = 0
    for msg in messages:
        content = getattr(msg, "content", "") or ""
        tokens = len(str(content)) // 4  # rough 4 chars/token estimate
        if isinstance(msg, (HumanMessage, SystemMessage)):
            input_tokens += tokens
        elif isinstance(msg, AIMessage):
            output_tokens += tokens
    return input_tokens, output_tokens


def research_location(
    location: str,
    model: BaseChatModel,
    model_id: str = "unknown",
    use_cache: bool = True,
    verbose: bool = False,
) -> LocationReport:
    findings: Dict[str, Any] = {
        "water_stress": [],
        "incidents": [],
        "regulations": [],
    }

    tools = make_tools(findings, use_cache=use_cache)

    user_message = (
        f"Research all three water risk dimensions for this industrial location: {location}\n"
        "You MUST find at least 2 validated sources per dimension before finishing.\n"
        "Workflow: search_water_risk → fetch_and_validate → record_finding (per source) → finish_research"
    )

    start = time.monotonic()

    result = _run_langgraph_agent(model, tools, user_message, verbose=verbose)

    elapsed_ms = (time.monotonic() - start) * 1000

    # If the agent exited without calling finish_research (common with smaller models),
    # synthesize summaries directly from the collected source excerpts.
    raw_summaries = findings.get("__summaries__", {})
    if not raw_summaries or not any(
        raw_summaries.get(d) for d in ("water_stress", "incidents", "regulations")
    ):
        findings["__summaries__"] = _generate_summaries_fallback(model, location, findings)

    # Estimate cost from message content
    messages = result.get("messages", [])
    input_tokens, output_tokens = _count_tokens_from_messages(messages)
    cost = _estimate_cost(model_id, input_tokens, output_tokens)

    summaries = findings.get("__summaries__", {})

    water_stress = _build_dimension_result(
        "water_stress", findings.get("water_stress", []), summaries, location, use_cache
    )
    incidents = _build_dimension_result(
        "incidents", findings.get("incidents", []), summaries, location, use_cache
    )
    regulations = _build_dimension_result(
        "regulations", findings.get("regulations", []), summaries, location, use_cache
    )

    return LocationReport(
        location=location,
        timestamp=datetime.now(timezone.utc),
        water_stress=water_stress,
        incidents=incidents,
        regulations=regulations,
        model_used=model_id,
        latency_ms=round(elapsed_ms, 1),
        cost_usd=cost,
    )
