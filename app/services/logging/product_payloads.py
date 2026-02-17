"""Compatibility shim for legacy app.services.logging.product_payloads imports."""

import sys

from typeshift.server.logging import product_payloads as _server_module

sys.modules[__name__] = _server_module
