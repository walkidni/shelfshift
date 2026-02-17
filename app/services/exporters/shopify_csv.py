"""Compatibility shim for legacy app.services.exporters.shopify_csv imports."""

import sys

from typeshift.core.exporters.platforms import shopify as _core_module

sys.modules[__name__] = _core_module
