from unittest.mock import Mock

import pytest

import api_collector.exceptions as exceptions
import api_collector.models as models
import api_collector.parsers as parser


def test_extract_fields_without_flatten() -> None:
    raw_data = {
        "category": "Programming",
        "type": "single",
        "id": 123,
        "lang": "en",
        "joke": "Why do programmers prefer dark mode?",
        "error": False,
        "flags": {"nsfw": False},
    }

    result = parser.extract_fields(raw_data, models.JokeApi, flatten=False)

    assert result == {
        "category": "Programming",
        "type": "single",
        "id": 123,
        "lang": "en",
        "joke": "Why do programmers prefer dark mode?",
    }
    assert "error" not in result
    assert "flags" not in result


def test_extract_fields_with_flatten() -> None:
    raw_data = {
        "latitude": 52.52,
        "longitude": 13.41,
        "timezone": "Europe/Berlin",
        "timezone_abbreviation": "CET",
        "current": {
            "time": "2024-01-15T14:00",
            "temperature_2m": 20.5,
            "wind_speed_10m": 15.3,
        },
        "daily": {
            "temperature_2m_max": [25.0, 26.0],
        },
    }

    result_no_flatten = parser.extract_fields(raw_data, models.OpenMeteo, flatten=False)
    assert "time" not in result_no_flatten
    assert "temperature_2m" not in result_no_flatten
    assert result_no_flatten["latitude"] == 52.52

    result_flatten = parser.extract_fields(raw_data, models.OpenMeteo, flatten=True)
    assert result_flatten == {
        "latitude": 52.52,
        "longitude": 13.41,
        "timezone": "Europe/Berlin",
        "timezone_abbreviation": "CET",
        "time": "2024-01-15T14:00",
        "temperature_2m": 20.5,
    }


def test_parse_date_valid_format() -> None:
    result = parser.parse_date("2024-01-15T14:30:00Z", "%Y-%m-%dT%H:%M:%SZ")
    assert result == "2024-01-15 14:30:00"


def test_parse_date_invalid_format() -> None:
    result = parser.parse_date("not a date", "%Y-%m-%dT%H:%M:%SZ")
    assert result == "not a date"


def test_parse_date_multiple_formats() -> None:
    result = parser.parse_date(
        "2024-01-15T14:30:00.123Z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
    )
    assert result == "2024-01-15 14:30:00"


def test_parse_joke_api() -> None:
    response = models.SourceResponse(
        name="JokeApi",
        response={
            "category": "Pun",
            "type": "twopart",
            "id": 176,
            "lang": "en",
            "setup": "What do you call 4 Mexicans in quicksand?",
            "delivery": "Quatro Sinko.",
            "error": False,
            "flags": {"nsfw": False},
        },
        status_code=200,
    )

    result = parser.parse_joke_api(response)

    assert len(result) == 1
    assert isinstance(result[0], models.JokeApi)
    assert result[0].category == "Pun"
    assert result[0].type == "twopart"
    assert result[0].id == 176
    assert result[0].lang == "en"
    assert result[0].setup == "What do you call 4 Mexicans in quicksand?"
    assert result[0].delivery == "Quatro Sinko."
    assert result[0].joke is None


def test_parse_joke_api_with_error() -> None:
    response = models.SourceResponse(
        name="JokeApi",
        response={
            "error": True,
            "internalError": False,
            "code": 106,
            "message": "No matching joke found",
            "causedBy": ["No jokes were found that match your provided filter(s)."],
            "timestamp": 1788091061768,
        },
        status_code=200,
    )

    with pytest.raises(exceptions.RequestError) as exc_info:
        parser.parse_joke_api(response)

    assert exc_info.value.status_code == 200
    assert exc_info.value.raw == response.response


def test_parse_noozra() -> None:
    response = models.SourceResponse(
        name="Noozra",
        response={
            "articles": [
                {
                    "headline": "First article",
                    "url": "https://example.com/1",
                    "published_at": "2024-01-15T14:30:00Z",
                    "description": "Description 1",
                    "author": "John",
                    "source": "test",
                },
                {
                    "headline": "Second article",
                    "url": "https://example.com/2",
                    "published_at": "2024-01-16T10:00:00.123Z",
                    "description": "Description 2",
                },
            ]
        },
        status_code=200,
    )
    result = parser.parse_noozra(response)

    assert len(result) == 2

    assert all(isinstance(item, models.Noozra) for item in result)

    assert isinstance(result[0], models.Noozra)
    assert isinstance(result[1], models.Noozra)

    assert result[0].headline == "First article"
    assert result[0].url == "https://example.com/1"
    assert result[0].description == "Description 1"
    assert result[0].published_at == "2024-01-15 14:30:00"

    assert result[1].headline == "Second article"
    assert result[1].url == "https://example.com/2"
    assert result[1].description == "Description 2"
    assert result[1].published_at == "2024-01-16 10:00:00"


def test_parse_bored_api() -> None:
    response = models.SourceResponse(
        name="BoredApi",
        response={
            "activity": "Go on a fishing trip with some friends",
            "type": "social",
            "participants": 3,
            "price": 0.4,
            "accessibility": "Minor challenges",
            "duration": "hours",
            "day": "Monday",
            "age": "12+",
        },
        status_code=200,
    )

    result = parser.parse_bored_api(response)

    assert len(result) == 1
    assert isinstance(result[0], models.BoredApi)
    assert result[0].activity == "Go on a fishing trip with some friends"
    assert result[0].type == "social"
    assert result[0].participants == 3
    assert result[0].price == 0.4
    assert result[0].accessibility == "Minor challenges"
    assert result[0].duration == "hours"


def test_parse_open_meteo() -> None:
    response = models.SourceResponse(
        name="OpenMeteo",
        response={
            "latitude": 55.75,
            "longitude": 37.625,
            "timezone": "Europe/Moscow",
            "timezone_abbreviation": "GMT+3",
            "current": {
                "time": "2026-08-30T14:45",
                "temperature_2m": 21.9,
                "wind_speed_10m": 5.2,
            },
            "city": "Moscow",
        },
        status_code=200,
    )

    result = parser.parse_open_meteo(response)

    assert len(result) == 1
    assert isinstance(result[0], models.OpenMeteo)
    assert result[0].latitude == 55.75
    assert result[0].longitude == 37.625
    assert result[0].timezone == "Europe/Moscow"
    assert result[0].timezone_abbreviation == "GMT+3"
    assert result[0].time == "2026-08-30 14:45:00"
    assert result[0].temperature_2m == 21.9


def test_parse_exchangerate() -> None:
    response = models.SourceResponse(
        name="Exchangerate",
        response={
            "result": "success",
            "time_next_update_unix": 1788135901,
            "time_last_update_utc": "Sat, 30 Aug 2026 00:02:31 +0000",
            "base_code": "USD",
            "rates": {
                "USD": 1,
                "AED": 3.6725,
                "AFN": 64.68294,
            },
        },
        status_code=200,
    )

    result = parser.parse_exchangerate(response)

    assert len(result) == 1
    assert isinstance(result[0], models.Exchangerate)
    assert result[0].time_last_update_utc == "2026-08-30 00:02:31"
    assert result[0].base_code == "USD"
    assert result[0].rates == {
        "USD": 1,
        "AED": 3.6725,
        "AFN": 64.68294,
    }


def test_parse_exchangerate_error() -> None:
    response = models.SourceResponse(
        name="Exchangerate",
        response={"result": "error", "error-type": "unsupported-code"},
        status_code=200,
    )

    with pytest.raises(exceptions.RequestError) as exc_info:
        parser.parse_exchangerate(response)

    assert exc_info.value.status_code == 200
    assert exc_info.value.raw == response.response


def test_parse_source_dispatches_to_correct_parser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_item = Mock()

    def fake_parser(data: models.SourceResponse) -> list[models.ParsedItem]:
        return [fake_item]

    monkeypatch.setattr(parser, "PARSE_SOURCES", {"FakeApi": fake_parser})

    response = models.SourceResponse(
        name="FakeApi", response={"some": "data"}, status_code=200
    )

    result = parser.parse_source(response)

    assert isinstance(result, models.SourcesResults)
    assert result.name == "FakeApi"
    assert result.data == [fake_item]


def test_parse_source_unknown_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parser, "PARSE_SOURCES", {})

    response = models.SourceResponse(name="UnknownApi", response={}, status_code=200)

    with pytest.raises(exceptions.RequestError) as exc_info:
        parser.parse_source(response)

    assert "Unknown source 'UnknownApi'" in exc_info.value.message
    assert exc_info.value.status_code == 200
    assert exc_info.value.raw == {}
