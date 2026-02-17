"""Compatibility shim for legacy app.services.exporters.utils imports."""

import sys

from typeshift.core.exporters.shared import utils as _core_module

sys.modules[__name__] = _core_module
