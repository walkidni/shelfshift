"""Compatibility shim for legacy app.services.importer.platforms.shopify imports."""

import sys

from typeshift.core.importers.url.platforms import shopify as _core_module

sys.modules[__name__] = _core_module
