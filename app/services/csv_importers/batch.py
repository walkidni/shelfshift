"""Compatibility shim for legacy app.services.csv_importers.batch imports."""

import sys

from typeshift.core.importers.csv import batch as _core_module

sys.modules[__name__] = _core_module
