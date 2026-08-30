from unittest.mock import Mock

import pytest
import requests

from api_collector import exceptions
from api_collector.client import get_request
from api_collector.models import Source

original_get_request = get_request.__wrapped__  # type: ignore[attr-defined]


@pytest.fixture
def mock_session() -> Mock:
    return Mock(spec=requests.Session)


@pytest.fixture
def mock_response() -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"key": "value"}
    response.text = ""
    response.raise_for_status = Mock()
    return response


def test_successful_response(
    mock_session: Mock, mock_response: Mock, fake_source: Source
) -> None:
    mock_session.get.return_value = mock_response
    result = original_get_request(mock_session, fake_source)

    assert result.name == fake_source.name
    assert result.status_code == mock_response.status_code
    assert result.response == mock_response.json.return_value


def test_timeout_error(mock_session: Mock, fake_source: Source) -> None:
    mock_session.get.side_effect = requests.exceptions.Timeout()
    with pytest.raises(exceptions.NetworkTimeoutError) as exc_info:
        original_get_request(mock_session, fake_source)

    assert str(exc_info.value) == f"Timeout during loading '{fake_source.url}'"
    assert isinstance(exc_info.value.__cause__, requests.exceptions.Timeout)


def test_connection_error(mock_session: Mock, fake_source: Source) -> None:
    mock_session.get.side_effect = requests.exceptions.ConnectionError()
    with pytest.raises(exceptions.NetworkConnectionError) as exc_info:
        original_get_request(mock_session, fake_source)

    assert str(exc_info.value) == f"Unable to connect to '{fake_source.url}'"
    assert isinstance(exc_info.value.__cause__, requests.exceptions.ConnectionError)


@pytest.mark.parametrize("status_code", [429, 500, 502, 503, 504])
def test_retryable_http_error(
    mock_session: Mock, mock_response: Mock, fake_source: Source, status_code: int
) -> None:
    mock_response.status_code = status_code
    mock_session.get.return_value = mock_response
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
    mock_response.json.return_value = {"error": "too many requests"}

    with pytest.raises(exceptions.RetryHttpError) as exc_info:
        original_get_request(mock_session, fake_source)

    assert exc_info.value.status_code == status_code
    assert str(exc_info.value) == f"HTTP status: {status_code}"
    assert exc_info.value.raw == {"error": "too many requests"}
    assert isinstance(exc_info.value.__cause__, requests.exceptions.HTTPError)


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 501])
def test_non_retryable_http_error(
    mock_session: Mock, mock_response: Mock, fake_source: Source, status_code: int
) -> None:
    mock_response.status_code = status_code
    mock_session.get.return_value = mock_response
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
    mock_response.json.return_value = {"error": "client error"}

    with pytest.raises(exceptions.NetworkHttpError) as exc_info:
        original_get_request(mock_session, fake_source)

    assert type(exc_info.value) is exceptions.NetworkHttpError
    assert exc_info.value.status_code == status_code
    assert str(exc_info.value) == f"HTTP status: {status_code}"
    assert exc_info.value.raw == {"error": "client error"}
    assert isinstance(exc_info.value.__cause__, requests.exceptions.HTTPError)


def test_json_decode_error(
    mock_session: Mock, mock_response: Mock, fake_source: Source
) -> None:
    mock_session.get.return_value = mock_response
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError(
        "Expecting value", "", 0
    )
    mock_response.text = "<html>not a json</html>"

    with pytest.raises(exceptions.RequestError) as exc_info:
        original_get_request(mock_session, fake_source)

    assert type(exc_info.value) is exceptions.RequestError
    assert str(exc_info.value) == "An unsuitable answer option has been received."
    assert exc_info.value.raw == mock_response.text
    assert exc_info.value.status_code == mock_response.status_code
    assert isinstance(exc_info.value.__cause__, requests.exceptions.JSONDecodeError)
