from __future__ import annotations

import datetime
import hashlib
import json
import secrets
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

from foreman_ai_hq import db
from foreman_ai_hq.estimation import estimate_task, EstimatorError, EstimateResult
from foreman_ai_hq.llm import extract_usage, resolve_cost, response_to_dict
from foreman_ai_hq.model_routing import route_worker_model, WorkerModelRoutingResult
from foreman_ai_hq.project_context import project_task_metadata, resolve_task_project, task_matches_project
from foreman_ai_hq.task_kind import read_task_kind
from foreman_ai_hq.worker_model_allowlist import allowed_worker_model_ids
from foreman_ai_hq.needs_you import (
    LOW_CONFIDENCE_THRESHOLD,
    is_low_confidence,
    _current_estimate_revision,
    _estimate_revision,
    _linked_scout_id,
    _pending_reestimate,
    _scout_task,
    _latest_completed_worker_run,
    _scout_findings_ready,
    _scout_session_href,
    build_findings_excerpt,
    reestimate_attempt_requires_recovery,
)


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
    scout_task_id: str | None = None,
    next_href: str | None = None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "project_id": project_id[:200],
        "task_id": task_id[:200],
        "decision_state": decision_state[:64],
        "scout_task_id": scout_task_id[:200] if scout_task_id else None,
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


def _build_scout_description(task: dict[str, Any]) -> str:
    metadata = task.get("metadata") or {}
    title = f"Scout for {task['id']}"
    description = task.get("description") or ""
    question = metadata.get("scout_question") or "What do I need to know before estimating this task?"
    boundary = metadata.get("scout_inspection_boundary") or "Inspect the connected project repository only."
    expected = metadata.get("scout_expected_findings") or "Relevant files, dependencies, risks, and a concise recommendation."
    sections = [
        title,
        "",
        f"Investigation question: {question}",
        f"Inspection boundary: {boundary}",
        f"Expected findings: {expected}",
        "",
        "Original task context:",
        description,
        "",
        "You are a read-only Scout. Produce findings, risks, and a recommendation. Do not edit files, run destructive commands, migrations, or commits.",
    ]
    return "\n".join(sections).strip()


def _selected_worker_adapter(database_path: Path | str, adapter_id: str | None) -> dict[str, Any] | None:
    if adapter_id:
        try:
            return db.get_worker_adapter(database_path, adapter_id)
        except KeyError:
            return None
    adapters = db.list_worker_adapters(database_path)
    return next((a for a in adapters if a.get("is_default")), adapters[0] if adapters else None)


def _to_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _from_json(value: str) -> dict[str, Any]:
    return json.loads(value)


async def create_scout_for_task(
    request: Request,
    database_path: Path | str,
    project_id: str,
    task_id: str,
    query_revision: int | None,
) -> dict[str, Any]:
    """Atomically create/link one Scout for the current estimate revision and estimate it."""
    task = _validate_project_task(database_path, project_id, task_id)
    _validate_estimate_revision(task, query_revision)
    metadata = task.get("metadata") or {}
    task_kind = read_task_kind(metadata)
    if task_kind == "scout":
        raise HTTPException(status_code=422, detail="Scout tasks cannot create nested Scouts")
    if not is_low_confidence(metadata):
        raise HTTPException(status_code=422, detail="task is not eligible for Scout creation")

    estimate_revision = _current_estimate_revision(task)
    project, _ = resolve_task_project(database_path, task, expected_project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="connected project not found")

    scout_id: str | None = None
    created_scout = False

    with db.connect(database_path) as conn:
        conn.execute("begin immediate")
        row = conn.execute("select metadata_json from tasks where id = ?", (task_id,)).fetchone()
        if row is None:
            conn.execute("rollback")
            raise HTTPException(status_code=404, detail="task not found")
        current_meta = _from_json(row["metadata_json"]) or {}
        if _estimate_revision(current_meta) != estimate_revision:
            conn.execute("rollback")
            raise HTTPException(status_code=409, detail="estimate revision changed during Scout creation")
        existing_scout_id = _linked_scout_id(current_meta)
        if existing_scout_id and _estimate_revision(current_meta) == estimate_revision:
            scout_id = existing_scout_id
        else:
            scout_id = f"scout_{uuid.uuid4().hex}"
            scout_meta = {
                **project_task_metadata(project),
                "task_kind": "scout",
                "scout_for_task_id": task_id,
                "scout_for_estimate_revision": estimate_revision,
                "estimation_state": "pending",
            }
            conn.execute(
                """
                insert into tasks (
                    id, description, status, estimate_tokens, recommended_model,
                    actual_tokens, session_id, metadata_json, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scout_id,
                    _build_scout_description(task),
                    "Pending",
                    0,
                    None,
                    None,
                    None,
                    _to_json(scout_meta),
                    _now_iso(),
                ),
            )
            updated_target = dict(current_meta)
            updated_target["linked_scout_id"] = scout_id
            updated_target["linked_scout_revision"] = estimate_revision
            updated_target["low_confidence_decision"] = "scout"
            conn.execute(
                "update tasks set metadata_json = ? where id = ?",
                (_to_json(updated_target), task_id),
            )
            created_scout = True

    if scout_id is None:
        raise HTTPException(status_code=503, detail="Scout creation failed")

    if not created_scout:
        return _envelope(
            project_id,
            task_id,
            "scout_pending",
            scout_task_id=scout_id,
            next_href=_safe_href(f"/projects/{project_id}#task-{scout_id}"),
        )

    scout = db.get_task(database_path, scout_id)
    settings = request.app.state.settings
    estimator_model = settings.estimator_model
    adapter = _selected_worker_adapter(database_path, None)
    try:
        result, llm_response = await estimate_task(
            scout["description"],
            request.app.state.guardrails,
            llm_client=request.app.state.llm_client,
            estimator_model=estimator_model,
            project_root=project.get("root_path"),
            project_profile=project.get("profile") or {},
            adapter=adapter,
            task_kind="scout",
        )
    except EstimatorError as exc:
        db.update_task(
            database_path,
            scout_id,
            {
                "metadata": {
                    **(scout.get("metadata") or {}),
                    "estimation_state": "failed",
                    "requires_manual_estimate": True,
                    "estimation_source": "manual_required",
                    "blocked_reason": "Scout estimation unavailable or invalid; manual estimate required.",
                    "blocked_condition": {
                        "reason": "Scout estimation unavailable or invalid; manual estimate required.",
                        "origin": "scout_estimation",
                        "timestamp": _now_iso(),
                    },
                    "estimator_failure_type": type(exc).__name__,
                },
            },
        )
        return _envelope(
            project_id,
            task_id,
            "scout_pending",
            scout_task_id=scout_id,
            next_href=_safe_href(f"/projects/{project_id}#task-{scout_id}"),
        )

    estimation_session = db.create_session(
        database_path,
        task_description=scout["description"],
        model=estimator_model,
        session_key_hash=_hash(f"scout-estimation:{scout_id}:{scout['description']}"),
        guardrail_overrides={},
        status="completed",
    )
    model_routing = route_worker_model(
        request.app.state.guardrails,
        complexity=result.complexity,
        estimate_tokens=result.token_estimate,
        remaining_daily_tokens=None,
        daily_cap_tokens=None,
        adapter=adapter,
        allowed_models=allowed_worker_model_ids(adapter) if adapter else [],
    )
    scout_meta = {
        **(scout.get("metadata") or {}),
        "estimation_source": result.source,
        "complexity": result.complexity,
        "confidence": result.confidence,
        "rationale": result.rationale,
        "assumptions": result.assumptions,
        "risk_flags": result.risk_flags,
        "budget_note": result.budget_note,
        "estimation_session_id": estimation_session["id"],
        "drivers": result.drivers,
        "shadow_token_estimate": result.shadow_token_estimate,
        "estimate_disagreement": result.estimate_disagreement,
        "coefficient_provenance": result.coefficient_provenance,
        "estimation_state": "estimated",
        "session_id": estimation_session["id"],
        **model_routing.metadata,
        "task_kind": "scout",
    }
    db.update_task(
        database_path,
        scout_id,
        {
            "status": "Estimated",
            "estimate_tokens": result.token_estimate,
            "recommended_model": model_routing.selected_model,
            "session_id": estimation_session["id"],
            "metadata": scout_meta,
        },
    )
    return _envelope(
        project_id,
        task_id,
        "scout_pending",
        scout_task_id=scout_id,
        next_href=_safe_href(f"/projects/{project_id}#task-{scout_id}"),
    )


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _record_reestimate_token_turn(
    database_path: Path | str,
    session_id: str,
    estimator_model: str,
    llm_response: Any,
) -> None:
    usage = extract_usage(llm_response)
    db.record_token_turn(
        database_path,
        session_id=session_id,
        usage_kind="estimation",
        model=estimator_model,
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
        cost=resolve_cost(estimator_model, llm_response),
        raw_usage={**usage, "response": response_to_dict(llm_response), "spend_category": "orchestration"},
    )


def _model_allowed_for_task(database_path: Path | str, model: str, adapter_id: str | None = None) -> bool:
    adapter = _selected_worker_adapter(database_path, adapter_id)
    if not adapter:
        return False
    return model in allowed_worker_model_ids(adapter)


def _set_pending_reestimate(database_path: Path | str, task_id: str, pending: dict[str, Any] | None) -> dict[str, Any]:
    def updater(metadata: dict[str, Any]) -> dict[str, Any]:
        updated = dict(metadata)
        if pending is None:
            updated.pop("pending_reestimate", None)
        else:
            updated["pending_reestimate"] = pending
        return updated
    return db.update_task_metadata(database_path, task_id, updater)


def _claim_initial_reestimate(
    database_path: Path | str,
    *,
    task_id: str,
    expected_revision: int,
    task_description: str,
    estimator_model: str,
    pending: dict[str, Any],
) -> None:
    """Atomically claim one running attempt and create its evidence session."""
    with db.connect(database_path) as conn:
        conn.execute("begin immediate")
        row = conn.execute("select metadata_json from tasks where id = ?", (task_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="task not found")
        metadata = _from_json(row["metadata_json"]) or {}
        if _estimate_revision(metadata) != expected_revision:
            raise HTTPException(status_code=409, detail="estimate revision changed before re-estimation")
        existing = _pending_reestimate(metadata)
        if existing and str(existing.get("state") or "") in {"running", "ready"}:
            raise HTTPException(
                status_code=409,
                detail=f"re-estimation already {existing['state']}",
            )
        conn.execute(
            """
            insert into sessions (
                id, task_description, model, session_key_hash, started_at, status,
                guardrail_overrides_json
            ) values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pending["session_id"],
                task_description,
                estimator_model,
                _hash(f"reestimate:{task_id}:{pending['scout_task_id']}:{pending['attempt_id']}"),
                pending["started_at"],
                "running",
                _to_json({}),
            ),
        )
        metadata["pending_reestimate"] = pending
        conn.execute(
            "update tasks set metadata_json = ? where id = ?",
            (_to_json(metadata), task_id),
        )


def _claim_retry_reestimate(
    database_path: Path | str,
    *,
    task_id: str,
    expected_revision: int,
    attempt_id: str | None,
    pending: dict[str, Any],
) -> dict[str, Any]:
    """Atomically recheck and claim a failed or abandoned attempt before spend."""
    with db.connect(database_path) as conn:
        conn.execute("begin immediate")
        row = conn.execute("select metadata_json from tasks where id = ?", (task_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="task not found")
        metadata = _from_json(row["metadata_json"]) or {}
        if _estimate_revision(metadata) != expected_revision:
            raise HTTPException(status_code=409, detail="estimate revision changed before retry")
        current = _pending_reestimate(metadata)
        if not current:
            raise HTTPException(status_code=409, detail="no pending re-estimate to retry")
        state = str(current.get("state") or "")
        if state != "failed" and not reestimate_attempt_requires_recovery(current):
            raise HTTPException(status_code=409, detail="re-estimate is not in a retryable state")
        if attempt_id and attempt_id != str(current.get("attempt_id") or ""):
            raise HTTPException(status_code=409, detail="attempt id does not match pending re-estimate")
        claimed = {
            **current,
            **pending,
            "state": "running",
            "started_at": _now_iso(),
            "acknowledged_duplicate_spend": True,
        }
        metadata["pending_reestimate"] = claimed
        conn.execute(
            "update tasks set metadata_json = ? where id = ?",
            (_to_json(metadata), task_id),
        )
    return claimed


def _apply_reestimate_result(
    database_path: Path | str,
    target: dict[str, Any],
    result: EstimateResult,
    model_routing: WorkerModelRoutingResult,
    pending: dict[str, Any],
) -> dict[str, Any]:
    metadata = dict(target.get("metadata") or {})
    new_revision = _next_estimate_revision(metadata)
    updated = {
        **metadata,
        **result.as_dict(),
        "estimation_source": result.source,
        "estimate_revision": new_revision,
        "low_confidence_decision": None,
        "pending_reestimate": None,
        "previous_estimate_revision": metadata.get("estimate_revision"),
        "scout_reestimate_applied_at": _now_iso(),
        "scout_reestimate_attempt_id": pending.get("attempt_id"),
    }
    return db.update_task(
        database_path,
        target["id"],
        {
            "estimate_tokens": result.token_estimate,
            "recommended_model": model_routing.selected_model,
            "metadata": updated,
        },
    )


async def request_scout_reestimate(
    request: Request,
    database_path: Path | str,
    project_id: str,
    task_id: str,
    query_revision: int | None,
) -> dict[str, Any]:
    task = _validate_project_task(database_path, project_id, task_id)
    _validate_estimate_revision(task, query_revision)
    metadata = task.get("metadata") or {}
    scout_id = _linked_scout_id(metadata)
    if not scout_id:
        raise HTTPException(status_code=422, detail="no linked Scout for re-estimation")
    scout = _scout_task(database_path, project_id, scout_id)
    if scout is None:
        raise HTTPException(status_code=404, detail="linked Scout not found")
    if not _scout_findings_ready(database_path, scout):
        raise HTTPException(status_code=422, detail="linked Scout does not have completed findings")
    project, _ = resolve_task_project(database_path, task, expected_project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="connected project not found")

    excerpt = build_findings_excerpt(database_path, scout, project)
    if not isinstance(excerpt.get("findings"), list) or not excerpt["findings"]:
        raise HTTPException(status_code=422, detail="no usable Scout findings for re-estimation")

    attempt_id = f"reattempt_{uuid.uuid4().hex}"
    base_revision = _current_estimate_revision(task)
    run = _latest_completed_worker_run(database_path, scout_id)
    if run is None:
        raise HTTPException(status_code=422, detail="linked Scout has no completed Worker Run")
    started_at = _now_iso()
    session_id = f"sess_{uuid.uuid4().hex}"
    pending: dict[str, Any] = {
        "attempt_id": attempt_id,
        "state": "running",
        "started_at": started_at,
        "base_estimate_revision": base_revision,
        "scout_task_id": scout_id,
        "session_id": session_id,
        "worker_run_id": run["id"],
        "findings": excerpt["findings"],
        "truncated": bool(excerpt.get("truncated")),
    }
    settings = request.app.state.settings
    estimator_model = settings.estimator_model
    _claim_initial_reestimate(
        database_path,
        task_id=task_id,
        expected_revision=base_revision,
        task_description=f"Re-estimate task {task_id} from Scout {scout_id}",
        estimator_model=estimator_model,
        pending=pending,
    )
    adapter = _selected_worker_adapter(database_path, None)
    try:
        result, llm_response = await estimate_task(
            task["description"],
            request.app.state.guardrails,
            llm_client=request.app.state.llm_client,
            estimator_model=estimator_model,
            project_root=project.get("root_path"),
            project_profile=project.get("profile") or {},
            adapter=adapter,
            task_kind=read_task_kind(metadata),
            scout_findings=excerpt,
        )
    except EstimatorError as exc:
        failed_pending = {
            **pending,
            "state": "failed",
            "failure": {
                "reason": str(exc),
                "timestamp": _now_iso(),
            },
        }
        _set_pending_reestimate(database_path, task_id, failed_pending)
        raise HTTPException(status_code=503, detail="re-estimation unavailable") from exc

    _record_reestimate_token_turn(database_path, session_id, estimator_model, llm_response)
    db.update_session_status(database_path, session_id, "completed")
    model_routing = route_worker_model(
        request.app.state.guardrails,
        complexity=result.complexity,
        estimate_tokens=result.token_estimate,
        remaining_daily_tokens=None,
        daily_cap_tokens=None,
        adapter=adapter,
        allowed_models=allowed_worker_model_ids(adapter) if adapter else [],
    )
    ready_pending = {
        **pending,
        "state": "ready",
        "result": {
            "token_estimate": result.token_estimate,
            "recommended_model": model_routing.selected_model,
            "complexity": result.complexity,
            "confidence": result.confidence,
            "rationale": result.rationale,
            "assumptions": result.assumptions,
            "risk_flags": result.risk_flags,
            "budget_note": result.budget_note,
            "drivers": result.drivers,
            "shadow_token_estimate": result.shadow_token_estimate,
            "estimate_disagreement": result.estimate_disagreement,
            "coefficient_provenance": result.coefficient_provenance,
        },
    }
    _set_pending_reestimate(database_path, task_id, ready_pending)
    return _envelope(
        project_id,
        task_id,
        "reestimate_ready",
        scout_task_id=scout_id,
        next_href=_safe_href(f"/projects/{project_id}#task-{task_id}"),
    )


def apply_reestimate(
    database_path: Path | str,
    project_id: str,
    task_id: str,
    query_revision: int | None,
    attempt_id: str | None,
) -> dict[str, Any]:
    task = _validate_project_task(database_path, project_id, task_id)
    _validate_estimate_revision(task, query_revision)
    metadata = task.get("metadata") or {}
    pending = _pending_reestimate(metadata)
    if not pending or str(pending.get("state")) != "ready":
        raise HTTPException(status_code=409, detail="no ready re-estimate to apply")
    if attempt_id and attempt_id != str(pending.get("attempt_id") or ""):
        raise HTTPException(status_code=409, detail="attempt id does not match pending re-estimate")
    base_revision = int(pending.get("base_estimate_revision") or 1)
    if base_revision != _current_estimate_revision(task):
        raise HTTPException(status_code=409, detail="estimate revision changed since re-estimate was computed")
    result_data = pending.get("result")
    if not isinstance(result_data, dict):
        raise HTTPException(status_code=422, detail="pending re-estimate result is malformed")
    recommended_model = str(result_data.get("recommended_model") or "")
    if not _model_allowed_for_task(database_path, recommended_model):
        raise HTTPException(status_code=409, detail="pending re-estimate route is no longer allowed")
    result = EstimateResult(
        token_estimate=int(result_data["token_estimate"]),
        complexity=str(result_data["complexity"]),
        confidence=float(result_data["confidence"]),
        rationale=str(result_data.get("rationale") or ""),
        assumptions=list(result_data.get("assumptions") or []),
        risk_flags=list(result_data.get("risk_flags") or []),
        budget_note=str(result_data.get("budget_note") or ""),
        source=str(result_data.get("source") or "llm"),
        drivers=dict(result_data.get("drivers") or {}),
        shadow_token_estimate=int(result_data.get("shadow_token_estimate") or 0),
        estimate_disagreement=float(result_data.get("estimate_disagreement") or 0.0),
        coefficient_provenance=dict(result_data.get("coefficient_provenance") or {}),
    )
    model_routing = WorkerModelRoutingResult(
        selected_model=recommended_model,
        metadata={"selected_adapter_id": (task.get("metadata") or {}).get("launch_adapter_id") or ""},
    )
    _apply_reestimate_result(database_path, task, result, model_routing, pending)
    return _envelope(
        project_id,
        task_id,
        "resolved",
        scout_task_id=_linked_scout_id(metadata),
        next_href=_safe_href(f"/projects/{project_id}"),
    )


def dismiss_reestimate(
    database_path: Path | str,
    project_id: str,
    task_id: str,
    query_revision: int | None,
    attempt_id: str | None,
) -> dict[str, Any]:
    task = _validate_project_task(database_path, project_id, task_id)
    _validate_estimate_revision(task, query_revision)
    metadata = task.get("metadata") or {}
    pending = _pending_reestimate(metadata)
    if not pending:
        raise HTTPException(status_code=409, detail="no pending re-estimate to dismiss")
    if attempt_id and attempt_id != str(pending.get("attempt_id") or ""):
        raise HTTPException(status_code=409, detail="attempt id does not match pending re-estimate")
    dismissed_at = _now_iso()

    def record_dismissal(current: dict[str, Any]) -> dict[str, Any]:
        current_pending = _pending_reestimate(current)
        if not current_pending or str(current_pending.get("attempt_id") or "") != str(
            pending.get("attempt_id") or ""
        ):
            raise HTTPException(status_code=409, detail="pending re-estimate changed before dismissal")
        updated = dict(current)
        updated.pop("pending_reestimate", None)
        updated["last_dismissed_reestimate"] = {
            "attempt_id": str(pending.get("attempt_id") or "")[:200],
            "state": str(pending.get("state") or "")[:64],
            "base_estimate_revision": int(pending.get("base_estimate_revision") or 0),
            "scout_task_id": str(pending.get("scout_task_id") or "")[:200] or None,
            "dismissed_at": dismissed_at,
        }
        return updated

    db.update_task_metadata(database_path, task_id, record_dismissal)
    return _envelope(
        project_id,
        task_id,
        "resolved",
        scout_task_id=_linked_scout_id(metadata),
        next_href=_safe_href(f"/projects/{project_id}"),
    )


async def retry_reestimate(
    request: Request,
    database_path: Path | str,
    project_id: str,
    task_id: str,
    query_revision: int | None,
    attempt_id: str | None,
    acknowledge_duplicate_spend: bool,
) -> dict[str, Any]:
    task = _validate_project_task(database_path, project_id, task_id)
    _validate_estimate_revision(task, query_revision)
    metadata = task.get("metadata") or {}
    pending = _pending_reestimate(metadata)
    if not pending:
        raise HTTPException(status_code=409, detail="no pending re-estimate to retry")
    state = str(pending.get("state") or "")
    if state != "failed" and not reestimate_attempt_requires_recovery(pending):
        raise HTTPException(status_code=409, detail="re-estimate is not in a retryable state")
    if attempt_id and attempt_id != str(pending.get("attempt_id") or ""):
        raise HTTPException(status_code=409, detail="attempt id does not match pending re-estimate")
    if not acknowledge_duplicate_spend:
        raise HTTPException(status_code=422, detail="retry requires acknowledge_possible_duplicate_spend: true")

    scout_id = _linked_scout_id(metadata)
    if not scout_id:
        raise HTTPException(status_code=422, detail="no linked Scout for re-estimation")
    scout = _scout_task(database_path, project_id, scout_id)
    if scout is None:
        raise HTTPException(status_code=404, detail="linked Scout not found")
    project, _ = resolve_task_project(database_path, task, expected_project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="connected project not found")

    excerpt = build_findings_excerpt(database_path, scout, project)
    if not isinstance(excerpt.get("findings"), list) or not excerpt["findings"]:
        raise HTTPException(status_code=422, detail="no usable Scout findings for re-estimation")
    pending = _claim_retry_reestimate(
        database_path,
        task_id=task_id,
        expected_revision=_current_estimate_revision(task),
        attempt_id=attempt_id,
        pending={
            **pending,
            "findings": excerpt["findings"],
            "truncated": bool(excerpt.get("truncated")),
        },
    )
    settings = request.app.state.settings
    estimator_model = settings.estimator_model
    adapter = _selected_worker_adapter(database_path, None)
    try:
        result, llm_response = await estimate_task(
            task["description"],
            request.app.state.guardrails,
            llm_client=request.app.state.llm_client,
            estimator_model=estimator_model,
            project_root=project.get("root_path"),
            project_profile=project.get("profile") or {},
            adapter=adapter,
            task_kind=read_task_kind(metadata),
            scout_findings=excerpt,
        )
    except EstimatorError as exc:
        failed_pending = {
            **pending,
            "state": "failed",
            "failure": {
                "reason": str(exc),
                "timestamp": _now_iso(),
            },
        }
        _set_pending_reestimate(database_path, task_id, failed_pending)
        raise HTTPException(status_code=503, detail="re-estimation unavailable") from exc

    session_id = str(pending.get("session_id") or "")
    if session_id:
        _record_reestimate_token_turn(database_path, session_id, estimator_model, llm_response)
    model_routing = route_worker_model(
        request.app.state.guardrails,
        complexity=result.complexity,
        estimate_tokens=result.token_estimate,
        remaining_daily_tokens=None,
        daily_cap_tokens=None,
        adapter=adapter,
        allowed_models=allowed_worker_model_ids(adapter) if adapter else [],
    )
    ready_pending = {
        **pending,
        "state": "ready",
        "result": {
            "token_estimate": result.token_estimate,
            "recommended_model": model_routing.selected_model,
            "complexity": result.complexity,
            "confidence": result.confidence,
            "rationale": result.rationale,
            "assumptions": result.assumptions,
            "risk_flags": result.risk_flags,
            "budget_note": result.budget_note,
            "drivers": result.drivers,
            "shadow_token_estimate": result.shadow_token_estimate,
            "estimate_disagreement": result.estimate_disagreement,
            "coefficient_provenance": result.coefficient_provenance,
        },
    }
    _set_pending_reestimate(database_path, task_id, ready_pending)
    return _envelope(
        project_id,
        task_id,
        "reestimate_ready",
        scout_task_id=scout_id,
        next_href=_safe_href(f"/projects/{project_id}#task-{task_id}"),
    )
