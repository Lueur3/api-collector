import tomllib
from pathlib import Path

from api_collector import exceptions
from api_collector.models import Source


def read_config(config_path: Path) -> list[Source]:
    try:
        api_config: list[Source] = []
        with open(config_path, "rb") as f:
            config = tomllib.load(f)

            for item in config["API"]:
                api_source = Source(
                    name=item["name"],
                    url=item["URL"],
                    timeout=item.get("timeout", 5),
                )
                api_config.append(api_source)

        return api_config

    except PermissionError as e:
        raise exceptions.ConfigPermissionError(
            message="There are no permissions to access this file.",
            config_path=config_path,
        ) from e

    except OSError as e:
        raise exceptions.ConfigFileError(
            message="System error or input/output error.", config_path=config_path
        ) from e

    except tomllib.TOMLDecodeError as e:
        raise exceptions.ConfigDecodeError(
            message="The file could not be read. Invalid encoding.",
            config_path=config_path,
        ) from e

    except ValueError as e:
        raise exceptions.ConfigIncorrect(
            "Incorrect configuration.", config_path=config_path
        ) from e

    except KeyError as e:
        raise exceptions.ConfigIncorrect(
            message="Incorrect configuration.", config_path=config_path
        ) from e

    except Exception as e:
        raise exceptions.ConfigError(
            message="Unexpected config error", config_path=config_path
        ) from e
