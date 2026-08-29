import logging
import sys
from typing import ClassVar


class ColoredFormatter(logging.Formatter):
    COLORS: ClassVar[dict[int, str]] = {
        logging.DEBUG: "\033[34m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[31m",
    }

    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)

        if not sys.stderr.isatty():
            return message

        color = self.COLORS.get(record.levelno)

        if color is not None:
            return f"{color}{message}{self.RESET}"

        return message


def configure_logging(verbose: bool = False) -> None:
    root_logger = logging.getLogger()

    if root_logger.handlers:
        return

    level = logging.DEBUG if verbose else logging.INFO

    console_handler = logging.StreamHandler()

    formatter = ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
