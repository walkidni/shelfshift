"""Compatibility shim for legacy app.helpers.payload imports."""

import sys

from typeshift.server.helpers import payload as _server_module

sys.modules[__name__] = _server_module
