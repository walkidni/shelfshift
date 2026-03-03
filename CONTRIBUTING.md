# Contributing

Thanks for contributing to Shelfshift.

## Local Development Setup

Prerequisites:

- Python 3.10+
- `uv` (recommended): <https://astral.sh/uv>

Install dependencies:

```bash
uv sync
```

Optional smoke check:

```bash
python -c "import shelfshift; print(shelfshift.__version__)"
```

## Run Commands Locally

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

## Run Tests

Activate the virtual environment in the same command/session before running tests:

```bash
source .venv/bin/activate
pytest -q
```

## Repository Layout

```text
src/
  shelfshift/
    __init__.py
    cli/
      main.py
    core/
      api.py
      registry.py
      canonical/
      detect/
      importers/
        csv/
        url/
      exporters/
        platforms/
        shared/
      validate/
tests/
guides/
```
