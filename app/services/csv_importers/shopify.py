"""Compatibility shim for legacy app.services.csv_importers.shopify imports."""

import sys

from typeshift.core.importers.csv import shopify as _core_module

sys.modules[__name__] = _core_module
