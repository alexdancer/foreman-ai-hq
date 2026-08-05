from __future__ import annotations

import math
from typing import Any

from foreman_ai_hq.project_context import task_matches_project
from foreman_ai_hq.task_kind import read_task_kind

LOW_CONFIDENCE_THRESHOLD = 0.60


def _as_finite_confidence(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    f = float(value)
    return f if math.isfinite(f) else None


def is_low_confidence(metadata: dict[str, Any] | None) -> bool:
    """Return True when an automatic estimate has a confidence below the advisory threshold."""
    metadata = metadata if isinstance(metadata, dict) else {}
    confidence = _as_finite_confidence(metadata.get("confidence"))
    investigation_recommended = metadata.get("investigation_recommended") is True
    if confidence is None or (
        confidence >= LOW_CONFIDENCE_THRESHOLD and not investigation_recommended
    ):
        return False
    source = str(metadata.get("estimation_source") or "")
    if source in ("manual", "manual_required", "manual_estimate"):
        return False
    decision = metadata.get("low_confidence_decision")
    if decision in ("acknowledged", "manual_estimate", "dismissed"):
        return False
    return True


def _estimate_revision(metadata: dict[str, Any]) -> int:
    value = metadata.get("estimate_revision")
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else 0


def _current_estimate_revision(task: dict[str, Any]) -> int:
    return _estimate_revision(task.get("metadata") or {})


def _safe_href(value: str) -> str | None:
    href = str(value).strip()
    return href if href.startswith("/") and not href.startswith("//") else None


def _bounded(value: Any, limit: int) -> str:
    text = str(value) if value is not None else ""
    return text[:limit]


def _action(kind: str, label: str, method: str, href: str | None) -> dict[str, Any] | None:
    safe_href = _safe_href(href) if href else None
    if not safe_href:
        return None
    return {
        "kind": kind,
        "label": label[:80],
        "method": method,
        "href": safe_href[:1000],
    }


def _investigate_href(project_id: str, task_id: str) -> str | None:
    """Generate a safe local href that opens the Planning Chat for this project and task."""
    return _safe_href(f"/projects/{project_id}/plan?investigate_task={task_id}")


def low_confidence_item(
    project_id: str,
    task: dict[str, Any],
    database_path: Path | str,
) -> dict[str, Any] | None:
    """Build a bounded low-confidence Needs You item, or None if not applicable."""
    metadata = task.get("metadata") or {}
    confidence = _as_finite_confidence(metadata.get("confidence"))
    if confidence is None or not is_low_confidence(metadata):
        return None

    # Project isolation: a task must belong to the requested project before any action is exposed.
    if not task_matches_project(task, project_id):
        return None

    task_kind = read_task_kind(metadata)
    estimate_revision = _current_estimate_revision(task)
    base = f"/api/projects/{project_id}/tasks/{task['id']}/estimate-decision"
    rev_q = f"?estimate_revision={estimate_revision}"

    actions = [
        _action("acknowledge_estimate", "Acknowledge estimate", "POST", f"{base}/acknowledge{rev_q}"),
        _action("manual_estimate", "Enter manual estimate", "POST", f"{base}/manual{rev_q}"),
        _action("investigate_in_chat", "Investigate in chat", "GET", _investigate_href(project_id, task["id"])),
    ]
    actions = [a for a in actions if a is not None]

    investigation_recommended = metadata.get("investigation_recommended") is True
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        reason = (
            f"Automatic estimate confidence is {confidence:.2f}, which is below the advisory threshold "
            f"of {LOW_CONFIDENCE_THRESHOLD:.2f}. "
        )
    else:
        reason = "Estimator explicitly recommends repository investigation before relying on this estimate. "
    reason += "Review the estimate, enter a manual value, or investigate in the Planning Chat."

    return {
        "id": f"task:{task['id']}:low_confidence_estimate"[:200],
        "kind": "low_confidence_estimate",
        "title": ("Investigation recommended" if investigation_recommended else "Low confidence estimate")[:200],
        "reason": _bounded(reason, 1000),
        "created_at": _bounded(task.get("created_at"), 64) or None,
        "task_id": str(task["id"])[:200],
        "task_kind": task_kind,
        "advisory": True,
        "confidence": confidence,
        "decision_state": "decision_required",
        "session_href": None,
        "actions": actions,
    }
