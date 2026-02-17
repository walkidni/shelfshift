"""Compatibility shim for legacy app.services.importer.platforms.squarespace imports."""

import sys

from shelfshift.core.importers.url.platforms import squarespace as _core_module

sys.modules[__name__] = _core_module
