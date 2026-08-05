from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from foreman_ai_hq import db
from foreman_ai_hq.needs_you import (
    LOW_CONFIDENCE_THRESHOLD,
    is_low_confidence,
    _current_estimate_revision,
    _estimate_revision,
)
from foreman_ai_hq.project_context import task_matches_project


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _next_estimate_revision(metadata: dict[str, Any]) -> int:
    return _estimate_revision(metadata) + 1


def _validate_project_task(database_path: Path | str, project_id: str, task_id: str) -> dict[str, Any]:
    try:
        task = db.get_task(database_path, task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="task not found") from exc
    if db.task_is_archived(task):
        raise HTTPException(status_code=409, detail="task is archived")
    if not task_matches_project(task, project_id):
        raise HTTPException(status_code=404, detail="task not found in project")
    return task


def _validate_estimate_revision(task: dict[str, Any], query_revision: int | None) -> None:
    if query_revision is None:
        return
    current = _current_estimate_revision(task)
    if query_revision != current:
        raise HTTPException(
            status_code=409,
            detail=f"estimate revision mismatch; current revision is {current}",
        )


def _envelope(
    project_id: str,
    task_id: str,
    decision_state: str,
    next_href: str | None = None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "project_id": project_id[:200],
        "task_id": task_id[:200],
        "decision_state": decision_state[:64],
        "next_href": next_href[:1000] if next_href else None,
    }


def _safe_href(value: str) -> str | None:
    href = str(value).strip()
    return href if href.startswith("/") and not href.startswith("//") else None


def acknowledge_low_confidence(
    database_path: Path | str,
    project_id: str,
    task_id: str,
    query_revision: int | None,
) -> dict[str, Any]:
    task = _validate_project_task(database_path, project_id, task_id)
    _validate_estimate_revision(task, query_revision)
    metadata = dict(task.get("metadata") or {})
    if not is_low_confidence(metadata):
        raise HTTPException(status_code=422, detail="task is not eligible for low-confidence acknowledgement")
    db.update_task(
        database_path,
        task_id,
        {
            "metadata": {
                **metadata,
                "low_confidence_decision": "acknowledged",
                "low_confidence_acknowledged_at": _now_iso(),
            },
        },
    )
    return _envelope(
        project_id,
        task_id,
        "resolved",
        next_href=_safe_href(f"/projects/{project_id}"),
    )


def apply_manual_estimate(
    database_path: Path | str,
    project_id: str,
    task_id: str,
    query_revision: int | None,
    estimate_tokens: int,
) -> dict[str, Any]:
    task = _validate_project_task(database_path, project_id, task_id)
    _validate_estimate_revision(task, query_revision)
    if not (1 <= estimate_tokens <= 10**15):
        raise HTTPException(status_code=422, detail="estimate_tokens must be a positive integer not greater than 10^15")
    metadata = dict(task.get("metadata") or {})
    recommended_model = task.get("recommended_model") or metadata.get("recommended_model")
    if not recommended_model:
        adapters = db.list_worker_adapters(database_path)
        default = next((a for a in adapters if a.get("is_default")), adapters[0] if adapters else None)
        supported = default.get("supported_models") or [] if default else []
        recommended_model = supported[0] if supported else ""
    new_revision = _next_estimate_revision(metadata)
    db.update_task(
        database_path,
        task_id,
        {
            "estimate_tokens": estimate_tokens,
            "recommended_model": recommended_model,
            "metadata": {
                **metadata,
                "estimation_source": "manual",
                "low_confidence_decision": "manual_estimate",
                "low_confidence_manual_estimated_at": _now_iso(),
                "estimate_revision": new_revision,
            },
        },
    )
    return _envelope(
        project_id,
        task_id,
        "resolved",
        next_href=_safe_href(f"/projects/{project_id}"),
    )
