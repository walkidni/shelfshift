"""Compatibility shim for legacy app.services.exporters.wix_csv imports."""

import sys

from typeshift.core.exporters import wix_csv as _core_module

sys.modules[__name__] = _core_module
