from pathlib import Path
from api_collector.config import read_config 
from api_collector.client import get_request 

MODULE_DIR = Path(__file__).parent
API_CONFIG = MODULE_DIR.parent / 'config.toml'



def main() -> None:
    api_config = read_config(API_CONFIG)
    
    

if __name__ == "__main__":
    main()