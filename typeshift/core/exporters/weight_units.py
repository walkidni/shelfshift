"""Compatibility shim for legacy typeshift.core.exporters.weight_units imports."""

import sys

from .shared import weight_units as _core_module

sys.modules[__name__] = _core_module
