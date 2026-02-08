from __future__ import annotations

import os
import typing as t
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
    rapidapi_key: t.Optional[str]
    amazon_country: str
    cors_allow_origins: tuple[str, ...]


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    origins = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
        if origin.strip()
    )
    return Settings(
        app_name=os.getenv("APP_NAME", "TradeMint Import Studio"),
        app_tagline=os.getenv(
            "APP_TAGLINE",
            "Turn product URLs into structured catalog data in seconds.",
        ),
        brand_primary=os.getenv("BRAND_PRIMARY", "#e65c2f"),
        brand_secondary=os.getenv("BRAND_SECONDARY", "#f8b84a"),
        brand_ink=os.getenv("BRAND_INK", "#1f1916"),
        debug=_env_bool("DEBUG", default=False),
        rapidapi_key=os.getenv("RAPIDAPI_KEY"),
        amazon_country=os.getenv("AMAZON_COUNTRY", "US"),
        cors_allow_origins=origins or ("*",),
    )
