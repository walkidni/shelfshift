"""Compatibility shim for legacy typeshift.core.exporters.wix_csv imports."""

import sys

from .platforms import wix as _core_module

sys.modules[__name__] = _core_module
