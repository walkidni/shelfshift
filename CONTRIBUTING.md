# Contributing

Thanks for contributing to Shelfshift.

## Local development setup

Prerequisites:

- Python 3.13+
- `uv` (recommended): <https://astral.sh/uv>

Install project dependencies:

```bash
uv sync
```

## Run commands locally

One-off invocation:

```bash
uv run shelfshift detect ./source.csv
```

Repeated local work:

```bash
source .venv/bin/activate
shelfshift detect ./source.csv
```

When `.venv` is activated, you do not need `uv run`.

## Run tests

Activate the virtual environment in the same command/session before running tests:

```bash
source .venv/bin/activate
pytest -q
```

## Repository layout

```text
shelfshift/
  core/
    canonical/
    detect/
    importers/
    exporters/
    validate/
  cli/
    main.py
  server/
    main.py
    config.py
    schemas.py
    routers/
    helpers/
    logging/
    web/
tests/
```
