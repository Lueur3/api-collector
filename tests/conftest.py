from unittest.mock import AsyncMock

import pytest

from api_collector.models import Source, SourceResponse


@pytest.fixture
async def fake_source() -> Source:
    return Source(name="test_source", url="https://example.com", timeout=5)


@pytest.fixture
async def fake_response() -> SourceResponse:
    return SourceResponse(name="test_source", response={"ok": True}, status_code=200)


@pytest.fixture
def mock_sleep(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock = AsyncMock()
    monkeypatch.setattr("api_collector.client.asyncio.sleep", mock)
    return mock
