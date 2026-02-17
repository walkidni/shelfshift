"""Compatibility shim for legacy app.services.csv_importers.detection imports."""

import sys

from shelfshift.core.importers.csv import detection as _core_module

sys.modules[__name__] = _core_module
