from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    timeout: float = 5.0

    def __post_init__(self) -> None:
        object.__setattr__(self, 'name', self.name.strip())
        object.__setattr__(self, 'url', self.url.strip())

        if not self.name:
            raise ValueError("Name is required")
        if not self.url:
            raise ValueError("URL is required")

        if self.timeout <= 0:
            raise ValueError(f"timeout must be greater than 0; got '{self.timeout}'")


@dataclass(frozen=True)
class SourceResponse:
    name: str
    response: Any
    status_code: int

@dataclass(frozen=True)
class SourcesResults:
    name: str
    items: list[ParsedItem] = field(default_factory=list)

@dataclass(frozen=True)
class JokeApi:
    category: str
    type: str
    id: int
    lang: str
    joke: str | None = None
    setup: str | None = None
    delivery: str | None = None

@dataclass(frozen=True)
class Noozra:
    headline: str
    url: str
    published_at: str
    description: str

@dataclass(frozen=True)
class BoredApi:
    activity: str
    type: str
    participants: int
    price: float
    accessibility: str
    duration: str

@dataclass(frozen=True)
class OpenMeteo:
    latitude: float
    longitude: float
    timezone: str
    timezone_abbreviation: str
    time: str
    temperature_2m: float

@dataclass(frozen=True)
class Exchangerate:
    time_last_update_utc: str
    base_code: str
    rates: dict[str, float]

ParsedItem = JokeApi | Noozra | BoredApi | OpenMeteo | Exchangerate