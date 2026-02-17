"""Compatibility shim for legacy typeshift.core.exporters.shopify_csv imports."""

import sys

from .platforms import shopify as _core_module

sys.modules[__name__] = _core_module
