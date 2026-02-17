"""Compatibility shim for legacy app.services.csv_importers.squarespace imports."""

import sys

from shelfshift.core.importers.csv import squarespace as _core_module

sys.modules[__name__] = _core_module
