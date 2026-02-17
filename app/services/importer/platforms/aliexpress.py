"""Compatibility shim for legacy app.services.importer.platforms.aliexpress imports."""

import sys

from shelfshift.core.importers.url.platforms import aliexpress as _core_module

sys.modules[__name__] = _core_module
