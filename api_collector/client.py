from typing import Any

import requests

from api_collector import exceptions


def get_request(api_url: str, api_timeout: float) -> tuple[Any, int]:

    try:
        try:
            response = requests.get(api_url, timeout=api_timeout)
        except requests.exceptions.Timeout as e:
            raise exceptions.NetworkTimeoutError(
                f"Timeout during loading '{api_url}'"
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise exceptions.NetworkConnectionError(
                f"Unable to connect to '{api_url}'"
            ) from e

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            try:
                raw_data = response.json()
            except requests.exceptions.JSONDecodeError:
                raw_data = response.text
            raise exceptions.NetworkHttpError(
                status_code=response.status_code, raw=raw_data
            ) from e

        try:
            data_response = response.json()
        except requests.exceptions.JSONDecodeError as e:
            raise exceptions.RequestError(
                message="An unsuitable answer option has been received.",
                status_code=response.status_code,
                raw=response.text,
            ) from e

    except requests.RequestException as e:
        raise exceptions.NetworkError("Unexpected network error.") from e

    return (data_response, response.status_code)
