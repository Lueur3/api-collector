# api-collector

An asynchronous poller for public JSON APIs. It reads a config with a list of
sources, polls them in parallel, survives failures, maps responses into its own
typed models, and streams the results to a file. The output is data plus a
report: what succeeded, what failed, and why.

## Features

- **Parallel polling of sources** — results are collected as they become ready
- **Concurrency limit** — no more than 15 simultaneous requests
- **Retry with exponential backoff** — only transient failures are retried
- **Timeouts** — per-request (from the config) and a total one per source (12 s)
- **Resilience to failures** — one failing source does not bring down the rest;
  failed sources land in the report as error entries
- **Streaming output** — results are not accumulated in memory; each line is written as soon as it is ready
- **Typed models** — each source's response is parsed into its own `frozen` dataclass
- **Project exception hierarchy** — no bare `except:`, no errors silently swallowed

## Installation

Requires **Python ≥ 3.14**.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .                 # the package itself
pip install -e ".[dev]"          # + dev tools (mypy, ruff, pytest)
```

The package is installed in editable mode and can be run from any directory.

## Usage

```bash
api-collector config.toml                    # result → ./results.jsonl
api-collector config.toml -o report.jsonl    # custom result file
api-collector config.toml -v                 # verbose logging (DEBUG)
```

### CLI

```
usage: api-collector [-h] [-o OUTPUT] [-v] config_path
```

| Argument | Description |
| --- | --- |
| `config_path` | path to the configuration file (positional) |
| `-o, --output` | path to the result file; defaults to `results.jsonl` in the project root |
| `-v, --verbose` | verbose logging (DEBUG level) |

Exit codes: `0` — success, `1` — config or runtime error, `130` — interrupted
by the user (`Ctrl+C`).

## Configuration

A config is a TOML file with `[[API]]` tables. Fields:

| Field | Required | Description |
| --- | --- | --- |
| `name` | yes | Name of the source; must match a known parser name (see below), otherwise the config is rejected |
| `URL` | yes | Address of a public JSON API |
| `timeout` | no (default `5`) | Request timeout in seconds; must be > 0 |

Example (`config.toml` in the project root):

```toml
[[API]]
name = 'JokeApi'
URL = "https://v2.jokeapi.dev/joke/Any"
timeout = 5

[[API]]
name = "OpenMeteo"
URL = "https://api.open-meteo.com/v1/forecast?latitude=55.752&longitude=37.6178&current=temperature_2m&timezone=auto"
timeout = 5

[[API]]
name = "Exchangerate"
URL = "https://open.er-api.com/v6/latest/USD"
timeout = 5
```

### Built-in sources

Five sources with different response shapes, each with its own model and parser:

| `name` | Model | Response shape |
| --- | --- | --- |
| `JokeApi` | `JokeApi` | flat object, two possible joke variants (`joke` / `setup`+`delivery`) |
| `Noozra` | `Noozra` | list of articles in the `articles` field, dates in various formats |
| `BoredApi` | `BoredApi` | flat "things to do" object |
| `OpenMeteo` | `OpenMeteo` | part of the data nested in the `current` object, requires flattening |
| `Exchangerate` | `Exchangerate` | `rates` field — a currency rates dictionary |

## Result format

The result file is JSONL: one line per source. Each result is written as soon as
it is ready, so the line order does not have to match the config order.

Success:

```json
{"name": "OpenMeteo", "data": [{"latitude": 55.75, "longitude": 37.625, "timezone": "Europe/Moscow", "timezone_abbreviation": "GMT+3", "time": "2026-09-09 18:30:00", "temperature_2m": 19.0}]}
```

Failure (a source was unreachable or its answer could not be parsed — the other
sources keep running):

```json
{"name": "Noozra", "status_code": null, "errors": ["Unable to connect to 'https://noozra.com/api/articles?category=tech&limit=2'", "All connection attempts failed"], "raw": null}
```

`raw` and `status_code` are filled in when HTTP failed or the response body
turned out not to be JSON, so even a failure can be inspected.

## How it works

### Pipeline

```
config.toml → read_config() → Source[]
                        ↓
              asyncio.as_completed(...)   ← sources are polled in parallel
                        ↓
             processing_source()          ← total timeout (12 s)
                        ↓
        CollectorClient.fetch_source()    ← semaphore + retry
                        ↓
          parsers.parse_source()          ← response → its own dataclass model
                        ↓
       write_result() → streaming write to JSONL + terminal output
```

### Async

- `httpx.AsyncClient` lives inside an async context manager — connections are
  closed even if something fails inside (`__aexit__` calls `aclose()`)
- `asyncio.Semaphore(15)` caps the number of simultaneous requests
- Per-source total limit — `asyncio.timeout(12.0)` around the request
- `asyncio.as_completed` yields results as they finish, without waiting for the
  slowest source

### Retry

The `@retry()` decorator on `get_request()`:

- retries with exponential backoff: `1s → 2s → 4s → …`
- defaults: `max_attempts=2`, `initial_delay=1s`
- only timeouts, connection errors and HTTP errors from
  `RETRY_CODES = 429, 500, 502, 503, 504` (transient failures) are retried
- `400/401/403/404/…` and parsing errors are **not** retried
- `KeyboardInterrupt`/`SystemExit` pass through the decorator untouched

### Exception hierarchy

```
CollectorError
├── NetworkError
│   ├── NetworkTimeoutError      # request timeout
│   ├── NetworkConnectionError   # could not connect
│   ├── NetworkHttpError         # HTTP status is not 2xx
│   │   └── RetryHttpError       # retryable code (429/5xx)
│   └── RequestError             # HTTP 200, but the body was unsuitable
└── ConfigError
    ├── ConfigDecodeError        # TOML could not be parsed
    ├── ConfigIncorrect          # wrong structure / unknown source
    ├── ConfigFileError
    │   ├── ConfigNotFound
    │   └── ConfigPermissionError
    └── InvalidUserPath          # path does not lead to a file
```

Application-level errors (HTTP 200 with an error in the body, e.g. `error: true`
from JokeApi) are caught by the parser and turned into `SourceFailure` records
instead of exceptions.

### Logging

- Default level is `INFO`, `-v` switches to `DEBUG`
- Service output goes through `logging`, not `print`: with parallel polling the
  lines do not get interleaved
- The result file is separate from the terminal log output
- Level colors — only when logging to a terminal

## Project structure

```
api_collector/
├── __init__.py
├── main.py            # CLI, orchestration, streaming write, timeout control
├── config.py          # reading and validating the TOML config
├── models.py          # frozen dataclasses: Source, results and source models
├── client.py          # retry decorator, CollectorClient, get_request
├── parsers.py         # parsing each source's response into its own model
├── exceptions.py      # project exception hierarchy
└── logging_config.py  # logging setup (colors, levels)
```

Layers are separated: config → models → client → parsers → entry point.
No "raw" dicts leave the place where they are parsed.

## Development

```bash
python -m pytest                              # tests (63, including async ones)
python -m mypy --strict api_collector tests   # strict type checking
ruff check .                                  # linter
```

- `mypy --strict` with no `# type: ignore` — a hard project rule
- Tests cover the retry decorator, HTTP client, config, parsers and orchestration;
  retry is tested with mocked network failures — no real network needed