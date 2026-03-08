"""Shared typing helpers for CSV schema modules."""

from collections.abc import Sequence

HeaderAliases = dict[str, tuple[str, ...]]
HeaderTemplates = Sequence[str]
