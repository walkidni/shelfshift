"""Compatibility shim for legacy app.services.exporters.weight_units imports."""

import sys

from typeshift.core.exporters import weight_units as _core_module

sys.modules[__name__] = _core_module
