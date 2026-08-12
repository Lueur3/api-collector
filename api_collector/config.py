from pathlib import Path
import tomllib
from api_collector.models import Source


def read_config(config_path: Path) -> list[Source]:
    with open(config_path, 'rb') as f:    
        api_config: list[Source] = []
        config = tomllib.load(f)
        for item in config['API']:
            api_source = Source(
                name=item['name'],
                url=item['URL'],
                timeout=item.get('timeout', 5)
            )
            api_config.append(api_source)
    return api_config

