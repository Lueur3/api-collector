from pathlib import Path
from typing import Any


class CollectorError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


# network exceptions
class NetworkError(CollectorError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        raw: dict[str, Any] | str | None = None,
    ) -> None:
        self.status_code = status_code
        self.raw = raw
        super().__init__(message)


class NetworkTimeoutError(NetworkError):
    pass


class NetworkConnectionError(NetworkError):
    pass


class NetworkHttpError(NetworkError):
    def __init__(
        self, status_code: int | None = None, raw: dict[str, Any] | str | None = None
    ) -> None:
        super().__init__(
            f"HTTP status: {status_code}", status_code=status_code, raw=raw
        )


class RetryHttpError(NetworkHttpError):
    pass


class RequestError(NetworkError):
    """
    The request was completed successfully,
    but the response turned out to be unsuitable for further work.
    """

    def __init__(
        self,
        message: str = "Incorrect response format.",
        status_code: int | None = None,
        raw: dict[str, Any] | str | None = None,
    ) -> None:
        super().__init__(message, status_code, raw=raw)


# config errors
class ConfigError(CollectorError):
    def __init__(self, message: str, config_path: Path | str | None = None) -> None:
        self.config_path = config_path
        super().__init__(message)


class ConfigDecodeError(ConfigError):
    pass


class ConfigIncorrect(ConfigError):
    pass


class ConfigFileError(ConfigError):
    pass


class InvalidUserPath(ConfigError):
    pass


class ConfigNotFound(ConfigFileError):
    pass


class ConfigPermissionError(ConfigFileError):
    pass
