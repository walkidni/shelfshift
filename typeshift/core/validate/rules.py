"""Baseline canonical validation rules."""

from __future__ import annotations

from app.models import Product

from .report import ValidationIssue, ValidationReport


def validate_product(product: Product) -> ValidationReport:
    issues: list[ValidationIssue] = []

    if not (product.title or "").strip():
        issues.append(
            ValidationIssue(
                code="missing_title",
                message="Product title is required.",
                field="title",
            )
        )

    if not product.variants:
        issues.append(
            ValidationIssue(
                code="missing_variants",
                message="At least one variant is required.",
                field="variants",
            )
        )

    return ValidationReport(valid=not issues, issues=issues)


__all__ = ["validate_product"]
