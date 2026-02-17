"""Compatibility shim for legacy typeshift.core.exporters.batch imports."""

import sys

from .shared import batch as _core_module

sys.modules[__name__] = _core_module
