import pytest
from waterplan.models.schemas import FetchResult, ValidationStatus


@pytest.fixture
def good_fetch():
    return FetchResult(
        text_content="Mexicali municipality faces extremely high baseline water stress according to the WRI Aqueduct tool.",
        status_code=200,
        final_url="https://example.com",
        method_used="httpx",
    )


@pytest.fixture
def failed_fetch():
    return FetchResult(
        text_content="",
        status_code=404,
        final_url="https://example.com/notfound",
        method_used="failed",
        error="404 Not Found",
    )


@pytest.fixture
def empty_fetch():
    return FetchResult(
        text_content="",
        status_code=200,
        final_url="https://example.com",
        method_used="httpx",
    )
