import asyncio
import json
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from api_collector import exceptions
from api_collector.client import get_request
from api_collector.models import Source

original_get_request = get_request.__wrapped__  # type: ignore[attr-defined]


@pytest.fixture
def mock_client() -> AsyncMock:
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def mock_response() -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"key": "value"}
    response.text = ""
    response.raise_for_status = Mock()
    return response


async def test_successful_response(
    mock_client: AsyncMock,
    mock_response: Mock,
    fake_source: Source,
    fake_semaphore: asyncio.Semaphore,
) -> None:
    mock_client.get.return_value = mock_response
    result = await original_get_request(mock_client, fake_source, fake_semaphore)

    assert result.name == fake_source.name
    assert result.status_code == mock_response.status_code
    assert result.response == mock_response.json.return_value


async def test_timeout_error(
    mock_client: AsyncMock, fake_source: Source, fake_semaphore: asyncio.Semaphore
) -> None:
    mock_client.get.side_effect = httpx.TimeoutException("Timeout Error")
    with pytest.raises(exceptions.NetworkTimeoutError) as exc_info:
        await original_get_request(mock_client, fake_source, fake_semaphore)

    assert str(exc_info.value) == f"Timeout during loading '{fake_source.url}'"
    assert isinstance(exc_info.value.__cause__, httpx.TimeoutException)


async def test_connection_error(
    mock_client: AsyncMock, fake_source: Source, fake_semaphore: asyncio.Semaphore
) -> None:
    mock_client.get.side_effect = httpx.ConnectError("Connection Error")
    with pytest.raises(exceptions.NetworkConnectionError) as exc_info:
        await original_get_request(mock_client, fake_source, fake_semaphore)

    assert str(exc_info.value) == f"Unable to connect to '{fake_source.url}'"
    assert isinstance(exc_info.value.__cause__, httpx.ConnectError)


@pytest.mark.parametrize("status_code", [429, 500, 502, 503, 504])
async def test_retryable_http_error(
    mock_client: AsyncMock,
    mock_response: Mock,
    fake_source: Source,
    status_code: int,
    fake_semaphore: asyncio.Semaphore,
) -> None:
    mock_response.status_code = status_code
    mock_client.get.return_value = mock_response
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="HTTPS Error", request=Mock(), response=mock_response
    )
    mock_response.json.return_value = {"error": "too many requests"}

    with pytest.raises(exceptions.RetryHttpError) as exc_info:
        await original_get_request(mock_client, fake_source, fake_semaphore)

    assert exc_info.value.status_code == status_code
    assert str(exc_info.value) == f"HTTP status: {status_code}"
    assert exc_info.value.raw == {"error": "too many requests"}
    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 501])
async def test_non_retryable_http_error(
    mock_client: AsyncMock,
    mock_response: Mock,
    fake_source: Source,
    status_code: int,
    fake_semaphore: asyncio.Semaphore,
) -> None:
    mock_response.status_code = status_code
    mock_client.get.return_value = mock_response
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="HTTPS Error", request=Mock(), response=mock_response
    )
    mock_response.json.return_value = {"error": "client error"}

    with pytest.raises(exceptions.NetworkHttpError) as exc_info:
        await original_get_request(mock_client, fake_source, fake_semaphore)

    assert type(exc_info.value) is exceptions.NetworkHttpError
    assert exc_info.value.status_code == status_code
    assert str(exc_info.value) == f"HTTP status: {status_code}"
    assert exc_info.value.raw == {"error": "client error"}
    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)


async def test_json_decode_error(
    mock_client: AsyncMock,
    mock_response: Mock,
    fake_source: Source,
    fake_semaphore: asyncio.Semaphore,
) -> None:
    mock_client.get.return_value = mock_response
    mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
    mock_response.text = "<html>not a json</html>"

    with pytest.raises(exceptions.RequestError) as exc_info:
        await original_get_request(mock_client, fake_source, fake_semaphore)

    assert type(exc_info.value) is exceptions.RequestError
    assert str(exc_info.value) == "An unsuitable answer option has been received."
    assert exc_info.value.raw == mock_response.text
    assert exc_info.value.status_code == mock_response.status_code
    assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)
