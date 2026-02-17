"""Compatibility shim for legacy app.services.importer.platforms.common imports."""

import sys

from shelfshift.core.importers.url import common as _core_module

sys.modules[__name__] = _core_module
