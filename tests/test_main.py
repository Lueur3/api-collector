import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

import api_collector.exceptions as exceptions
import api_collector.models as models
import api_collector.parsers as parsers
from api_collector.client import CollectorClient
from api_collector.main import processing_source, validate_sources


def test_validate_sources_all_known(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parsers, "PARSE_SOURCES", {"JokeApi": None, "BoredApi": None})

    sources = [
        models.Source(name="JokeApi", url="https://example.com"),
        models.Source(name="BoredApi", url="https://example.com"),
    ]

    validate_sources(sources, Path("config.toml"))


def test_validate_sources_unknown_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parsers, "PARSE_SOURCES", {"JokeApi": None})

    sources = [
        models.Source(name="JokeApi", url="https://example.com"),
        models.Source(name="UnknownApi", url="https://example.com"),
    ]
    config_path = Path("config.toml")

    with pytest.raises(exceptions.ConfigIncorrect) as exc_info:
        validate_sources(sources, config_path)

    assert "UnknownApi" in exc_info.value.message
    assert exc_info.value.config_path == config_path


@pytest.mark.parametrize("unknown_name", ["Foo", "Bar", "TypoApi"])
def test_validate_sources_various_unknown_names(
    unknown_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(parsers, "PARSE_SOURCES", {"JokeApi": None})

    sources = [models.Source(name=unknown_name, url="https://example.com")]

    with pytest.raises(exceptions.ConfigIncorrect):
        validate_sources(sources, Path("config.toml"))


async def test_processing_source_timeout(
    monkeypatch: pytest.MonkeyPatch, fake_source: models.Source
) -> None:
    timeout = 0.05
    monkeypatch.setattr("api_collector.main.SOURCE_TIMEOUT", timeout)

    async def slow_fetch(source: models.Source) -> models.SourceResponse:
        await asyncio.sleep(10)
        raise AssertionError("fetch_source finished before the timeout")

    client = Mock(spec=CollectorClient)
    client.fetch_source = AsyncMock(side_effect=slow_fetch)

    result = await processing_source(client, fake_source)

    assert isinstance(result, models.SourceFailure)
    assert result.name == fake_source.name
    assert result.status_code is None
    assert result.raw is None
    assert len(result.errors) == 1
    assert f"timed out (limit: {timeout}s)" in result.errors[0]
    client.fetch_source.assert_awaited_once_with(fake_source)
