"""Compatibility shim for legacy app.services.csv_importers.woocommerce imports."""

import sys

from typeshift.core.importers.csv import woocommerce as _core_module

sys.modules[__name__] = _core_module
