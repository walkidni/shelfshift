"""Compatibility shim for legacy app.services.exporters.wix_csv imports."""

import sys

from shelfshift.core.exporters.platforms import wix as _core_module

sys.modules[__name__] = _core_module
