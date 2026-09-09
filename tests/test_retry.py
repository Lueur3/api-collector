from collections.abc import Callable
from unittest.mock import AsyncMock, Mock, call

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


async def test_success_on_first_attempt(
    fake_source: Source, fake_response: SourceResponse, mock_sleep: AsyncMock
) -> None:

    mock_func = AsyncMock(return_value=fake_response)
    fake_session = Mock()

    decorated_func = retry(max_attempts=3, initial_delay=1.0)(mock_func)

    result = await decorated_func(fake_session, fake_source)

    assert result == fake_response
    assert mock_func.call_count == 1
    assert mock_sleep.call_count == 0


async def test_retry_then_success(
    mock_sleep: AsyncMock, fake_source: Source, fake_response: SourceResponse
) -> None:
    mock_func = AsyncMock(
        side_effect=[NetworkTimeoutError("Timeout Error"), fake_response]
    )
    fake_session = Mock()

    decorated_func = retry(max_attempts=3, initial_delay=1.0)(mock_func)

    result = await decorated_func(fake_session, fake_source)

    assert result == fake_response
    assert mock_func.call_count == 2
    assert mock_sleep.call_count == 1
    mock_sleep.assert_called_once_with(1.0)


async def test_exhausted_attempts(mock_sleep: AsyncMock, fake_source: Source) -> None:
    mock_func = AsyncMock(side_effect=NetworkConnectionError("Connection Error"))
    fake_session = Mock()

    decorated_func = retry(max_attempts=3, initial_delay=1.0)(mock_func)

    with pytest.raises(NetworkConnectionError):
        await decorated_func(fake_session, fake_source)

    assert mock_func.call_count == 3
    assert mock_sleep.call_count == 2
    assert mock_sleep.call_args_list == [call(1.0), call(2.0)]


@pytest.mark.parametrize(
    "status_code",
    [400, 401, 403, 404, 501],
)
async def test_non_retryable_error(
    mock_sleep: AsyncMock, fake_source: Source, status_code: int
) -> None:
    mock_func = AsyncMock(side_effect=NetworkHttpError(status_code=status_code))
    fake_session = Mock()

    decorated_func = retry(max_attempts=3, initial_delay=1.0)(mock_func)

    with pytest.raises(NetworkHttpError):
        await decorated_func(fake_session, fake_source)

    assert mock_func.call_count == 1
    assert mock_sleep.call_count == 0


async def test_exponential_delay_growth(
    mock_sleep: AsyncMock, fake_source: Source
) -> None:
    mock_func = AsyncMock(side_effect=RetryHttpError(status_code=429))
    fake_session = Mock()

    decorated_func = retry(max_attempts=4, initial_delay=1.0)(mock_func)

    with pytest.raises(RetryHttpError):
        await decorated_func(fake_session, fake_source)

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


async def test_one_attempt_success(
    mock_sleep: AsyncMock, fake_source: Source, fake_response: SourceResponse
) -> None:
    mock_func = AsyncMock(return_value=fake_response)
    fake_session = Mock()

    decorated_func = retry(max_attempts=1, initial_delay=1.0)(mock_func)

    result = await decorated_func(fake_session, fake_source)

    assert result == fake_response
    assert mock_func.call_count == 1
    assert mock_sleep.call_count == 0


async def test_one_attempt_fail(mock_sleep: AsyncMock, fake_source: Source) -> None:
    mock_func = AsyncMock(side_effect=NetworkTimeoutError("Timeout Error"))
    fake_session = Mock()

    decorated_func = retry(max_attempts=1, initial_delay=1.0)(mock_func)

    with pytest.raises(NetworkTimeoutError):
        await decorated_func(fake_session, fake_source)

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
async def test_retryable_exceptions_trigger_retry(
    mock_sleep: AsyncMock,
    fake_source: Source,
    fake_response: SourceResponse,
    exception_class: Callable[..., NetworkError],
    exc_args: tuple[object, ...],
    exc_kwargs: dict[str, object],
) -> None:
    exception_instance = exception_class(*exc_args, **exc_kwargs)

    mock_func = AsyncMock(side_effect=[exception_instance, fake_response])
    fake_session = Mock()

    decorated_func = retry(max_attempts=3, initial_delay=1.0)(mock_func)

    result = await decorated_func(fake_session, fake_source)

    assert result == fake_response
    assert mock_func.call_count == 2
    assert mock_sleep.call_count == 1
    mock_sleep.assert_called_once_with(1.0)


async def test_interrupt(mock_sleep: AsyncMock, fake_source: Source) -> None:
    mock_func = AsyncMock(side_effect=KeyboardInterrupt())
    fake_session = Mock()

    decorated_func = retry(max_attempts=3, initial_delay=1.0)(mock_func)

    with pytest.raises(KeyboardInterrupt):
        await decorated_func(fake_session, fake_source)

    assert mock_func.call_count == 1
    assert mock_sleep.call_count == 0


async def test_system_exit(mock_sleep: AsyncMock, fake_source: Source) -> None:
    mock_func = AsyncMock(side_effect=SystemExit())
    fake_session = Mock()

    decorated_func = retry(max_attempts=3, initial_delay=1.0)(mock_func)

    with pytest.raises(SystemExit):
        await decorated_func(fake_session, fake_source)

    assert mock_func.call_count == 1
    assert mock_sleep.call_count == 0


async def test_state_resets_between_calls(
    mock_sleep: AsyncMock, fake_source: Source, fake_response: SourceResponse
) -> None:
    mock_func = AsyncMock(
        side_effect=[
            NetworkTimeoutError("Timeout Error"),
            fake_response,
            fake_response,
        ]
    )
    fake_session = Mock()

    decorated_func = retry(max_attempts=2, initial_delay=1.0)(mock_func)

    result_1 = await decorated_func(fake_session, fake_source)

    result_2 = await decorated_func(fake_session, fake_source)

    assert result_1 == fake_response
    assert result_2 == fake_response

    assert mock_func.call_count == 3

    assert mock_sleep.call_count == 1
    mock_sleep.assert_called_once_with(1.0)
