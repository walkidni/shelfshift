"""Compatibility shim for legacy app.services.csv_importers.common imports."""

import sys

from shelfshift.core.importers.csv import common as _core_module

sys.modules[__name__] = _core_module
