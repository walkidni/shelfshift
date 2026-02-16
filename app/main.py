"""Compatibility entrypoint for legacy ``app.main`` imports.

The canonical FastAPI adapter now lives under ``typeshift.server.main``.
"""

from typeshift.server.main import (  # noqa: F401
    BASE_DIR,
    STATIC_DIR,
    app,
    create_app,
    logger,
    settings,
)
from .helpers.importing import run_import_product as _run_import_product  # noqa: F401
