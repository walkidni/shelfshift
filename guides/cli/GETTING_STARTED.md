# Shelfshift CLI Getting Started

## Install

### Option A: pip (inside a virtual environment)

```bash
python -m venv .venv
source .venv/bin/activate
pip install shelfshift
```

### Option B: uv (run without installing globally)

```bash
uvx shelfshift --help
```

### Option C: uv (install CLI tool once)

```bash
uv tool install shelfshift
shelfshift --help
```

## Quickstart: Convert a CSV in one command

```bash
shelfshift convert ./source.csv \
  --to shopify \
  --out ./shopify.csv \
  --report ./convert_report.json
```

## Confirm CLI Is Available

```bash
shelfshift --help
```

---

Previous: [CLI Guide Index](./INDEX.md) | Next: [CLI Core Concepts](./CORE_CONCEPTS.md)
