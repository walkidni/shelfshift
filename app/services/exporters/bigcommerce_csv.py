"""Compatibility shim for legacy app.services.exporters.bigcommerce_csv imports."""

import sys

from typeshift.core.exporters.platforms import bigcommerce as _core_module

sys.modules[__name__] = _core_module
