"""Shared runtime settings for server/web adapters.

This module owns environment-backed application settings. It is intentionally
separate from ``shelfshift.core.config`` because core config stays minimal and
framework-agnostic.
"""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_tagline: str
    brand_primary: str
    brand_secondary: str
    brand_ink: str
    debug: bool
    log_verbosity: str
    rapidapi_key: str | None
    cors_allow_origins: tuple[str, ...]


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _env_choice(name: str, default: str, *, allowed: set[str]) -> str:
    val = os.getenv(name)
    if val is None:
        return default
    normalized = val.strip().lower()
    if normalized in allowed:
        return normalized
    return default


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    origins = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
        if origin.strip()
    )
    return Settings(
        app_name=os.getenv("APP_NAME", "ShelfShift"),
        app_tagline=os.getenv(
            "APP_TAGLINE",
            "Developer toolkit for ecommerce catalog translation.",
        ),
        brand_primary=os.getenv("BRAND_PRIMARY", "#18d9b6"),
        brand_secondary=os.getenv("BRAND_SECONDARY", "#27c6f5"),
        brand_ink=os.getenv("BRAND_INK", "#020b1a"),
        debug=_env_bool("DEBUG", default=False),
        log_verbosity=_env_choice(
            "LOG_VERBOSITY",
            default="medium",
            allowed={"low", "medium", "high", "extrahigh"},
        ),
        rapidapi_key=os.getenv("RAPIDAPI_KEY"),
        cors_allow_origins=origins or ("*",),
    )


__all__ = ["Settings", "get_settings"]
