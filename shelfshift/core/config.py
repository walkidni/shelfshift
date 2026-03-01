"""Core engine configuration.

Core config is side-effect free: it does not load dotenv files.
"""


import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CoreConfig:
    strict: bool = False
    debug: bool = False
    rapidapi_key: str | None = None


def resolve_rapidapi_key(rapidapi_key: str | None = None) -> str | None:
    if rapidapi_key is not None:
        return rapidapi_key
    return os.getenv("RAPIDAPI_KEY")


def config_from_env(*, strict: bool = False, debug: bool = False) -> CoreConfig:
    return CoreConfig(
        strict=strict,
        debug=debug,
        rapidapi_key=resolve_rapidapi_key(),
    )


__all__ = ["CoreConfig", "config_from_env", "resolve_rapidapi_key"]
