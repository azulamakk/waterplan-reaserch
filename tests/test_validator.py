import pytest
from waterplan.models.schemas import FetchResult, ValidationStatus
from waterplan.validation.validator import validate_excerpt


def test_exact_match(good_fetch):
    result = validate_excerpt(
        "Mexicali municipality faces extremely high baseline water stress",
        good_fetch,
    )
    assert result.status == ValidationStatus.MATCH


def test_fuzzy_match(good_fetch):
    # Slightly modified excerpt — should still match via fuzzy
    result = validate_excerpt(
        "Mexicali faces extremely high baseline water stress",
        good_fetch,
    )
    assert result.status == ValidationStatus.MATCH


def test_failed_on_404(failed_fetch):
    result = validate_excerpt("any excerpt", failed_fetch)
    assert result.status == ValidationStatus.FAILED
    assert "404" in result.detail or "not reachable" in result.detail.lower()


def test_failed_on_empty_page(empty_fetch):
    result = validate_excerpt("any excerpt", empty_fetch)
    assert result.status == ValidationStatus.FAILED


def test_failed_on_nonexistent_text(good_fetch):
    result = validate_excerpt(
        "This text does not appear anywhere in the page content at all",
        good_fetch,
    )
    assert result.status == ValidationStatus.FAILED


def test_failed_fetch_result():
    fetch = FetchResult(
        text_content="",
        status_code=0,
        final_url="https://example.com",
        method_used="failed",
        error="Connection timeout",
    )
    result = validate_excerpt("any text", fetch)
    assert result.status == ValidationStatus.FAILED
    assert "timeout" in result.detail.lower() or "not reachable" in result.detail.lower()
