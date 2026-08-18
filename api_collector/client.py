import requests

from api_collector import exceptions
from api_collector.models import Source, SourceResponse

MAX_LEN_RESPONSE = 2000


def truncate_response(raw_text: str) -> str:
    slice_length = MAX_LEN_RESPONSE // 2
    raw_data = (
        raw_text[:slice_length]
        + "\n\n... [TRUNCATED] ...\n\n"
        + raw_text[-slice_length:]
    )

    return raw_data


def get_request(api_source: Source) -> SourceResponse:

    try:
        try:
            response = requests.get(api_source.url, timeout=api_source.timeout)
        except requests.exceptions.Timeout as e:
            raise exceptions.NetworkTimeoutError(
                f"Timeout during loading '{api_source.url}'"
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise exceptions.NetworkConnectionError(
                f"Unable to connect to '{api_source.url}'"
            ) from e

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            try:
                raw_data = response.json()
            except requests.exceptions.JSONDecodeError:
                raw_data = response.text
                if len(raw_data) > MAX_LEN_RESPONSE:
                    raw_data = truncate_response(raw_data)

            raise exceptions.NetworkHttpError(
                status_code=response.status_code, raw=raw_data
            ) from e

        try:
            data_response = response.json()
        except requests.exceptions.JSONDecodeError as e:
            raw_data = response.text
            if len(raw_data) > MAX_LEN_RESPONSE:
                raw_data = truncate_response(raw_data)
            raise exceptions.RequestError(
                message="An unsuitable answer option has been received.",
                status_code=response.status_code,
                raw=raw_data,
            ) from e

    except requests.RequestException as e:
        raise exceptions.NetworkError("Unexpected network error.") from e

    sr = SourceResponse(
        name=api_source.name, response=data_response, status_code=response.status_code
    )

    return sr
