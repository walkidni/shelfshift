"""Compatibility shim for legacy app.services.importer.platforms.amazon imports."""

import sys

from typeshift.core.importers.url.platforms import amazon as _core_module

sys.modules[__name__] = _core_module
