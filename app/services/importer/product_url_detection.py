"""Compatibility shim for legacy app.services.importer.product_url_detection imports."""

import sys

from shelfshift.core.detect import url as _core_module

sys.modules[__name__] = _core_module
