"""Compatibility shim for legacy app.services.exporters.squarespace_csv imports."""

import sys

from shelfshift.core.exporters.platforms import squarespace as _core_module

sys.modules[__name__] = _core_module
