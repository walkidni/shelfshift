"""Application entry-point.

This module creates the FastAPI ``app`` instance, wires middleware, mounts
static files and includes all routers.  Business logic lives in
``app.helpers`` and route handlers live in ``app.routers``.
"""

from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from dotenv import load_dotenv
load_dotenv()

from .config import get_settings
from .routers import api, web_csv, web_url

# Re-export so that ``monkeypatch.setattr("app.main._run_import_product", ...)``
# in test code keeps working after the refactor.
from .helpers.importing import run_import_product as _run_import_product  # noqa: F401

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web" / "static"

settings = get_settings()
logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)


app = FastAPI(
    title=settings.app_name,
    summary="Ingest product URLs and export importable platform CSV files",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allow_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include routers ---
app.include_router(api.router)
app.include_router(web_url.router)
app.include_router(web_csv.router)
