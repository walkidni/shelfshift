"""Compatibility shim for legacy app.helpers.rendering imports."""

import sys

from shelfshift.server.helpers import rendering as _server_module

sys.modules[__name__] = _server_module
