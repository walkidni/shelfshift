"""Compatibility shim for legacy typeshift.core.exporters.squarespace_csv imports."""

import sys

from .platforms import squarespace as _core_module

sys.modules[__name__] = _core_module
