"""Compatibility facade for legacy ``app.config`` imports."""

from typeshift.config import Settings, get_settings


__all__ = ["Settings", "get_settings"]
