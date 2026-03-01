"""Server configuration facade."""

from fastapi import Request

from ..config import Settings, get_settings


def get_app_settings(request: Request) -> Settings:
    app_settings = getattr(request.app.state, "settings", None)
    if isinstance(app_settings, Settings):
        return app_settings
    return get_settings()


__all__ = ["Settings", "get_app_settings", "get_settings"]
