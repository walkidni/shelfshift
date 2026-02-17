"""Compatibility shim for legacy app.helpers.exporting imports."""

import sys

from shelfshift.server.helpers import exporting as _server_module

sys.modules[__name__] = _server_module
