"""Compatibility shim for legacy app.services.exporters.squarespace_csv imports."""

import sys

from typeshift.core.exporters import squarespace_csv as _core_module

sys.modules[__name__] = _core_module
