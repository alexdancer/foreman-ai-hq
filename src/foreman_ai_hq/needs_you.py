from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from foreman_ai_hq import db
from foreman_ai_hq.evidence_reporting import safe_evidence
from foreman_ai_hq.project_context import canonical_project_root, task_matches_project
from foreman_ai_hq.task_kind import read_task_kind

LOW_CONFIDENCE_THRESHOLD = 0.60
REESTIMATE_ATTEMPT_STALE_AFTER = timedelta(minutes=15)


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


def _is_resolved_by_decision(metadata: dict[str, Any]) -> bool:
    return metadata.get("low_confidence_decision") in ("acknowledged", "manual_estimate", "dismissed")


def _linked_scout_id(metadata: dict[str, Any]) -> str | None:
    value = metadata.get("linked_scout_id")
    return str(value) if value else None


def _pending_reestimate(metadata: dict[str, Any]) -> dict[str, Any] | None:
    value = metadata.get("pending_reestimate")
    return value if isinstance(value, dict) else None


def reestimate_attempt_requires_recovery(
    pending: dict[str, Any], *, now: datetime | None = None
) -> bool:
    """Return whether a recorded running attempt can no longer be trusted as live."""
    if str(pending.get("state") or "") != "running":
        return False
    started_at = pending.get("started_at")
    if not isinstance(started_at, str) or not started_at:
        return True
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    current = now or datetime.now(UTC)
    return current - started.astimezone(UTC) >= REESTIMATE_ATTEMPT_STALE_AFTER


def _safe_href(value: str) -> str | None:
    href = str(value).strip()
    return href if href.startswith("/") and not href.startswith("//") else None


def _bounded(value: Any, limit: int) -> str:
    text = str(value) if value is not None else ""
    return text[:limit]


def _scout_task(database_path: Path | str, project_id: str, scout_id: str) -> dict[str, Any] | None:
    try:
        scout = db.get_task(database_path, scout_id)
    except KeyError:
        return None
    if db.task_is_archived(scout):
        return None
    if not task_matches_project(scout, project_id):
        return None
    return scout


def _latest_completed_worker_run(database_path: Path | str, task_id: str) -> dict[str, Any] | None:
    runs = db.list_worker_runs(database_path, task_id=task_id)
    completed = [run for run in runs if run.get("status") == "completed" and run.get("session_id")]
    if not completed:
        return None
    # Chronological by id/started_at; take the latest completed run.
    return completed[-1]


def _scout_findings_ready(database_path: Path | str, scout: dict[str, Any]) -> bool:
    status = scout.get("status")
    if status not in {"Review", "Done"}:
        return False
    run = _latest_completed_worker_run(database_path, scout["id"])
    return run is not None and bool(run.get("session_id"))


def _scout_session_href(scout: dict[str, Any]) -> str | None:
    session_id = scout.get("session_id") or (scout.get("metadata") or {}).get("session_id")
    return _safe_href(f"/sessions/{session_id}") if session_id else None


def _redact_findings_text(text: str, project: dict[str, Any] | None) -> str:
    if not isinstance(text, str):
        return ""
    # Secret and path replacement must both happen before the item bound.
    redacted = safe_evidence(text, max_length=max(2000, len(text)))
    if not isinstance(redacted, str):
        redacted = ""
    if project:
        root = canonical_project_root(str(project["root_path"]))
        redacted = redacted.replace(root, "<project-root>")
    home = str(Path.home())
    redacted = redacted.replace(home, "<home>")
    return redacted[:2000]


def build_findings_excerpt(
    database_path: Path | str,
    scout: dict[str, Any],
    project: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract bounded, redacted Scout findings for re-estimation."""
    run = _latest_completed_worker_run(database_path, scout["id"])
    if run is None:
        return {"scout_task_id": scout["id"], "session_id": None, "worker_run_id": None, "findings": [], "truncated": False}
    session_id = scout.get("session_id") or (scout.get("metadata") or {}).get("session_id")
    worker_run_id = run["id"]
    events = db.list_worker_run_events(database_path, worker_run_id=worker_run_id) if run.get("session_id") else []
    findings: list[str] = []
    truncated = False
    aggregate_len = 0
    for event in events:
        if not isinstance(event, dict):
            continue
        if str(event.get("kind")) != "agent_message" or str(event.get("layer")) != "worker_harness":
            continue
        detail = event.get("detail") or {}
        if not isinstance(detail, dict):
            continue
        text = detail.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        redacted = _redact_findings_text(text, project)
        if len(redacted) >= 2000:
            truncated = True
        item_len = len(redacted.encode("utf-8"))
        if aggregate_len + item_len > 12_000:
            truncated = True
            break
        if len(findings) >= 6:
            truncated = True
            break
        findings.append(redacted)
        aggregate_len += item_len
    return {
        "scout_task_id": scout["id"][:200],
        "session_id": (session_id or "")[:200] if session_id else None,
        "worker_run_id": worker_run_id[:200] if worker_run_id else None,
        "findings": findings,
        "truncated": truncated,
    }


def _decision_state(
    task: dict[str, Any],
    metadata: dict[str, Any],
    database_path: Path | str,
    project_id: str,
) -> tuple[str, dict[str, Any] | None, str | None]:
    """Return (decision_state, scout_task_or_None, session_href_or_None)."""
    pending = _pending_reestimate(metadata)
    if pending:
        state = str(pending.get("state") or "")
        if state == "running":
            if reestimate_attempt_requires_recovery(pending):
                return "reestimate_failed", None, _scout_session_href_from_pending(pending)
            return "reestimate_running", None, _scout_session_href_from_pending(pending)
        if state == "ready":
            return "reestimate_ready", None, _scout_session_href_from_pending(pending)
        if state == "failed":
            return "reestimate_failed", None, _scout_session_href_from_pending(pending)
    scout_id = _linked_scout_id(metadata)
    if scout_id:
        scout = _scout_task(database_path, project_id, scout_id)
        if scout is None:
            return "scout_unavailable", None, None
        session_href = _scout_session_href(scout)
        if _scout_findings_ready(database_path, scout):
            return "findings_ready", scout, session_href
        return "scout_pending", scout, session_href
    return "decision_required", None, None


def _scout_session_href_from_pending(pending: dict[str, Any]) -> str | None:
    session_id = pending.get("session_id") if isinstance(pending, dict) else None
    return _safe_href(f"/sessions/{session_id}") if session_id else None


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


def _decision_actions(
    state: str,
    project_id: str,
    task_id: str,
    task_kind: str,
    estimate_revision: int,
    scout: dict[str, Any] | None,
    pending: dict[str, Any] | None,
    session_href: str | None,
) -> list[dict[str, Any]]:
    base = f"/api/projects/{project_id}/tasks/{task_id}/estimate-decision"
    rev_q = f"?estimate_revision={estimate_revision}"
    actions: list[dict[str, Any]] = []
    if state == "decision_required":
        actions.append(_action("acknowledge_estimate", "Acknowledge estimate", "POST", f"{base}/acknowledge{rev_q}"))
        actions.append(_action("manual_estimate", "Enter manual estimate", "POST", f"{base}/manual{rev_q}"))
        if task_kind != "scout":
            actions.append(_action("create_scout", "Create linked Scout", "POST", f"{base}/scout{rev_q}"))
    elif state == "scout_unavailable":
        actions.append(_action("acknowledge_estimate", "Acknowledge estimate", "POST", f"{base}/acknowledge{rev_q}"))
        actions.append(_action("manual_estimate", "Enter manual estimate", "POST", f"{base}/manual{rev_q}"))
    elif state == "scout_pending":
        if scout:
            href = _safe_href(f"/projects/{project_id}#task-{scout['id']}")
            actions.append(_action("view_scout", "View linked Scout", "GET", href))
    elif state == "findings_ready":
        if session_href:
            actions.append(_action("view_scout_report", "View Scout report", "GET", session_href))
        actions.append(_action("request_reestimate", "Request re-estimate", "POST", f"{base}/scout/reestimate{rev_q}"))
    elif state == "reestimate_running":
        if session_href:
            actions.append(_action("view_scout_report", "View Scout report", "GET", session_href))
    elif state == "reestimate_ready":
        if session_href:
            actions.append(_action("view_scout_report", "View Scout report", "GET", session_href))
        if pending:
            attempt_id = str(pending.get("attempt_id") or "")
            base_rev = int(pending.get("base_estimate_revision") or estimate_revision)
            apply_q = f"?estimate_revision={base_rev}&attempt_id={attempt_id}"
            actions.append(_action("apply_reestimate", "Apply re-estimate", "POST", f"{base}/scout/reestimate/apply{apply_q}"))
            actions.append(_action("dismiss_reestimate", "Dismiss re-estimate", "POST", f"{base}/scout/reestimate/dismiss{apply_q}"))
    elif state == "reestimate_failed":
        if session_href:
            actions.append(_action("view_scout_report", "View Scout report", "GET", session_href))
        if pending:
            attempt_id = str(pending.get("attempt_id") or "")
            base_rev = int(pending.get("base_estimate_revision") or estimate_revision)
            retry_q = f"?estimate_revision={base_rev}&attempt_id={attempt_id}"
            actions.append(_action("retry_reestimate", "Retry re-estimate", "POST", f"{base}/scout/reestimate/retry{retry_q}"))
            dismiss_q = f"?estimate_revision={base_rev}&attempt_id={attempt_id}"
            actions.append(_action("dismiss_reestimate", "Dismiss re-estimate", "POST", f"{base}/scout/reestimate/dismiss{dismiss_q}"))
    return [a for a in actions if a is not None]


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
    task_kind = read_task_kind(metadata)
    state, scout, session_href = _decision_state(task, metadata, database_path, project_id)
    estimate_revision = _current_estimate_revision(task)
    pending = _pending_reestimate(metadata)
    actions = _decision_actions(state, project_id, task["id"], task_kind, estimate_revision, scout, pending, session_href)
    scout_id = None if state == "scout_unavailable" else _linked_scout_id(metadata)
    investigation_recommended = metadata.get("investigation_recommended") is True
    reason = (
        f"Automatic estimate confidence is {confidence:.2f}, which is below the advisory threshold of {LOW_CONFIDENCE_THRESHOLD:.2f}. "
        if confidence < LOW_CONFIDENCE_THRESHOLD
        else "Estimator explicitly recommends repository investigation before relying on this estimate. "
    )
    return {
        "id": f"task:{task['id']}:low_confidence_estimate"[:200],
        "kind": "low_confidence_estimate",
        "title": ("Investigation recommended" if investigation_recommended else "Low confidence estimate")[:200],
        "reason": _bounded(
            reason + "Review the estimate, enter a manual value, or create a linked Scout to gather more information.",
            1000,
        ),
        "created_at": _bounded(task.get("created_at"), 64) or None,
        "task_id": str(task["id"])[:200],
        "task_kind": task_kind,
        "advisory": True,
        "confidence": confidence,
        "decision_state": state,
        "scout_task_id": scout_id[:200] if scout_id else None,
        "session_href": session_href,
        "actions": actions,
    }
