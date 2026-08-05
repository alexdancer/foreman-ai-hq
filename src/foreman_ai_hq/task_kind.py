from __future__ import annotations

from typing import Any

CANONICAL_TASK_KINDS = {"implementation", "acceptance_verification"}
DEFAULT_TASK_KIND = "implementation"
# Retired kinds remain readable as history, but cannot be set on new Tasks.
LEGACY_TASK_KINDS = {"scout"}


def read_task_kind(metadata: dict[str, Any] | None) -> str:
    """Canonical Task-kind reader.

    Prefer ``metadata.task_kind``, preserve valid legacy
    ``metadata.task_breakdown_kind`` (including retired kinds such as
    ``scout``), otherwise default to ``implementation``. No DB migration
    required.
    """

    metadata = metadata or {}
    task_kind = metadata.get("task_kind")
    if task_kind in CANONICAL_TASK_KINDS:
        return str(task_kind)
    if task_kind in LEGACY_TASK_KINDS:
        return str(task_kind)
    legacy = metadata.get("task_breakdown_kind")
    if legacy in CANONICAL_TASK_KINDS:
        return str(legacy)
    if legacy in LEGACY_TASK_KINDS:
        return str(legacy)
    return DEFAULT_TASK_KIND


def is_canonical_task_kind(value: Any) -> bool:
    return isinstance(value, str) and value in CANONICAL_TASK_KINDS


def validate_task_kind(value: Any) -> str:
    if not is_canonical_task_kind(value):
        raise ValueError(f"task_kind must be one of {sorted(CANONICAL_TASK_KINDS)}, got {value!r}")
    return str(value)


def with_task_kind(metadata: dict[str, Any] | None, kind: str) -> dict[str, Any]:
    """Return metadata with canonical ``task_kind`` set.

    Validates the supplied kind and preserves the existing legacy
    ``task_breakdown_kind`` provenance.
    """

    validate_task_kind(kind)
    updated = dict(metadata or {})
    updated["task_kind"] = kind
    return updated
