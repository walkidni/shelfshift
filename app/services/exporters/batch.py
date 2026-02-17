"""Compatibility shim for legacy app.services.exporters.batch imports."""

import sys

from typeshift.core.exporters import batch as _core_module

sys.modules[__name__] = _core_module
