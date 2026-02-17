"""Compatibility shim for legacy app.services.csv_importers.bigcommerce imports."""

import sys

from typeshift.core.importers.csv import bigcommerce as _core_module

sys.modules[__name__] = _core_module
