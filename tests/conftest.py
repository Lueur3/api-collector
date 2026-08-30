import pytest

from api_collector.models import Source, SourceResponse


@pytest.fixture
def fake_source() -> Source:
    return Source(name="test_source", url="https://example.com", timeout=5)


@pytest.fixture
def fake_response() -> SourceResponse:
    return SourceResponse(name="test_source", response={"ok": True}, status_code=200)
