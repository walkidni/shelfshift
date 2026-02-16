"""Core engine configuration.

Core config is side-effect free: it does not load dotenv files.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CoreConfig:
    strict: bool = False
    debug: bool = False
    rapidapi_key: str | None = None


def config_from_env(*, strict: bool = False, debug: bool = False) -> CoreConfig:
    return CoreConfig(
        strict=strict,
        debug=debug,
        rapidapi_key=os.getenv("RAPIDAPI_KEY"),
    )


__all__ = ["CoreConfig", "config_from_env"]
