from pathlib import Path

import pytest

import api_collector.exceptions as exceptions
import api_collector.models as models
import api_collector.parsers as parsers
from api_collector.main import validate_sources


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
