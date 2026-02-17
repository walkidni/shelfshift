"""Compatibility shim for legacy typeshift.core.exporters.bigcommerce_csv imports."""

import sys

from .platforms import bigcommerce as _core_module

sys.modules[__name__] = _core_module
