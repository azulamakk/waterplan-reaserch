from __future__ import annotations

from typing import Dict, List

QUERY_TEMPLATES: Dict[str, List[str]] = {
    "water_stress": [
        "{location} water stress scarcity physical risk score availability index",
        "{location} water shortage drought industrial water supply risk assessment",
    ],
    "incidents": [
        "{location} water protest strike crisis conflict 2022 2023 2024",
        "{location} water shortage dispute community industrial water conflict news",
    ],
    "regulations": [
        "{location} industrial water use regulations permit requirements law",
        "{location} water discharge environmental compliance factory regulations",
    ],
}

DIMENSION_LABELS = {
    "water_stress": "Water Stress",
    "incidents": "Incidents & Conflicts",
    "regulations": "Regulations",
}

DIMENSION_EMOJIS = {
    "water_stress": "💧",
    "incidents": "⚠️",
    "regulations": "📋",
}


def build_queries(location: str, dimension: str) -> List[str]:
    templates = QUERY_TEMPLATES.get(dimension, [])
    return [t.format(location=location) for t in templates]


def all_queries(location: str) -> Dict[str, List[str]]:
    return {dim: build_queries(location, dim) for dim in QUERY_TEMPLATES}
