"""Core engine configuration.

Core config is side-effect free: it does not load dotenv files.
"""


from dataclasses import dataclass


@dataclass(frozen=True)
class CoreConfig:
    strict: bool = False
    debug: bool = False


def config_from_env(*, strict: bool = False, debug: bool = False) -> CoreConfig:
    return CoreConfig(strict=strict, debug=debug)


__all__ = ["CoreConfig", "config_from_env"]
