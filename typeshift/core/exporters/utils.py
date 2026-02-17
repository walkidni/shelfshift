"""Compatibility shim for legacy typeshift.core.exporters.utils imports."""

import sys

from .shared import utils as _core_module

sys.modules[__name__] = _core_module
