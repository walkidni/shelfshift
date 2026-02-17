"""Validation report types for canonical product checks."""


from dataclasses import dataclass, field


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"
    field: str | None = None


@dataclass
class ValidationReport:
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)


__all__ = ["ValidationIssue", "ValidationReport"]
