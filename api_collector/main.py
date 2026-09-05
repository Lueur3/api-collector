import argparse
import json
import logging
import sys
from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path
from typing import TextIO

import api_collector.parsers as parsers
from api_collector import exceptions, models
from api_collector.client import CollectorClient
from api_collector.config import read_config
from api_collector.logging_config import configure_logging

MODULE_DIR = Path(__file__).parent
RES_PATH = MODULE_DIR.parent / "results.jsonl"
logger = logging.getLogger(__name__)


def make_failure(
    data_name: str,
    e_data: list[str],
    e: exceptions.NetworkError | exceptions.RequestError,
) -> models.SourceFailure:
    return models.SourceFailure(
        name=data_name, errors=e_data, status_code=e.status_code, raw=e.raw
    )


def processing_source(
    client: CollectorClient, source: models.Source
) -> models.SourceResult:
    try:
        res: models.SourceResponse = client.fetch_source(source)
    except exceptions.NetworkError as e:
        sf = make_failure(source.name, [str(e), str(e.__cause__)], e)
        logger.error(
            "Failed to fetch source '%s': %s (cause: %s)",
            source.name,
            e,
            e.__cause__,
        )

        return sf

    else:
        try:
            parse_result = parsers.parse_source(res)
        except exceptions.RequestError as e:
            sf = make_failure(res.name, [e.message], e)
            logger.error("Failed to parse source '%s': %s", source.name, e.message)

            return sf

        else:
            return parse_result


def get_api_responds(
    client: CollectorClient, api_config: list[models.Source]
) -> Iterator[models.SourceResult]:

    for source in api_config:
        yield processing_source(client, source)


def write_result(api_res: models.SourceResult, writer: TextIO) -> None:
    data = asdict(api_res)
    writer.write(json.dumps(data, ensure_ascii=False) + "\n")
    logger.info("Result saved to: %s", writer.name)


def show_api_result(source: models.SourceResult) -> None:
    print(source.name)

    match source:
        case models.SourcesResults(data=items):
            pass
        case models.SourceFailure(errors=items):
            pass
        case _:
            items = []

    for item in items:
        print(item)
        print()
    print()


def get_config_path(user_path: str) -> Path:
    clean_path = user_path.strip().strip("'\"")
    target_path = Path(clean_path)

    try:
        target_path = target_path.resolve()

        if not target_path.exists():
            raise exceptions.ConfigNotFound("Config not found.", target_path)

        if not target_path.is_file():
            raise exceptions.InvalidUserPath(
                f"Is a directory, not a file: '{target_path}'"
            )

    except OSError as e:
        raise exceptions.InvalidUserPath("Invalid user path.", target_path) from e

    return target_path


def validate_sources(
    api_config: list[models.Source],
    config_path: Path,
) -> None:
    for source in api_config:
        if source.name not in parsers.PARSE_SOURCES:
            raise exceptions.ConfigIncorrect(
                message=f"Unknown source: '{source.name}'",
                config_path=config_path,
            )


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Polls data from configured API sources"
    )

    parser.add_argument("config_path", help="Path to the source configuration file")
    parser.add_argument(
        "-o", "--output", required=False, help="Path to the result file"
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable detailed logging"
    )

    args = parser.parse_args()
    configure_logging(verbose=args.verbose)

    try:
        config_path = get_config_path(args.config_path)
        api_config: list[models.Source] = read_config(config_path)

        validate_sources(api_config, config_path)

        res_file_path = args.output if args.output else RES_PATH
        with CollectorClient() as client:
            results = get_api_responds(client, api_config)

            with open(res_file_path, "w", encoding="utf-8") as writer:
                for res in results:
                    write_result(res, writer)
                    show_api_result(res)

    except exceptions.CollectorError as e:
        logger.error("Program Error: %s : (cause %s)", e, e.__cause__)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("The program was stopped by the user")
        sys.exit(130)
    except Exception:
        logger.exception("Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()
