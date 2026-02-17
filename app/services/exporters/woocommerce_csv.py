"""Compatibility shim for legacy app.services.exporters.woocommerce_csv imports."""

import sys

from typeshift.core.exporters.platforms import woocommerce as _core_module

sys.modules[__name__] = _core_module
