from collections.abc import Callable
from unittest.mock import Mock, call

import pytest

from api_collector.client import retry
from api_collector.exceptions import (
    NetworkConnectionError,
    NetworkError,
    NetworkHttpError,
    NetworkTimeoutError,
    RetryHttpError,
)
from api_collector.models import Source, SourceResponse


@pytest.fixture
def fake_source() -> Source:
    return Source(name="test_source", url="https://example.com", timeout=5)


@pytest.fixture
def fake_response() -> SourceResponse:
    return SourceResponse(name="test_source", response={"ok": True}, status_code=200)


def test_success_on_first_attempt(
    monkeypatch: pytest.MonkeyPatch, fake_source: Source, fake_response: SourceResponse
) -> None:

    mock_func = Mock(return_value=fake_response)
    mock_sleep = Mock()
    monkeypatch.setattr("api_collector.client.sleep", mock_sleep)

    decorated_func = retry(max_attempts=3, initial_delay=1.0)(mock_func)

    result = decorated_func(fake_source)

    assert result == fake_response
    assert mock_func.call_count == 1
    assert mock_sleep.call_count == 0


def test_retry_then_success(
    monkeypatch: pytest.MonkeyPatch, fake_source: Source, fake_response: SourceResponse
) -> None:
    mock_func = Mock(side_effect=[NetworkTimeoutError("Timeout Error"), fake_response])
    mock_sleep = Mock()
    monkeypatch.setattr("api_collector.client.sleep", mock_sleep)

    decorated_func = retry(max_attempts=3, initial_delay=1.0)(mock_func)

    result = decorated_func(fake_source)

    assert result == fake_response
    assert mock_func.call_count == 2
    assert mock_sleep.call_count == 1
    mock_sleep.assert_called_once_with(1.0)


def test_exhausted_attempts(
    monkeypatch: pytest.MonkeyPatch, fake_source: Source
) -> None:
    mock_func = Mock(side_effect=NetworkConnectionError("Connection Error"))
    mock_sleep = Mock()
    monkeypatch.setattr("api_collector.client.sleep", mock_sleep)
    decorated_func = retry(max_attempts=3, initial_delay=1.0)(mock_func)

    with pytest.raises(NetworkConnectionError):
        decorated_func(fake_source)

    assert mock_func.call_count == 3
    assert mock_sleep.call_count == 2
    assert mock_sleep.call_args_list == [call(1.0), call(2.0)]


@pytest.mark.parametrize(
    "status_code",
    [400, 401, 403, 404, 501],
)
def test_non_retryable_error(
    monkeypatch: pytest.MonkeyPatch, fake_source: Source, status_code: int
) -> None:
    mock_func = Mock(side_effect=NetworkHttpError(status_code=status_code))
    mock_sleep = Mock()
    monkeypatch.setattr("api_collector.client.sleep", mock_sleep)
    decorated_func = retry(max_attempts=3, initial_delay=1.0)(mock_func)

    with pytest.raises(NetworkHttpError):
        decorated_func(fake_source)

    assert mock_func.call_count == 1
    assert mock_sleep.call_count == 0


def test_exponential_delay_growth(
    monkeypatch: pytest.MonkeyPatch, fake_source: Source
) -> None:
    mock_func = Mock(side_effect=RetryHttpError(status_code=429))
    mock_sleep = Mock()
    monkeypatch.setattr("api_collector.client.sleep", mock_sleep)
    decorated_func = retry(max_attempts=4, initial_delay=1.0)(mock_func)

    with pytest.raises(RetryHttpError):
        decorated_func(fake_source)

    assert mock_func.call_count == 4
    assert mock_sleep.call_count == 3
    assert mock_sleep.call_args_list == [call(1.0), call(2.0), call(4.0)]


@pytest.mark.parametrize(
    "attempts",
    [
        -1,
        0,
    ],
)
def test_max_attempts(attempts: int) -> None:
    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        retry(max_attempts=attempts)


@pytest.mark.parametrize(
    "delay",
    [
        -1,
        0,
    ],
)
def test_delay(delay: int) -> None:
    with pytest.raises(ValueError, match="initial_delay must be > 0"):
        retry(initial_delay=delay)


def test_one_attempt_success(
    monkeypatch: pytest.MonkeyPatch, fake_source: Source, fake_response: SourceResponse
) -> None:
    mock_func = Mock(return_value=fake_response)
    mock_sleep = Mock()
    monkeypatch.setattr("api_collector.client.sleep", mock_sleep)
    decorated_func = retry(max_attempts=1, initial_delay=1.0)(mock_func)

    result = decorated_func(fake_source)

    assert result == fake_response
    assert mock_func.call_count == 1
    assert mock_sleep.call_count == 0


def test_one_attempt_fail(monkeypatch: pytest.MonkeyPatch, fake_source: Source) -> None:
    mock_func = Mock(side_effect=NetworkTimeoutError("Timeout Error"))
    mock_sleep = Mock()
    monkeypatch.setattr("api_collector.client.sleep", mock_sleep)
    decorated_func = retry(max_attempts=1, initial_delay=1.0)(mock_func)

    with pytest.raises(NetworkTimeoutError):
        decorated_func(fake_source)

    assert mock_func.call_count == 1
    assert mock_sleep.call_count == 0


@pytest.mark.parametrize(
    "exception_class, exc_args, exc_kwargs",
    [
        pytest.param(
            NetworkTimeoutError,
            ("Timeout Error",),
            {},
            id="NetworkTimeoutError",
        ),
        pytest.param(
            NetworkConnectionError,
            ("Connection Error",),
            {},
            id="NetworkConnectionError",
        ),
        pytest.param(
            RetryHttpError,
            (),
            {"status_code": 429, "raw": "some raw data"},
            id="RetryHttpError-429",
        ),
    ],
)
def test_retryable_exceptions_trigger_retry(
    monkeypatch: pytest.MonkeyPatch,
    fake_source: Source,
    fake_response: SourceResponse,
    exception_class: Callable[..., NetworkError],
    exc_args: tuple[object, ...],
    exc_kwargs: dict[str, object],
) -> None:
    exception_instance = exception_class(*exc_args, **exc_kwargs)

    mock_func = Mock(side_effect=[exception_instance, fake_response])
    mock_sleep = Mock()
    monkeypatch.setattr("api_collector.client.sleep", mock_sleep)

    decorated_func = retry(max_attempts=3, initial_delay=1.0)(mock_func)

    result = decorated_func(fake_source)

    assert result == fake_response
    assert mock_func.call_count == 2
    assert mock_sleep.call_count == 1
    mock_sleep.assert_called_once_with(1.0)


def test_interrupt(monkeypatch: pytest.MonkeyPatch, fake_source: Source) -> None:
    mock_func = Mock(side_effect=KeyboardInterrupt())
    mock_sleep = Mock()
    monkeypatch.setattr("api_collector.client.sleep", mock_sleep)

    decorated_func = retry(max_attempts=3, initial_delay=1.0)(mock_func)

    with pytest.raises(KeyboardInterrupt):
        decorated_func(fake_source)

    assert mock_func.call_count == 1
    assert mock_sleep.call_count == 0


def test_system_exit(monkeypatch: pytest.MonkeyPatch, fake_source: Source) -> None:
    mock_func = Mock(side_effect=SystemExit())
    mock_sleep = Mock()
    monkeypatch.setattr("api_collector.client.sleep", mock_sleep)

    decorated_func = retry(max_attempts=3, initial_delay=1.0)(mock_func)

    with pytest.raises(SystemExit):
        decorated_func(fake_source)

    assert mock_func.call_count == 1
    assert mock_sleep.call_count == 0


def test_state_resets_between_calls(
    monkeypatch: pytest.MonkeyPatch, fake_source: Source, fake_response: SourceResponse
) -> None:
    mock_func = Mock(
        side_effect=[
            NetworkTimeoutError("Timeout Error"),
            fake_response,
            fake_response,
        ]
    )
    mock_sleep = Mock()
    monkeypatch.setattr("api_collector.client.sleep", mock_sleep)

    decorated_func = retry(max_attempts=2, initial_delay=1.0)(mock_func)

    result_1 = decorated_func(fake_source)

    result_2 = decorated_func(fake_source)

    assert result_1 == fake_response
    assert result_2 == fake_response

    assert mock_func.call_count == 3

    assert mock_sleep.call_count == 1
    mock_sleep.assert_called_once_with(1.0)
