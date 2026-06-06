from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Tuple

from rapidfuzz import fuzz, utils as rfutils

from waterplan.models.schemas import FetchResult, ValidationStatus


@dataclass
class ValidationResult:
    status: ValidationStatus
    detail: str
    match_ratio: float = 0.0


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def _sliding_window_best_ratio(needle: str, haystack: str, window_size: int = 600) -> float:
    """Scan haystack with a sliding window and return the best fuzzy ratio.

    partial_ratio finds the best matching substring — correct for excerpt-in-page validation.
    token_set_ratio used as a fallback for word-order differences.
    """
    if len(haystack) <= window_size:
        return max(
            fuzz.partial_ratio(needle, haystack),
            fuzz.token_set_ratio(needle, haystack),
        )

    best = 0.0
    step = max(1, window_size // 2)
    for i in range(0, len(haystack) - window_size + 1, step):
        window = haystack[i : i + window_size]
        ratio = max(fuzz.partial_ratio(needle, window), fuzz.token_set_ratio(needle, window))
        if ratio > best:
            best = ratio
        if best >= 95:
            break
    return best


def validate_excerpt(excerpt: str, fetch_result: FetchResult) -> ValidationResult:
    if fetch_result.method_used == "failed" or fetch_result.status_code == 0:
        return ValidationResult(
            status=ValidationStatus.FAILED,
            detail=f"URL not reachable: {fetch_result.error or 'unknown error'}",
        )

    if fetch_result.status_code >= 400:
        return ValidationResult(
            status=ValidationStatus.FAILED,
            detail=f"URL returned HTTP {fetch_result.status_code}",
        )

    if not fetch_result.text_content.strip():
        return ValidationResult(
            status=ValidationStatus.FAILED,
            detail="Page returned empty content",
        )

    norm_excerpt = _normalize(excerpt)
    norm_content = _normalize(fetch_result.text_content)

    # Tier 1: exact substring
    if norm_excerpt in norm_content:
        return ValidationResult(
            status=ValidationStatus.MATCH,
            detail="Exact match found in page content",
            match_ratio=100.0,
        )

    # Tier 2: fuzzy sliding window
    ratio = _sliding_window_best_ratio(norm_excerpt, norm_content)
    if ratio >= 85:
        return ValidationResult(
            status=ValidationStatus.MATCH,
            detail=f"Fuzzy match found (similarity: {ratio:.1f}%)",
            match_ratio=ratio,
        )

    return ValidationResult(
        status=ValidationStatus.FAILED,
        detail=f"Excerpt not found in source content (best similarity: {ratio:.1f}%)",
        match_ratio=ratio,
    )
