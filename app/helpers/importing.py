"""Compatibility shim for legacy app.helpers.importing imports."""

import sys

from shelfshift.server.helpers import importing as _server_module

sys.modules[__name__] = _server_module
