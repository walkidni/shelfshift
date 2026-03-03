# Shelfshift Getting Started

## Install

### pip

```bash
pip install shelfshift
```

### uv (project dependency)

```bash
uv add shelfshift
uv sync
```

### uv (virtualenv-style install)

```bash
uv venv
source .venv/bin/activate
uv pip install shelfshift
```

## 🚀 Quickstart: Convert a CSV in one line

```python
from shelfshift import convert_csv

csv_bytes, report = convert_csv(
    "./source.csv",
    target="shopify",
)
```

---

Previous: [Core Library Guide Index](./INDEX.md) | Next: [Core Concepts](./CORE_CONCEPTS.md)
