from pathlib import Path
from typing import Any

import pytest

import api_collector.exceptions as exceptions
from api_collector.config import read_config


def test_read_valid_config(tmp_path: Path) -> None:
    content = """\
    [[API]]
    name = "TestApi"
    URL = "https://example.com"
    timeout = 5
    """

    config_file = tmp_path / "config.toml"
    config_file.write_text(content, encoding="utf-8")

    result = read_config(config_file)

    assert len(result) == 1
    assert result[0].name == "TestApi"
    assert result[0].url == "https://example.com"
    assert result[0].timeout == 5


def test_read_multiple_sources(tmp_path: Path) -> None:
    content = """\
        [[API]]
        name = "TestApi"
        URL = "https://example.com"
        timeout = 5
        [[API]]
        name = "AnotherApi"
        URL = "https://test-url.com"
        timeout = 2
    """

    config_file = tmp_path / "config.toml"
    config_file.write_text(content, encoding="utf-8")

    result = read_config(config_file)

    assert result[0].name == "TestApi"
    assert result[0].url == "https://example.com"
    assert result[0].timeout == 5

    assert result[1].name == "AnotherApi"
    assert result[1].url == "https://test-url.com"
    assert result[1].timeout == 2


def test_invalid_toml(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("this is not [valid TOML", encoding="utf-8")

    with pytest.raises(exceptions.ConfigDecodeError) as exc_info:
        read_config(config_file)

    assert exc_info.value.config_path == config_file


def test_missing_required_key(tmp_path: Path) -> None:
    content = """\
        [[API]]
        URL = "https://example.com"
        """
    config_file = tmp_path / "config.toml"
    config_file.write_text(content, encoding="utf-8")

    with pytest.raises(exceptions.ConfigIncorrect) as exc_info:
        read_config(config_file)

    assert exc_info.value.config_path == config_file


def test_invalid_source_data(tmp_path: Path) -> None:
    content = """\
        [[API]]
        name = ""
        URL = "https://example.com"
        timeout = 5
        """
    config_file = tmp_path / "config.toml"
    config_file.write_text(content, encoding="utf-8")

    with pytest.raises(exceptions.ConfigIncorrect) as exc_info:
        read_config(config_file)

    assert exc_info.value.config_path == config_file


def test_missing_file(tmp_path: Path) -> None:
    nonexistent = tmp_path / "nonexistent.toml"

    with pytest.raises(exceptions.ConfigFileError) as exc_info:
        read_config(nonexistent)

    assert exc_info.value.config_path == nonexistent


def test_permission_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("[[API]]\nname = 'x'\nURL = 'y'\n", encoding="utf-8")

    def mock_open(*args: Any, **kwargs: Any) -> Any:
        raise PermissionError("No permission")

    monkeypatch.setattr("builtins.open", mock_open)

    with pytest.raises(exceptions.ConfigPermissionError) as exc_info:
        read_config(config_file)

    assert exc_info.value.config_path == config_file


def test_unexpected_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("[[API]]\nname = 'x'\nURL = 'y'\n", encoding="utf-8")

    def mock_load(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("something unexpected")

    monkeypatch.setattr("api_collector.config.tomllib.load", mock_load)

    with pytest.raises(exceptions.ConfigError) as exc_info:
        read_config(config_file)

    assert exc_info.value.config_path == config_file
