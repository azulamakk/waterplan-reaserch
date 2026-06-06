from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, field_validator


class ValidationStatus(str, Enum):
    MATCH = "MATCH_FOUND"
    FAILED = "FAILED_VALIDATION"
    PENDING = "PENDING"


class Source(BaseModel):
    url: str
    title: str
    excerpt: str
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validation_detail: str = ""
    fetched_at: Optional[datetime] = None

    def status_icon(self) -> str:
        if self.validation_status == ValidationStatus.MATCH:
            return "✅ MATCH FOUND"
        elif self.validation_status == ValidationStatus.FAILED:
            return "❌ FAILED VALIDATION"
        return "⏳ PENDING"


class DimensionResult(BaseModel):
    dimension: str
    summary: str
    risk_score: Optional[float] = None
    sources: List[Source] = []
    self_critique: str = ""
    confidence: float = 0.0

    def validation_pass_rate(self) -> float:
        if not self.sources:
            return 0.0
        passed = sum(1 for s in self.sources if s.validation_status == ValidationStatus.MATCH)
        return passed / len(self.sources)


class LocationReport(BaseModel):
    location: str
    timestamp: datetime
    water_stress: DimensionResult
    incidents: DimensionResult
    regulations: DimensionResult
    model_used: str
    latency_ms: float
    cost_usd: Optional[float] = None

    def overall_pass_rate(self) -> float:
        all_sources = (
            self.water_stress.sources
            + self.incidents.sources
            + self.regulations.sources
        )
        if not all_sources:
            return 0.0
        passed = sum(1 for s in all_sources if s.validation_status == ValidationStatus.MATCH)
        return passed / len(all_sources)

    def total_sources(self) -> int:
        return (
            len(self.water_stress.sources)
            + len(self.incidents.sources)
            + len(self.regulations.sources)
        )


class ModelScore(BaseModel):
    model_id: str
    validation_pass_rate: float
    avg_source_relevance: float
    source_count: float
    latency_ms: float
    cost_usd: Optional[float]
    overall_score: float


class ModelComparisonResult(BaseModel):
    location: str
    results: Dict[str, LocationReport]
    scores: Dict[str, ModelScore]


class SearchResult(BaseModel):
    url: str
    title: str
    snippet: str


class FetchResult(BaseModel):
    text_content: str
    status_code: int
    final_url: str
    method_used: str  # "httpx" | "playwright" | "failed"
    error: Optional[str] = None


class CritiqueResult(BaseModel):
    relevance: float  # 0-10
    recency: str  # "current" | "dated" | "unknown"
    authority: str  # "government" | "academic" | "news" | "blog" | "other"
    suggestion: str
    overall_score: float  # 0-10
