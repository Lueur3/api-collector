import logging
from collections.abc import Callable
from functools import wraps
from time import sleep
from types import TracebackType
from typing import Any, Literal, Self

import requests

from api_collector import exceptions
from api_collector.models import Source, SourceResponse

MAX_LEN_RESPONSE = 2000
RETRY_CODES = 429, 500, 502, 503, 504

RequestFunc = Callable[[requests.Session, Source], SourceResponse]

logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 2, initial_delay: float = 1
) -> Callable[[RequestFunc], RequestFunc]:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if initial_delay <= 0:
        raise ValueError("initial_delay must be > 0")

    def decorator(
        func: RequestFunc,
    ) -> RequestFunc:

        @wraps(func)
        def wrapper(
            req_session: requests.Session, api_source: Source
        ) -> SourceResponse:

            attempts_left = max_attempts
            current_delay = initial_delay
            source_name = api_source.name

            logger.info("Starting request for source '%s'", source_name)
            logger.debug(
                "max attempts: %s, initial delay: %ss", max_attempts, initial_delay
            )

            while attempts_left > 0:
                attempt_number = max_attempts - attempts_left + 1
                try:
                    logger.debug("Attempt %s of %s", attempt_number, max_attempts)

                    result = func(req_session, api_source)
                    logger.info("Attempt %s succeeded", attempt_number)

                    return result

                except (
                    exceptions.NetworkTimeoutError,
                    exceptions.NetworkConnectionError,
                    exceptions.RetryHttpError,
                ) as e:
                    attempts_left -= 1
                    if attempts_left > 0:
                        logger.warning(
                            "Retryable error on attempt %s: %s. Next retry in %ss",
                            attempt_number,
                            e,
                            current_delay,
                        )
                        sleep(current_delay)
                        current_delay *= 2
                    else:
                        logger.warning(
                            "Attempt %s failed with retryable error: %s",
                            attempt_number,
                            e,
                        )
                        raise

            raise RuntimeError("Unexpected exit from retry loop")

        return wrapper

    return decorator


def truncate_response(raw_text: str) -> str:
    if len(raw_text) <= MAX_LEN_RESPONSE:
        return raw_text
    slice_length = MAX_LEN_RESPONSE // 2
    raw_data = (
        raw_text[:slice_length]
        + "\n\n... [TRUNCATED] ...\n\n"
        + raw_text[-slice_length:]
    )

    return raw_data


def get_data(response: requests.models.Response) -> dict[str, Any] | str:
    raw_data: dict[str, Any] | str
    try:
        raw_data = response.json()
    except requests.exceptions.JSONDecodeError:
        raw_data = truncate_response(response.text)

    return raw_data


class CollectorClient:
    def __init__(self) -> None:
        self.req_session = requests.Session()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        self.req_session.close()
        return False

    def fetch_source(self, api_source: Source) -> SourceResponse:
        return get_request(self.req_session, api_source)


@retry()
def get_request(session: requests.Session, api_source: Source) -> SourceResponse:
    try:
        response = session.get(api_source.url, timeout=api_source.timeout)
    except requests.exceptions.Timeout as e:
        raise exceptions.NetworkTimeoutError(
            f"Timeout during loading '{api_source.url}'"
        ) from e
    except requests.exceptions.ConnectionError as e:
        raise exceptions.NetworkConnectionError(
            f"Unable to connect to '{api_source.url}'"
        ) from e
    except requests.RequestException as e:
        raise exceptions.NetworkError("Unexpected network error.") from e

    try:
        response.raise_for_status()
        data_response = response.json()
    except requests.exceptions.HTTPError as e:
        raw_data = get_data(response)

        if response.status_code in RETRY_CODES:
            raise exceptions.RetryHttpError(
                status_code=response.status_code, raw=raw_data
            ) from e
        else:
            raise exceptions.NetworkHttpError(
                status_code=response.status_code, raw=raw_data
            ) from e

    except requests.exceptions.JSONDecodeError as e:
        raw_data = truncate_response(response.text)
        raise exceptions.RequestError(
            message="An unsuitable answer option has been received.",
            status_code=response.status_code,
            raw=raw_data,
        ) from e

    except requests.RequestException as e:
        raise exceptions.NetworkError("Unexpected network error.") from e

    sr = SourceResponse(
        name=api_source.name,
        response=data_response,
        status_code=response.status_code,
    )

    return sr
