from dataclasses import fields
from datetime import datetime
from collections.abc import Callable
import api_collector.models as models


def parse_joke_api(data: models.SourceResponse) -> list[models.ParsedItem]: 
    api_response = {}
    data_fields = {f.name for f in fields(models.JokeApi)}
    for k, v in data.response.items():
        if k in data_fields:
            api_response[k] = v
        
    return [models.JokeApi(**api_response)]

def parse_noozra(data: models.SourceResponse) -> list[models.ParsedItem]:
    res: list[models.ParsedItem] = []
    data_fields = {f.name for f in fields(models.Noozra)}
    for article in data.response['articles']:
        api_response = {}
        for k, v in article.items():
            if k in data_fields:
                api_response[k] = v

        dt = datetime.strptime(api_response['published_at'], "%Y-%m-%dT%H:%M:%SZ")
        api_response['published_at'] = dt.strftime("%Y-%m-%d %H:%M:%S")
        res.append(models.Noozra(**api_response))

    return res
    

def parse_bored_api(data: models.SourceResponse) -> list[models.ParsedItem]: 
    api_response = {}
    data_fields = {f.name for f in fields(models.BoredApi)}
    for k, v in data.response.items():
        if k in data_fields:
            api_response[k] = v
            
    return [models.BoredApi(**api_response)]


def parse_open_meteo(data: models.SourceResponse) -> list[models.ParsedItem]: 
    api_response = {}
    data_fields = {f.name for f in fields(models.OpenMeteo)}
    for k, v in data.response.items():
        if k in data_fields:
            api_response[k] = v
        if isinstance(v, dict):
            for k_c, v_c in v.items():
                if k_c in data_fields:
                    api_response[k_c] = v_c
        
    dt = datetime.strptime(api_response['time'], "%Y-%m-%dT%H:%M")
    api_response['time'] = dt.strftime("%Y-%m-%d %H:%M:%S")

    return [models.OpenMeteo(**api_response)]


def parse_exchangerate(data: models.SourceResponse) -> list[models.ParsedItem]: 
    api_response = {}
    data_fields = {f.name for f in fields(models.Exchangerate)}
    for k, v in data.response.items():
        if k in data_fields:
            api_response[k] = v

    dt = datetime.strptime(api_response["time_last_update_utc"], "%a, %d %b %Y %H:%M:%S %z")
    api_response["time_last_update_utc"] = dt.strftime("%Y-%m-%d %H:%M:%S")

    return [models.Exchangerate(**api_response)]



PARSE_SOURCES: dict[str, Callable[[models.SourceResponse], list[models.ParsedItem]]] = {"JokeApi": parse_joke_api, "Noozra": parse_noozra, "BoredApi": parse_bored_api, "OpenMeteo": parse_open_meteo, "Exchangerate": parse_exchangerate}

def parse_source(api_sources: list[models.SourceResponse]) -> list[models.SourcesResults]:
    sr_list: list[models.SourcesResults] = []
    
    for source in api_sources:
        parse_function = PARSE_SOURCES[source.name]

        sr = models.SourcesResults(
            name=source.name,
            items=parse_function(source)
        )
        sr_list.append(sr)
    
    return sr_list
