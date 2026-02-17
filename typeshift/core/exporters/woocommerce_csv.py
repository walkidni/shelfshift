"""Compatibility shim for legacy typeshift.core.exporters.woocommerce_csv imports."""

import sys

from .platforms import woocommerce as _core_module

sys.modules[__name__] = _core_module
