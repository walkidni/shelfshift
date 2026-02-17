"""Compatibility shim for legacy app.services.csv_importers.wix imports."""

import sys

from typeshift.core.importers.csv import wix as _core_module

sys.modules[__name__] = _core_module
