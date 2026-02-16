"""FastAPI server adapter for the Typeshift core engine."""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Load .env before importing modules that may resolve/capture settings.
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

from .config import get_settings
from .routers import api, web_csv, web_url

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web" / "static"

settings = get_settings()
logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)


def create_app() -> FastAPI:
    fastapi_app = FastAPI(
        title=settings.app_name,
        summary="Ingest product URLs and export importable platform CSV files",
        version="1.0.0",
    )

    fastapi_app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allow_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    fastapi_app.include_router(api.router)
    fastapi_app.include_router(web_url.router)
    fastapi_app.include_router(web_csv.router)
    return fastapi_app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("typeshift.server.main:app", host="0.0.0.0", port=8000, reload=settings.debug)


__all__ = ["BASE_DIR", "STATIC_DIR", "app", "create_app", "logger", "run", "settings"]
