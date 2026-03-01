"""FastAPI server adapter for the Shelfshift core engine."""


import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Load .env before importing modules that may resolve/capture settings.
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

from .config import Settings, get_settings
from .routers import api, web_csv, web_url

BASE_DIR = Path(__file__).resolve().parent
PACKAGE_STATIC_DIR = BASE_DIR / "web" / "static"
PUBLIC_STATIC_DIR = ROOT_DIR / "public" / "static"
STATIC_DIR = PUBLIC_STATIC_DIR if PUBLIC_STATIC_DIR.exists() else PACKAGE_STATIC_DIR

logger = logging.getLogger("uvicorn.error")


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings if settings is not None else get_settings()
    logger.setLevel(logging.DEBUG if resolved_settings.debug else logging.INFO)

    fastapi_app = FastAPI(
        title=resolved_settings.app_name,
        summary="Ingest product URLs and export importable platform CSV files",
        version="1.0.0",
    )
    fastapi_app.state.settings = resolved_settings

    fastapi_app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_allow_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    fastapi_app.include_router(api.router)
    fastapi_app.include_router(web_url.router)
    fastapi_app.include_router(web_csv.router)
    return fastapi_app


app = create_app()
settings = app.state.settings


def run() -> None:
    import uvicorn

    uvicorn.run("shelfshift.server.main:app", host="0.0.0.0", port=8000, reload=bool(app.state.settings.debug))


__all__ = ["BASE_DIR", "STATIC_DIR", "app", "create_app", "logger", "run", "settings"]
