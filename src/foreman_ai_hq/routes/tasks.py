from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import quote
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from pydantic import ValidationError

from foreman_ai_hq import db
from foreman_ai_hq.auth import require_portal_auth
from foreman_ai_hq.orchestrator_gate import require_configured_orchestrator
from foreman_ai_hq.estimation import EstimatorError, estimate_task
from foreman_ai_hq.task_kind import (
    DEFAULT_TASK_KIND,
    is_canonical_task_kind,
    read_task_kind,
    validate_task_kind,
    with_task_kind,
)
from foreman_ai_hq.evidence_reporting import safe_evidence as _safe_review_value
from foreman_ai_hq.evidence_reporting import token_totals
from foreman_ai_hq.model_routing import route_worker_model
from foreman_ai_hq.pi_adapter import (
    PiStructuredJobError,
    PiStructuredOutputError,
    run_pi_structured_job,
)
from foreman_ai_hq.project_context import project_task_metadata, resolve_task_project, task_matches_project, task_project_board_path
from foreman_ai_hq.repo_context import build_repo_context_brief
from foreman_ai_hq.task_launch import (
    DEFAULT_PROXY_URL,
    TaskLaunchBlocked,
    _create_harness_commit,
    _fast_forward_base,
    _git_diff_summary,
    _restore_operator_branch,
    _review_disposition_state_after_commit,
    detect_pr_capability,
    launch_task,
    refresh_task_from_session,
)
from foreman_ai_hq.task_breakdown import (
    TaskBreakdownError,
    breakdown_task_source,
    validate_breakdown_result,
)
from foreman_ai_hq.estimate_decision import (
    acknowledge_low_confidence,
    apply_manual_estimate,
    apply_reestimate,
    create_scout_for_task,
    dismiss_reestimate,
    request_scout_reestimate,
    retry_reestimate,
)
from foreman_ai_hq.worker_model_allowlist import allowed_worker_model_ids

router = APIRouter()
CANONICAL_TASK_STATUSES = {"Estimated", "Running", "Review", "Done"}
PositiveStrictInt = Annotated[int, Field(strict=True, gt=0)]
NonNegativeStrictInt = Annotated[int, Field(strict=True, ge=0)]


class TaskCreateRequest(BaseModel):
    description: str = Field(min_length=1)
    status: str | None = None
    estimate_tokens: PositiveStrictInt | None = None
    recommended_model: str | None = None
    actual_tokens: NonNegativeStrictInt | None = None
    session_id: str | None = None
    metadata: dict[str, Any] | None = None


class TaskUpdateRequest(BaseModel):
    description: str | None = None
    status: str | None = None
    estimate_tokens: PositiveStrictInt | None = None
    recommended_model: str | None = None
    actual_tokens: NonNegativeStrictInt | None = None
    session_id: str | None = None
    metadata: dict[str, Any] | None = None


class EstimateRequest(BaseModel):
    description: str = Field(min_length=1)
    adapter_id: str | None = None
    remaining_daily_tokens: NonNegativeStrictInt | None = None
    daily_cap_tokens: PositiveStrictInt | None = None
    task_kind: str | None = None


class TaskLaunchRequest(BaseModel):
    adapter_id: str | None = None
    model: str | None = None
    proxy_url: str | None = None
    project_id: str | None = None
    estimate_tokens: PositiveStrictInt | None = None
    budget_override: bool = False
    native_budget_acknowledged: bool = False


class TaskReviewActionRequest(BaseModel):
    action: str = Field(pattern="^(save_prompt|agent_review|mark_done|block|approve_commit|open_pr)$")
    project_id: str | None = None
    review_prompt: str | None = None
    blocked_reason: str | None = None
    approve_commit_reason: str | None = None


class ManualEstimateRequest(BaseModel):
    estimate_tokens: PositiveStrictInt


class RetryReestimateRequest(BaseModel):
    acknowledge_possible_duplicate_spend: bool = False


@router.post("/tasks")
def create_task(payload: TaskCreateRequest, request: Request) -> dict[str, Any]:
    database_path = request.app.state.settings.database_path
    try:
        status, metadata = _initial_task_status_and_metadata(payload, database_path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    metadata = _with_single_project_default(database_path, metadata)
    return db.create_task(
        database_path,
        description=payload.description,
        status=status,
        estimate_tokens=payload.estimate_tokens,
        recommended_model=payload.recommended_model,
        actual_tokens=payload.actual_tokens,
        session_id=payload.session_id,
        metadata=metadata,
    )


@router.put("/tasks/{task_id}")
def update_task(task_id: str, payload: TaskUpdateRequest, request: Request) -> dict[str, Any]:
    database_path = request.app.state.settings.database_path
    try:
        updates = _canonicalize_task_updates(
            database_path,
            db.get_task(database_path, task_id),
            payload.model_dump(exclude_unset=True),
        )
        return db.update_task(
            database_path,
            task_id,
            updates,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="task not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/launch", dependencies=[Depends(require_portal_auth), Depends(require_configured_orchestrator)])
async def launch_task_endpoint(task_id: str, request: Request):
    try:
        payload, wants_html = await _launch_payload_from_request(request)
    except HTTPException as exc:
        if _wants_react_json(request):
            return _react_action_outcome(
                ok=False,
                error=_http_exception_message(exc),
                status_code=exc.status_code,
            )
        raise
    database_path = request.app.state.settings.database_path
    runner = getattr(request.app.state, "task_launch_runner", None)
    try:
        result = launch_task(
            database_path,
            task_id,
            adapter_id=payload.adapter_id,
            model=payload.model,
            proxy_url=payload.proxy_url or DEFAULT_PROXY_URL,
            project_id=payload.project_id,
            estimate_tokens=payload.estimate_tokens,
            budget_override=payload.budget_override,
            native_budget_acknowledged=payload.native_budget_acknowledged,
            budget_since=db.effective_daily_budget_window_start(
                database_path,
                timezone=request.app.state.settings.timezone,
            ),
            runner=runner,
        )
    except KeyError as exc:
        if _wants_react_json(request):
            return _react_action_outcome(ok=False, error="task not found", status_code=404)
        raise HTTPException(status_code=404, detail="task not found") from exc
    except TaskLaunchBlocked as exc:
        diagnostic = (exc.task.get("metadata") or {}).get("launch_diagnostic")
        diagnostic = diagnostic if isinstance(diagnostic, dict) else {}
        if wants_html:
            redirect_path = _board_redirect_for_task(exc.task, payload.project_id)
            if exc.task.get("metadata", {}).get("launch_retryable"):
                # Retryable launch failures already annotate the card; avoid a noisy banner.
                return RedirectResponse(redirect_path, status_code=303)
            error_msg = "; ".join(exc.reasons) if exc.reasons else "Launch failed."
            return RedirectResponse(f"{redirect_path}?error={quote(error_msg)}", status_code=303)
        if _wants_react_json(request):
            return _react_action_outcome(
                ok=False,
                error="; ".join(exc.reasons) or "Launch failed.",
                setup_href=diagnostic.get("setup_href")
                or (f"/settings/workers?adapter_id={quote(payload.adapter_id)}" if payload.adapter_id else "/settings/workers"),
                status_code=exc.status_code,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "task": exc.task,
                "session": exc.task.get("session_id"),
                "launch_guardrails": {"passed": False, "reasons": exc.reasons},
            },
        )
    if wants_html:
        return RedirectResponse(_board_redirect_for_task(result.task, payload.project_id), status_code=303)
    if _wants_react_json(request):
        return _react_action_outcome(ok=True, task=result.task)
    return result.as_response()


@router.post("/tasks/{task_id}/refresh", dependencies=[Depends(require_portal_auth)])
async def refresh_task_endpoint(task_id: str, request: Request):
    content_type = request.headers.get("content-type", "")
    is_form = "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type
    form = await request.form() if is_form else None
    project_id = _form_project_id(form) if form is not None else None
    wants_html = _wants_html(request) or (is_form and not _wants_react_json(request))
    try:
        database_path = request.app.state.settings.database_path
        db.mark_stale_worker_runs_interrupted(database_path)
        current = db.get_task(database_path, task_id)
        _ensure_task_project_binding(current, project_id)
        task = refresh_task_from_session(database_path, task_id)
        if wants_html:
            return RedirectResponse(_board_redirect_for_task(task, project_id), status_code=303)
        if _wants_react_json(request):
            return _react_action_outcome(ok=True, task=task)
        return task
    except KeyError as exc:
        if _wants_react_json(request):
            return _react_action_outcome(ok=False, error="task not found", status_code=404)
        raise HTTPException(status_code=404, detail="task not found") from exc
    except ValueError as exc:
        if wants_html:
            return RedirectResponse(
                f"{_project_board_path(project_id)}?error={quote(str(exc))}",
                status_code=303,
            )
        if _wants_react_json(request):
            return _react_action_outcome(ok=False, error=str(exc), status_code=409)
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/review", dependencies=[Depends(require_portal_auth)])
async def review_task_endpoint(task_id: str, request: Request):
    try:
        payload, wants_html = await _review_action_payload_from_request(request)
    except HTTPException as exc:
        if _wants_react_json(request):
            return _react_action_outcome(
                ok=False,
                error=_http_exception_message(exc),
                status_code=exc.status_code,
            )
        raise
    database_path = request.app.state.settings.database_path
    try:
        task = db.get_task(database_path, task_id)
        _ensure_task_project_binding(task, payload.project_id)
        _ensure_review_task(task, database_path)
        if payload.action == "save_prompt":
            updated = _save_review_prompt(database_path, task, payload.review_prompt)
        elif payload.action == "mark_done":
            updated = _mark_review_done(database_path, task)
        elif payload.action == "block":
            updated = _block_review_task(database_path, task, payload.blocked_reason)
        elif payload.action == "agent_review":
            updated = await _run_agent_review(request, task, payload.review_prompt)
        elif payload.action == "approve_commit":
            updated = _approve_harness_commit(database_path, task, payload.approve_commit_reason)
        elif payload.action == "open_pr":
            updated = _open_pull_request(database_path, task)
        else:  # pragma: no cover - pydantic validation prevents this
            raise HTTPException(status_code=422, detail="unsupported review action")
    except KeyError as exc:
        if _wants_react_json(request):
            return _react_action_outcome(ok=False, error="task not found", status_code=404)
        raise HTTPException(status_code=404, detail="task not found") from exc
    except ValueError as exc:
        if wants_html:
            from urllib.parse import quote

            return RedirectResponse(f"{_board_redirect_for_task(task, payload.project_id)}?error={quote(str(exc))}", status_code=303)
        if _wants_react_json(request):
            return _react_action_outcome(ok=False, error=str(exc), status_code=409)
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if wants_html:
        return RedirectResponse(_board_redirect_for_task(updated, payload.project_id), status_code=303)
    if _wants_react_json(request):
        return _react_action_outcome(ok=True, task=updated)
    return updated


def _estimate_revision_query(request: Request) -> int | None:
    value = request.query_params.get("estimate_revision")
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _attempt_id_query(request: Request) -> str | None:
    value = request.query_params.get("attempt_id")
    return value if value else None


def _estimate_decision_error_response(request: Request, exc: HTTPException) -> JSONResponse:
    if _wants_react_json(request):
        return _react_action_outcome(ok=False, error=_http_exception_message(exc), status_code=exc.status_code)
    raise exc


@router.post("/api/projects/{project_id}/tasks/{task_id}/estimate-decision/acknowledge", dependencies=[Depends(require_portal_auth)])
async def acknowledge_estimate_decision(project_id: str, task_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    try:
        result = acknowledge_low_confidence(database_path, project_id, task_id, _estimate_revision_query(request))
    except HTTPException as exc:
        return _estimate_decision_error_response(request, exc)
    return result


@router.post("/api/projects/{project_id}/tasks/{task_id}/estimate-decision/manual", dependencies=[Depends(require_portal_auth)])
async def manual_estimate_decision(project_id: str, task_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    try:
        body = await request.json()
        estimate_tokens = int(body.get("estimate_tokens", 0))
    except Exception:
        try:
            form = await request.form()
            estimate_tokens = int(form.get("estimate_tokens", 1))
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "invalid request body"})
    try:
        result = apply_manual_estimate(database_path, project_id, task_id, _estimate_revision_query(request), estimate_tokens)
    except HTTPException as exc:
        return _estimate_decision_error_response(request, exc)
    return result


@router.post("/api/projects/{project_id}/tasks/{task_id}/estimate-decision/scout", dependencies=[Depends(require_portal_auth)])
async def create_scout_decision(project_id: str, task_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    try:
        result = await create_scout_for_task(request, database_path, project_id, task_id, _estimate_revision_query(request))
    except HTTPException as exc:
        return _estimate_decision_error_response(request, exc)
    return result


@router.post("/api/projects/{project_id}/tasks/{task_id}/estimate-decision/scout/reestimate", dependencies=[Depends(require_portal_auth)])
async def request_reestimate_decision(project_id: str, task_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    try:
        result = await request_scout_reestimate(request, database_path, project_id, task_id, _estimate_revision_query(request))
    except HTTPException as exc:
        return _estimate_decision_error_response(request, exc)
    return result


@router.post("/api/projects/{project_id}/tasks/{task_id}/estimate-decision/scout/reestimate/retry", dependencies=[Depends(require_portal_auth)])
async def retry_reestimate_decision(project_id: str, task_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    try:
        body = await request.json()
        ack = bool(body.get("acknowledge_possible_duplicate_spend"))
    except Exception:
        try:
            form = await request.form()
            ack = str(form.get("acknowledge_possible_duplicate_spend", "")).lower() in {"1", "true", "on"}
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "invalid request body"})
    try:
        result = await retry_reestimate(request, database_path, project_id, task_id, _estimate_revision_query(request), _attempt_id_query(request), ack)
    except HTTPException as exc:
        return _estimate_decision_error_response(request, exc)
    return result


@router.post("/api/projects/{project_id}/tasks/{task_id}/estimate-decision/scout/reestimate/apply", dependencies=[Depends(require_portal_auth)])
async def apply_reestimate_decision(project_id: str, task_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    try:
        result = apply_reestimate(database_path, project_id, task_id, _estimate_revision_query(request), _attempt_id_query(request))
    except HTTPException as exc:
        return _estimate_decision_error_response(request, exc)
    return result


@router.post("/api/projects/{project_id}/tasks/{task_id}/estimate-decision/scout/reestimate/dismiss", dependencies=[Depends(require_portal_auth)])
async def dismiss_reestimate_decision(project_id: str, task_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    try:
        result = dismiss_reestimate(database_path, project_id, task_id, _estimate_revision_query(request), _attempt_id_query(request))
    except HTTPException as exc:
        return _estimate_decision_error_response(request, exc)
    return result


@router.post("/estimate", dependencies=[Depends(require_portal_auth), Depends(require_configured_orchestrator)])
async def estimate(payload: EstimateRequest, request: Request) -> dict[str, Any]:
    return await _estimate_and_create_task(
        request,
        payload.description,
        adapter_id=payload.adapter_id,
        remaining_daily_tokens=payload.remaining_daily_tokens,
        daily_cap_tokens=payload.daily_cap_tokens,
    )


async def _estimate_and_create_task(
    request: Request,
    description: str,
    *,
    adapter_id: str | None = None,
    remaining_daily_tokens: int | None = None,
    daily_cap_tokens: int | None = None,
    extra_metadata: dict[str, Any] | None = None,
    task_id: str | None = None,
    task_kind: str | None = None,
) -> dict[str, Any]:
    database_path = request.app.state.settings.database_path
    if task_id is not None:
        try:
            return db.get_task(database_path, task_id)
        except KeyError:
            pass
    settings = request.app.state.settings
    estimator_model = settings.estimator_model
    adapter = _selected_worker_adapter(database_path, adapter_id)
    if task_kind is None:
        task_kind = read_task_kind(extra_metadata) if extra_metadata else DEFAULT_TASK_KIND
    try:
        project_root = (extra_metadata or {}).get("project_root_path")
        result, job_result = await estimate_task(
            description,
            request.app.state.guardrails,
            database_path=database_path,
            job_runner=request.app.state.orchestrator_job_runner,
            estimator_model=estimator_model,
            remaining_daily_tokens=remaining_daily_tokens,
            daily_cap_tokens=daily_cap_tokens,
            project_root=project_root,
            project_profile=(extra_metadata or {}).get("project_profile"),
            adapter=adapter,
            task_kind=task_kind,
        )
    except EstimatorError as exc:
        return db.create_task(
            database_path,
            task_id=task_id,
            description=description,
            status="Estimated",
            metadata={
                "blocked_reason": "Estimator unavailable or invalid; manual estimate required.",
                "blocked_condition": _blocked_condition(
                    "Estimator unavailable or invalid; manual estimate required.",
                    "task_estimation",
                ),
                "requires_manual_estimate": True,
                "estimation_source": "manual_required",
                "estimator_failure_type": type(exc).__name__,
                "task_kind": task_kind,
                "estimate_revision": 1,
                **(extra_metadata or {}),
            },
        )

    estimation_session = job_result.session
    # Route Worker model choice after estimation so allowlists and budgets can constrain it.
    model_routing = route_worker_model(
        request.app.state.guardrails,
        complexity=result.complexity,
        estimate_tokens=result.token_estimate,
        remaining_daily_tokens=remaining_daily_tokens,
        daily_cap_tokens=daily_cap_tokens,
        adapter=adapter,
        allowed_models=allowed_worker_model_ids(adapter) if adapter else [],
    )
    metadata = {
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
        "investigation_recommended": result.investigation_recommended,
        **(extra_metadata or {}),
        **model_routing.metadata,
        "task_kind": task_kind,
        "estimate_revision": 1,
    }
    metadata = _with_single_project_default(database_path, metadata)
    task = db.create_task(
        database_path,
        task_id=task_id,
        description=description,
        status="Estimated",
        estimate_tokens=result.token_estimate,
        recommended_model=model_routing.selected_model,
        metadata=metadata,
    )
    return {**task, **result.as_dict(), "recommended_model": model_routing.selected_model}


def _selected_worker_adapter(database_path: Path | str, adapter_id: str | None) -> dict[str, Any] | None:
    if adapter_id:
        try:
            return db.get_worker_adapter(database_path, adapter_id)
        except KeyError:
            return None
    adapters = db.list_worker_adapters(database_path)
    return next((item for item in adapters if item.get("is_default")), adapters[0] if adapters else None)


@router.post("/tasks/estimate-form", dependencies=[Depends(require_portal_auth), Depends(require_configured_orchestrator)])
async def estimate_form(
    request: Request,
    description: str = Form(""),
    task_kind: str = Form(DEFAULT_TASK_KIND),
    markdown_file: UploadFile | None = File(None),
):
    """HTML or negotiated JSON intake: plain text estimates; Markdown is review-first."""
    return await _estimate_form_for_project(request, description=description, task_kind=task_kind, markdown_file=markdown_file)


@router.post("/projects/{project_id}/tasks/estimate-form", dependencies=[Depends(require_portal_auth), Depends(require_configured_orchestrator)])
async def project_estimate_form(
    project_id: str,
    request: Request,
    description: str = Form(""),
    task_kind: str = Form(DEFAULT_TASK_KIND),
    markdown_file: UploadFile | None = File(None),
):
    return await _estimate_form_for_project(
        request,
        description=description,
        task_kind=task_kind,
        markdown_file=markdown_file,
        project_id=project_id,
    )


async def _estimate_form_for_project(
    request: Request,
    *,
    description: str,
    task_kind: str,
    markdown_file: UploadFile | None,
    project_id: str | None = None,
):
    wants_json = _wants_react_json(request)
    project_metadata: dict[str, Any] = {}
    board_path = "/board"
    if project_id:
        board_path = f"/projects/{project_id}"
        try:
            project = db.get_connected_project(request.app.state.settings.database_path, project_id)
        except KeyError as exc:
            if wants_json:
                return _react_action_outcome(
                    ok=False,
                    error="connected project not found",
                    status_code=404,
                )
            raise HTTPException(status_code=404, detail="connected project not found") from exc
        if db.project_is_archived(project):
            error = "restore archived project before adding tasks"
            if wants_json:
                return _react_action_outcome(ok=False, error=error, status_code=409)
            return RedirectResponse(
                f"{board_path}?error={quote(error)}",
                status_code=303,
            )
        project_metadata = project_task_metadata(project)
    try:
        task_kind = validate_task_kind(task_kind)
        if task_kind not in {"implementation", "acceptance_verification"}:
            raise ValueError("short intake task_kind must be implementation or acceptance_verification")
    except ValueError as exc:
        error = str(exc)
        if wants_json:
            return _react_action_outcome(ok=False, error=error, status_code=422)
        return RedirectResponse(f"{board_path}?error={quote(error)}", status_code=303)

    try:
        normalized_description, intake_metadata = await _description_from_intake_form(description, markdown_file)
    except ValueError as exc:
        if wants_json:
            return _react_action_outcome(ok=False, error=str(exc), status_code=422)
        return RedirectResponse(f"{board_path}?error={quote(str(exc))}", status_code=303)

    intake_metadata = _with_single_project_default(
        request.app.state.settings.database_path,
        {"task_kind": task_kind, **intake_metadata, **project_metadata},
    )

    if _requires_task_breakdown_review(normalized_description, intake_metadata):
        # Large or Markdown-shaped intake is reviewed before it becomes board cards.
        breakdown = await _create_task_breakdown_review(request, normalized_description, intake_metadata)
        review_href = f"/task-breakdowns/{breakdown['id']}/review"
        if wants_json:
            return _react_action_outcome(ok=True, next_href=review_href)
        return RedirectResponse(review_href, status_code=303)

    task = await _estimate_and_create_task(
        request,
        normalized_description,
        task_kind=task_kind,
        extra_metadata=intake_metadata,
    )
    if wants_json:
        return _react_action_outcome(ok=True, task=task)
    return RedirectResponse(board_path, status_code=303)


@router.get("/task-breakdowns/{breakdown_id}/review", response_class=HTMLResponse, dependencies=[Depends(require_portal_auth)])
def task_breakdown_review(breakdown_id: str, request: Request):
    from foreman_ai_hq.routes.react_shell import react_shell_or_missing_build

    # Existence stays backend-authoritative: an unknown breakdown is a 404
    # whether or not the frontend is built. The full review context is built by
    # the JSON handoff the shell then calls.
    try:
        db.get_task_breakdown(request.app.state.settings.database_path, breakdown_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="task breakdown not found") from exc
    return react_shell_or_missing_build()


@router.post("/task-breakdowns/{breakdown_id}/accept", dependencies=[Depends(require_portal_auth), Depends(require_configured_orchestrator)])
async def accept_task_breakdown(breakdown_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    wants_json = _wants_react_json(request)
    try:
        breakdown = db.get_task_breakdown(database_path, breakdown_id)
    except KeyError as exc:
        if wants_json:
            return _breakdown_action_outcome(None, status_code=404, error="Task breakdown not found.")
        raise HTTPException(status_code=404, detail="Task breakdown not found") from exc
    if breakdown["status"] == "accepted":
        if wants_json:
            return _breakdown_action_outcome(breakdown, ok=True, next_href=_breakdown_react_board_path(breakdown))
        return RedirectResponse(_breakdown_board_path(breakdown), status_code=303)
    if breakdown.get("status") not in {"proposed", "pending_review"}:
        if wants_json:
            return _breakdown_action_outcome(
                breakdown,
                status_code=409,
                error="Review must be retried or replaced manually before acceptance.",
                retry_href=f"/task-breakdowns/{breakdown_id}/review",
            )
        return RedirectResponse(f"/task-breakdowns/{breakdown_id}/review", status_code=303)

    try:
        form = await request.form()
        candidates = breakdown.get("candidates")
        _validate_breakdown_accept_form(
            form, candidate_count=len(candidates) if isinstance(candidates, list) else 0
        )
        global_contract_summary = _present_text_or_original(
            form, "global_contract_summary", breakdown.get("global_contract_summary")
        )
        if not global_contract_summary:
            raise HTTPException(status_code=422, detail="Task breakdown acceptance is invalid.")
        global_constraints = _present_lines_or_original(
            form, "global_constraints", breakdown.get("global_constraints")
        )
        verification = _present_lines_or_original(form, "verification", breakdown.get("verification"))
        accepted_candidates = _accepted_breakdown_candidates(
            breakdown, form, presence_aware=True
        )
        _validate_scout_target_tasks(database_path, breakdown, accepted_candidates)
        claimed_breakdown = db.update_task_breakdown(
            database_path,
            breakdown_id,
            {
                "status": "accepting",
                "candidates": accepted_candidates,
                "global_contract_summary": global_contract_summary,
                "global_constraints": global_constraints,
                "verification": verification,
                "created_task_ids": [],
            },
            expected_statuses={"proposed", "pending_review"},
            expected_revision=breakdown["revision"],
        )
        if claimed_breakdown is None:
            breakdown = db.get_task_breakdown(database_path, breakdown_id)
            if breakdown["status"] == "accepted":
                if wants_json:
                    return _breakdown_action_outcome(
                        breakdown, ok=True, next_href=_breakdown_react_board_path(breakdown)
                    )
                return RedirectResponse(_breakdown_board_path(breakdown), status_code=303)
            if wants_json:
                return _breakdown_action_outcome(
                    breakdown,
                    status_code=409,
                    error="Task breakdown changed or acceptance is already in progress.",
                    retry_href=f"/task-breakdowns/{breakdown_id}/review",
                )
            return RedirectResponse(f"/task-breakdowns/{breakdown_id}/review", status_code=303)
        breakdown = claimed_breakdown
        created_task_ids: list[str] = []
        for index, candidate in enumerate(accepted_candidates, start=1):
            source_index = candidate["_source_index"]
            description = _breakdown_candidate_description(
                candidate,
                global_contract_summary,
                global_constraints,
                verification,
                source_text=breakdown.get("source_text", ""),
            )
            task = await _estimate_and_create_task(
                request,
                description,
                task_id=_task_breakdown_candidate_task_id(breakdown_id, source_index),
                extra_metadata={
                    **breakdown.get("intake_metadata", {}),
                    "task_kind": candidate["kind"],
                    "task_breakdown_id": breakdown["id"],
                    "task_breakdown_source_sha256": breakdown["source_sha256"],
                    "task_breakdown_decision": breakdown["decision"],
                    "task_breakdown_index": index,
                    "task_breakdown_count": len(accepted_candidates),
                    "task_breakdown_kind": candidate["kind"],
                    "task_breakdown_title": candidate["title"],
                    "task_breakdown_objective": candidate["objective"],
                    "task_breakdown_prompt": candidate["prompt"],
                    "task_breakdown_acceptance_criteria": candidate["acceptance_criteria"],
                    "task_breakdown_constraints": candidate["constraints"],
                    "task_breakdown_proof": candidate["proof"],
                    "task_breakdown_dependencies": candidate["dependencies"],
                    "task_breakdown_likely_entry_points": candidate["likely_entry_points"],
                    "task_breakdown_execution_mode": candidate["execution_mode"],
                    "task_breakdown_hitl_reason": candidate["hitl_reason"],
                    "task_breakdown_policy_evidence": _candidate_policy_evidence(candidate),
                    "task_breakdown_global_contract_summary": global_contract_summary,
                    "task_breakdown_global_constraints": global_constraints,
                    "task_breakdown_verification": verification,
                    "task_breakdown_recommended_last": candidate["kind"] == "acceptance_verification",
                    **(
                        {
                            "scout_question": candidate["objective"],
                            "scout_inspection_boundary": candidate["constraints"],
                            "scout_expected_findings": candidate["acceptance_criteria"],
                            "scout_proof": candidate["proof"],
                            **(
                                {"target_task_id": candidate["target_task_id"]}
                                if candidate.get("target_task_id")
                                else {}
                            ),
                        }
                        if candidate["kind"] == "scout"
                        else {}
                    ),
                },
            )
            created_task_ids.append(task["id"])
            updated_claim = db.update_task_breakdown(
                database_path,
                breakdown_id,
                {"created_task_ids": created_task_ids},
                expected_statuses={"accepting"},
                expected_revision=breakdown["revision"],
            )
            if updated_claim is None:
                raise RuntimeError("Task breakdown acceptance claim was lost.")
            breakdown = updated_claim
        persisted_candidates = [
            {key: value for key, value in candidate.items() if key != "_source_index"}
            for candidate in accepted_candidates
        ]
        created_task_ids = list(
            dict.fromkeys(
                [*created_task_ids, *db.list_task_ids_for_breakdown(database_path, breakdown_id)]
            )
        )
        accepted_breakdown = db.update_task_breakdown(
            database_path,
            breakdown_id,
            {
                "status": "accepted",
                "candidates": persisted_candidates,
                "global_contract_summary": global_contract_summary,
                "global_constraints": global_constraints,
                "verification": verification,
                "created_task_ids": created_task_ids,
            },
            expected_statuses={"accepting"},
            expected_revision=breakdown["revision"],
        )
        if accepted_breakdown is None:
            raise RuntimeError("Task breakdown acceptance claim was lost.")
        breakdown = accepted_breakdown
    except (HTTPException, TaskBreakdownError, ValueError) as exc:
        if wants_json:
            return _breakdown_action_outcome(
                breakdown,
                status_code=422,
                error="Task breakdown acceptance is invalid.",
                retry_href=f"/task-breakdowns/{breakdown_id}/review",
            )
        raise exc
    except Exception:
        if wants_json:
            return _breakdown_action_outcome(
                breakdown,
                status_code=500,
                error="Task breakdown action failed.",
                retry_href=f"/task-breakdowns/{breakdown_id}/review",
            )
        raise
    if wants_json:
        return _breakdown_action_outcome(breakdown, ok=True, next_href=_breakdown_react_board_path(breakdown))
    return RedirectResponse(_breakdown_board_path(breakdown), status_code=303)


@router.post("/task-breakdowns/{breakdown_id}/retry", dependencies=[Depends(require_portal_auth), Depends(require_configured_orchestrator)])
async def retry_task_breakdown(breakdown_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    wants_json = _wants_react_json(request)
    try:
        breakdown = db.get_task_breakdown(database_path, breakdown_id)
    except KeyError as exc:
        if wants_json:
            return _breakdown_action_outcome(None, status_code=404, error="Task breakdown not found.")
        raise HTTPException(status_code=404, detail="Task breakdown not found") from exc
    if breakdown["status"] == "accepted":
        if wants_json:
            return _breakdown_action_outcome(breakdown, ok=True, next_href=_breakdown_react_board_path(breakdown))
        return RedirectResponse(_breakdown_board_path(breakdown), status_code=303)
    if breakdown["status"] == "accepting":
        if wants_json:
            return _breakdown_action_outcome(
                breakdown,
                status_code=409,
                error="Task breakdown acceptance is already in progress.",
                retry_href=f"/task-breakdowns/{breakdown_id}/review",
            )
        return RedirectResponse(f"/task-breakdowns/{breakdown_id}/review", status_code=303)
    try:
        updates = await _task_breakdown_agent_updates(
            request,
            breakdown["source_text"],
            breakdown.get("intake_metadata", {}),
            source_sha256=breakdown["source_sha256"],
        )
        updated_breakdown = db.update_task_breakdown(
            database_path,
            breakdown_id,
            updates,
            expected_statuses={breakdown["status"]},
            expected_revision=breakdown["revision"],
        )
        if updated_breakdown is None:
            breakdown = db.get_task_breakdown(database_path, breakdown_id)
            if breakdown["status"] == "accepted":
                if wants_json:
                    return _breakdown_action_outcome(
                        breakdown, ok=True, next_href=_breakdown_react_board_path(breakdown)
                    )
                return RedirectResponse(_breakdown_board_path(breakdown), status_code=303)
            if wants_json:
                return _breakdown_action_outcome(
                    breakdown,
                    status_code=409,
                    error="Task breakdown changed while Retry was running.",
                    retry_href=f"/task-breakdowns/{breakdown_id}/review",
                )
            return RedirectResponse(f"/task-breakdowns/{breakdown_id}/review", status_code=303)
        breakdown = updated_breakdown
    except Exception:
        if wants_json:
            return _breakdown_action_outcome(
                breakdown,
                status_code=500,
                error="Task breakdown action failed.",
                retry_href=f"/task-breakdowns/{breakdown_id}/review",
            )
        raise
    if wants_json:
        return _breakdown_action_outcome(
            breakdown,
            ok=True,
            next_href=f"/task-breakdowns/{breakdown_id}/review",
        )
    return RedirectResponse(f"/task-breakdowns/{breakdown_id}/review", status_code=303)


@router.post("/task-breakdowns/{breakdown_id}/manual", dependencies=[Depends(require_portal_auth)])
async def manual_task_breakdown_candidate(
    breakdown_id: str,
    request: Request,
):
    database_path = request.app.state.settings.database_path
    wants_json = _wants_react_json(request)
    try:
        breakdown = db.get_task_breakdown(database_path, breakdown_id)
    except KeyError as exc:
        if wants_json:
            return _breakdown_action_outcome(None, status_code=404, error="Task breakdown not found.")
        raise HTTPException(status_code=404, detail="Task breakdown not found") from exc
    if breakdown["status"] == "accepted":
        if wants_json:
            return _breakdown_action_outcome(breakdown, ok=True, next_href=_breakdown_react_board_path(breakdown))
        return RedirectResponse(_breakdown_board_path(breakdown), status_code=303)
    if breakdown["status"] == "accepting":
        if wants_json:
            return _breakdown_action_outcome(
                breakdown,
                status_code=409,
                error="Task breakdown acceptance is already in progress.",
                retry_href=f"/task-breakdowns/{breakdown_id}/review",
            )
        return RedirectResponse(f"/task-breakdowns/{breakdown_id}/review", status_code=303)
    try:
        form = await request.form()
        _validate_manual_breakdown_form(form)
        title = (
            str(form.get("title") or "").strip()
            if "title" in form
            else "Manual task from source"
        )
        prompt = (
            str(form.get("prompt") or "").strip()
            if "prompt" in form
            else str(breakdown.get("source_text") or "").strip()
        )
        if not title or not prompt:
            raise HTTPException(status_code=422, detail="Manual candidate is invalid.")
        acceptance_criteria = str(form.get("acceptance_criteria") or "").strip()
        candidate = {
            "kind": "implementation",
            "title": title,
            "objective": prompt,
            "prompt": prompt,
            "acceptance_criteria": acceptance_criteria,
            "constraints": [],
            "proof": acceptance_criteria or "Operator-provided manual candidate requires manual verification.",
            "why_this_task_exists": "Operator created this manual candidate from the original source.",
            "why_not_smaller": "Manual recovery keeps the source as one reviewed slice until the operator refines it.",
            "why_not_larger": "This manual candidate is scoped to the original Task Breakdown source.",
            "dependencies": [],
            "likely_entry_points": [],
            "execution_mode": "HITL",
            "hitl_reason": "Manual recovery candidate requires operator review.",
            "human_in_loop": True,
        }
        updated_breakdown = db.update_task_breakdown(
            database_path,
            breakdown_id,
            {
                "status": "proposed",
                "decision": "single_task",
                "candidates": [candidate],
                "failure_type": None,
                "failure_message": None,
            },
            expected_statuses={breakdown["status"]},
            expected_revision=breakdown["revision"],
        )
        if updated_breakdown is None:
            breakdown = db.get_task_breakdown(database_path, breakdown_id)
            if breakdown["status"] == "accepted":
                if wants_json:
                    return _breakdown_action_outcome(
                        breakdown, ok=True, next_href=_breakdown_react_board_path(breakdown)
                    )
                return RedirectResponse(_breakdown_board_path(breakdown), status_code=303)
            if wants_json:
                return _breakdown_action_outcome(
                    breakdown,
                    status_code=409,
                    error="Task breakdown changed while Manual recovery was running.",
                    retry_href=f"/task-breakdowns/{breakdown_id}/review",
                )
            return RedirectResponse(f"/task-breakdowns/{breakdown_id}/review", status_code=303)
        breakdown = updated_breakdown
    except (HTTPException, ValueError):
        if wants_json:
            return _breakdown_action_outcome(
                breakdown,
                status_code=422,
                error="Manual candidate is invalid.",
                retry_href=f"/task-breakdowns/{breakdown_id}/review",
            )
        raise
    except Exception:
        if wants_json:
            return _breakdown_action_outcome(
                breakdown,
                status_code=500,
                error="Task breakdown action failed.",
                retry_href=f"/task-breakdowns/{breakdown_id}/review",
            )
        raise
    if wants_json:
        return _breakdown_action_outcome(
            breakdown,
            ok=True,
            next_href=f"/task-breakdowns/{breakdown_id}/review",
        )
    return RedirectResponse(f"/task-breakdowns/{breakdown_id}/review", status_code=303)


def _requires_task_breakdown_review(description: str, intake_metadata: dict[str, Any]) -> bool:
    if intake_metadata.get("intake_source") in {"markdown_paste", "markdown_upload"}:
        return True
    return len(description.split()) >= 120


async def _create_task_breakdown_review(
    request: Request, description: str, intake_metadata: dict[str, Any]
) -> dict[str, Any]:
    database_path = request.app.state.settings.database_path
    source_sha256 = hashlib.sha256(description.encode("utf-8")).hexdigest()
    payload = await _task_breakdown_agent_updates(
        request,
        description,
        intake_metadata,
        source_sha256=source_sha256,
    )
    return db.create_task_breakdown(
        database_path,
        source_text=description,
        source_sha256=source_sha256,
        intake_metadata=intake_metadata,
        **payload,
    )


async def _task_breakdown_agent_updates(
    request: Request,
    description: str,
    intake_metadata: dict[str, Any],
    *,
    source_sha256: str,
) -> dict[str, Any]:
    database_path = request.app.state.settings.database_path
    settings = request.app.state.settings
    model = settings.task_breakdown_model
    repo_context, repo_context_evidence = _build_breakdown_repo_context(intake_metadata)
    try:
        result, job_result = await breakdown_task_source(
            description,
            database_path=database_path,
            job_runner=request.app.state.orchestrator_job_runner,
            task_breakdown_model=model,
            intake_metadata=intake_metadata,
            structure_hints=_markdown_task_items(description),
            repo_context=repo_context,
            timeout_seconds=settings.task_breakdown_timeout_seconds,
        )
        session = job_result.session
        payload = result.as_dict()
        return {
            "status": "proposed",
            "decision": payload["decision"],
            "model": model,
            "session_id": session["id"],
            "candidates": payload["candidates"],
            "rejected_items": payload["rejected_items"],
            "global_contract_summary": payload["global_contract_summary"],
            "global_constraints": payload["global_constraints"],
            "verification": payload["verification"],
            "non_goals": payload["non_goals"],
            "recommended_sequence": payload["recommended_sequence"],
            "repo_context_evidence": repo_context_evidence or {},
            "confidence": payload["confidence"],
            "rationale": payload["rationale"],
            "failure_type": None,
            "failure_message": None,
        }
    except TaskBreakdownError as exc:
        # Keep the failed breakdown visible so the operator can retry or recover manually.
        reason = str(_safe_review_value(str(exc))).strip()
        failure_message = "Task Breakdown Agent failed; retry or create a manual candidate."
        if reason:
            failure_message = f"Task Breakdown Agent failed: {reason}. Retry or create a manual candidate."
        return {
            "status": "failed",
            "decision": "manual_required",
            "model": model,
            "session_id": getattr(exc, "session_id", None),
            "candidates": [],
            "rejected_items": [],
            "global_contract_summary": "",
            "global_constraints": [],
            "verification": [],
            "non_goals": [],
            "recommended_sequence": [],
            "repo_context_evidence": repo_context_evidence or {},
            "confidence": None,
            "rationale": "",
            "failure_type": type(exc).__name__,
            "failure_message": failure_message,
        }


def _build_breakdown_repo_context(intake_metadata: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    project_root = str(intake_metadata.get("project_root_path") or "").strip()
    if not project_root:
        return None, None
    root = Path(project_root).expanduser()
    if not root.is_dir():
        return None, None
    try:
        brief = build_repo_context_brief(root)
    except OSError:
        return None, None
    return brief, _breakdown_repo_context_evidence(brief)


def _breakdown_repo_context_evidence(brief: dict[str, Any]) -> dict[str, Any]:
    documents = [
        str(document.get("path"))
        for document in brief.get("documents", [])
        if isinstance(document, dict) and document.get("path")
    ]
    return {
        "source": "repo_context_brief",
        "project_root": brief.get("project_root"),
        "documents": documents[:10],
        "manifests": list(brief.get("manifests", []))[:10],
        "entrypoints": list(brief.get("entrypoints", []))[:10],
        "test_commands": list(brief.get("test_commands", []))[:10],
        "tracked_files_sample": list(brief.get("tracked_files_sample", []))[:40],
        "text_chars": len(str(brief.get("text") or "")),
    }


_BREAKDOWN_ACCEPT_FIELD_LIMITS = {
    "global_contract_summary": 50_000,
    "global_constraints": 50_000,
    "verification": 50_000,
    "title": 1_000,
    "kind": 64,
    "execution_mode": 64,
    "objective": 20_000,
    "prompt": 100_000,
    "acceptance_criteria": 40_000,
    "proof": 40_000,
    "hitl_reason": 20_000,
    "constraints": 40_000,
    "why_this_task_exists": 20_000,
    "why_not_smaller": 20_000,
    "why_not_larger": 20_000,
    "dependencies": 40_000,
    "likely_entry_points": 40_000,
}


def _breakdown_action_outcome(
    breakdown: dict[str, Any] | None,
    *,
    ok: bool = False,
    error: str | None = None,
    next_href: str | None = None,
    retry_href: str | None = None,
    status_code: int = 200,
    created_task_count: int | None = None,
) -> JSONResponse:
    if breakdown is None:
        breakdown_id = None
        status_value = None
        count = 0
    else:
        breakdown_id = str(breakdown.get("id") or "") or None
        raw_status = breakdown.get("status")
        status_value = "proposed" if raw_status in {"pending_review", "accepting"} else raw_status
        if status_value not in {"proposed", "failed", "accepted"}:
            status_value = "failed"
        stored_ids = breakdown.get("created_task_ids")
        count = len(stored_ids) if isinstance(stored_ids, list) and status_value == "accepted" else 0
    if created_task_count is not None:
        count = created_task_count
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": bool(ok),
            "error": error,
            "next_href": next_href,
            "retry_href": retry_href,
            "breakdown_id": breakdown_id,
            "status": status_value,
            "created_task_count": count,
        },
    )


def _validate_breakdown_accept_form(form: Any, *, candidate_count: int) -> None:
    global_fields = {
        "global_contract_summary",
        "global_constraints",
        "verification",
    }
    candidate_fields = set(_BREAKDOWN_ACCEPT_FIELD_LIMITS) - global_fields
    candidate_fields.add("accept")
    for raw_key, raw_value in form.items():
        key = str(raw_key)
        if key in global_fields:
            field = key
        else:
            match = re.fullmatch(r"([a-z_]+)_(0|[1-9]\d*)", key)
            if (
                not match
                or match.group(1) not in candidate_fields
                or int(match.group(2)) >= candidate_count
            ):
                raise HTTPException(status_code=422, detail="Task breakdown acceptance is invalid.")
            field = match.group(1)
        limit = _BREAKDOWN_ACCEPT_FIELD_LIMITS.get(field)
        if limit is not None and len(str(raw_value)) > limit:
            raise HTTPException(status_code=422, detail="Task breakdown acceptance is invalid.")


def _validate_manual_breakdown_form(form: Any) -> None:
    limits = {"title": 1_000, "prompt": 100_000, "acceptance_criteria": 40_000}
    if any(str(field) not in limits for field in form):
        raise HTTPException(status_code=422, detail="Manual candidate is invalid.")
    for field, limit in limits.items():
        if field in form and len(str(form.get(field) or "")) > limit:
            raise HTTPException(status_code=422, detail="Manual candidate is invalid.")


def _present_text_or_original(form: Any, field: str, original: Any) -> str:
    if field in form:
        return str(form.get(field) or "").strip()
    return original.strip() if isinstance(original, str) else ""


def _present_lines_or_original(form: Any, field: str, original: Any) -> list[str]:
    if field in form:
        return _textarea_lines(str(form.get(field) or ""))
    return [item.strip() for item in original if isinstance(item, str) and item.strip()] if isinstance(original, list) else []


def _accepted_breakdown_candidates(
    breakdown: dict[str, Any], form: Any, *, presence_aware: bool = False
) -> list[dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    source_indexes: list[int] = []
    candidates = breakdown.get("candidates")
    for index, original in enumerate(candidates if isinstance(candidates, list) else []):
        if f"accept_{index}" not in form:
            continue
        original = original if isinstance(original, dict) else {}
        title = _candidate_form_text(form, original, "title", index, presence_aware=presence_aware)
        prompt = _candidate_form_text(form, original, "prompt", index, presence_aware=presence_aware)
        kind = _candidate_form_text(form, original, "kind", index, fallback="implementation", presence_aware=presence_aware)
        objective = _candidate_form_text(form, original, "objective", index, fallback=prompt, presence_aware=presence_aware)
        acceptance_criteria = _candidate_form_text(form, original, "acceptance_criteria", index, presence_aware=presence_aware)
        proof = _candidate_form_text(form, original, "proof", index, fallback=acceptance_criteria, presence_aware=presence_aware)
        execution_mode = _candidate_execution_mode(
            form, original, index, presence_aware=presence_aware
        )
        hitl_reason = _candidate_form_text(
            form,
            original,
            "hitl_reason",
            index,
            presence_aware=presence_aware,
            empty_uses_fallback=not presence_aware,
        )
        if execution_mode == "AFK":
            hitl_reason = ""
        why_this_task_exists = _candidate_form_text(
            form,
            original,
            "why_this_task_exists",
            index,
            fallback=f"{title} is a distinct board-card candidate from the source contract.",
            presence_aware=presence_aware,
        )
        why_not_smaller = _candidate_form_text(
            form,
            original,
            "why_not_smaller",
            index,
            fallback="Smaller substeps would not be independently useful and verifiable.",
            presence_aware=presence_aware,
        )
        why_not_larger = _candidate_form_text(
            form,
            original,
            "why_not_larger",
            index,
            fallback="Merging this with adjacent work would broaden the Worker prompt and weaken reviewability.",
            presence_aware=presence_aware,
        )
        if kind not in {"implementation", "scout", "acceptance_verification"}:
            raise HTTPException(status_code=422, detail="Task breakdown acceptance is invalid.")
        if execution_mode not in {"AFK", "HITL"}:
            raise HTTPException(status_code=422, detail="Task breakdown acceptance is invalid.")
        required = [title, objective, prompt, acceptance_criteria, proof, why_this_task_exists, why_not_smaller, why_not_larger]
        if execution_mode == "HITL" and presence_aware:
            required.append(hitl_reason)
        if any(not value for value in required):
            raise HTTPException(status_code=422, detail="Task breakdown acceptance is invalid.")
        accepted.append(
            {
                "kind": kind,
                "title": title,
                "objective": objective,
                "prompt": prompt,
                "acceptance_criteria": acceptance_criteria,
                "constraints": _candidate_form_lines(form, original, "constraints", index, presence_aware=presence_aware),
                "proof": proof,
                "why_this_task_exists": why_this_task_exists,
                "why_not_smaller": why_not_smaller,
                "why_not_larger": why_not_larger,
                "dependencies": _candidate_form_lines(form, original, "dependencies", index, presence_aware=presence_aware),
                "likely_entry_points": _candidate_form_lines(form, original, "likely_entry_points", index, presence_aware=presence_aware),
                "target_task_id": original.get("target_task_id"),
                "execution_mode": execution_mode,
                "hitl_reason": hitl_reason,
                "human_in_loop": execution_mode == "HITL",
            }
        )
        stored_source_index = original.get("_source_index") if isinstance(original, dict) else None
        source_indexes.append(
            stored_source_index
            if isinstance(stored_source_index, int)
            and not isinstance(stored_source_index, bool)
            and stored_source_index >= 0
            else index
        )
    if not accepted:
        raise HTTPException(status_code=422, detail="Select at least one task candidate to accept.")
    result = validate_breakdown_result(
        {
            "decision": breakdown.get("decision") if breakdown.get("decision") in {"single_task", "proposed_task_breakdown"} else "proposed_task_breakdown",
            "candidates": accepted,
            "rejected_items": [item for item in breakdown.get("rejected_items", []) if isinstance(item, dict)] if isinstance(breakdown.get("rejected_items"), list) else [],
            "global_contract_summary": breakdown.get("global_contract_summary") if isinstance(breakdown.get("global_contract_summary"), str) else "",
            "global_constraints": [item for item in breakdown.get("global_constraints", []) if isinstance(item, str)] if isinstance(breakdown.get("global_constraints"), list) else [],
            "verification": [item for item in breakdown.get("verification", []) if isinstance(item, str)] if isinstance(breakdown.get("verification"), list) else [],
            "non_goals": [item for item in breakdown.get("non_goals", []) if isinstance(item, str)] if isinstance(breakdown.get("non_goals"), list) else [],
            "recommended_sequence": [item for item in breakdown.get("recommended_sequence", []) if isinstance(item, str)] if isinstance(breakdown.get("recommended_sequence"), list) else [],
            "confidence": breakdown.get("confidence") if isinstance(breakdown.get("confidence"), (int, float)) and not isinstance(breakdown.get("confidence"), bool) else 0,
            "rationale": breakdown.get("rationale") if isinstance(breakdown.get("rationale"), str) and breakdown.get("rationale") else "Operator-edited candidate.",
            "source": "llm",
        }
    )
    return [
        {**candidate.as_dict(), "_source_index": source_index}
        for source_index, candidate in zip(source_indexes, result.candidates, strict=True)
    ]


def _validate_scout_target_tasks(
    database_path: Path | str,
    breakdown: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> None:
    intake_metadata = breakdown.get("intake_metadata") or {}
    project_id = intake_metadata.get("connected_project_id")
    for candidate in candidates:
        target_task_id = candidate.get("target_task_id")
        if not target_task_id:
            continue
        if candidate.get("kind") != "scout" or not project_id:
            raise HTTPException(status_code=422, detail="Scout target Task is invalid.")
        try:
            target = db.get_task(database_path, str(target_task_id))
        except KeyError as exc:
            raise HTTPException(status_code=422, detail="Scout target Task is invalid.") from exc
        if not task_matches_project(target, str(project_id)):
            raise HTTPException(status_code=422, detail="Scout target Task is invalid.")


def _task_breakdown_candidate_task_id(breakdown_id: str, source_index: int) -> str:
    digest = hashlib.sha256(f"{breakdown_id}:{source_index}".encode("utf-8")).hexdigest()
    return f"task_{digest[:32]}"


def _candidate_form_text(
    form: Any,
    original: dict[str, Any],
    field: str,
    index: int,
    *,
    fallback: str = "",
    presence_aware: bool = False,
    empty_uses_fallback: bool = False,
) -> str:
    key = f"{field}_{index}"
    if key in form:
        present = str(form.get(key) or "").strip()
        if presence_aware or present:
            return present
        if empty_uses_fallback:
            return fallback.strip()
    value = original.get(field)
    text = value.strip() if isinstance(value, str) else ""
    return text or fallback.strip()


def _candidate_form_lines(
    form: Any,
    original: dict[str, Any],
    field: str,
    index: int,
    *,
    presence_aware: bool = False,
) -> list[str]:
    key = f"{field}_{index}"
    if key in form:
        present = _textarea_lines(str(form.get(key) or ""))
        if presence_aware or present:
            return present
    value = original.get(field)
    return [item.strip() for item in value if isinstance(item, str) and item.strip()] if isinstance(value, list) else []


def _candidate_execution_mode(
    form: Any, original: dict[str, Any], index: int, *, presence_aware: bool = False
) -> str:
    key = f"execution_mode_{index}"
    value = form.get(key)
    if key in form and presence_aware:
        return str(value or "").strip().upper()
    if value is None:
        value = original.get("execution_mode")
    if not isinstance(value, str):
        value = None
    if value is None or value == "":
        return "AFK" if original.get("human_in_loop") is False else "HITL"
    return str(value).strip().upper()


def _candidate_policy_evidence(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "objective": candidate.get("objective", ""),
        "proof": candidate.get("proof", ""),
        "why_this_task_exists": candidate.get("why_this_task_exists", ""),
        "why_not_smaller": candidate.get("why_not_smaller", ""),
        "why_not_larger": candidate.get("why_not_larger", ""),
        "dependencies": list(candidate.get("dependencies", [])),
        "likely_entry_points": list(candidate.get("likely_entry_points", [])),
        "execution_mode": candidate.get("execution_mode", ""),
        "hitl_reason": candidate.get("hitl_reason", ""),
    }


def _breakdown_candidate_description(
    candidate: dict[str, Any],
    global_contract_summary: str,
    global_constraints: list[str],
    verification: list[str],
    *,
    source_text: str,
) -> str:
    sections = [candidate["title"]]
    if candidate.get("objective"):
        sections.extend(["", "Objective:", candidate["objective"]])
    sections.extend(["", "Task instructions:", candidate["prompt"]])
    if global_contract_summary:
        sections.extend(["", "Global contract summary:", global_contract_summary])
    if candidate.get("kind") == "acceptance_verification":
        sections.extend(
            [
                "",
                "Acceptance Verification scope:",
                "Verify the combined artifact against the original source contract. Use the smallest executable proof available and report findings. Do not reimplement the whole source task as one oversized implementation task.",
            ]
        )
        if source_text.strip():
            sections.extend(["", "Original source contract:", source_text.strip()])
    elif candidate.get("kind") == "scout":
        sections.extend(
            [
                "",
                "Scout scope:",
                "This is a read-only investigation. Ask the bounded question, inspect only the declared boundary, collect the expected findings, and report. Do not edit files, run destructive commands, migrations, or commits.",
            ]
        )
    else:
        sections.extend(
            [
                "",
                "Implementation slice scope:",
                "Implement only this slice. Use the global contract summary and constraints as boundaries; do not rerun or re-solve the full source task.",
            ]
        )
    if candidate.get("dependencies"):
        sections.extend(["", "Dependencies:", *[f"- {item}" for item in candidate["dependencies"]]])
    if candidate.get("likely_entry_points"):
        sections.extend(
            ["", "Likely repo entry points:", *[f"- {item}" for item in candidate["likely_entry_points"]]]
        )
    if candidate.get("acceptance_criteria"):
        sections.extend(["", "Acceptance criteria:", candidate["acceptance_criteria"]])
    if candidate.get("proof"):
        sections.extend(["", "Candidate proof:", candidate["proof"]])
    if candidate.get("execution_mode"):
        sections.extend(["", "Execution mode:", candidate["execution_mode"]])
        if candidate.get("execution_mode") == "HITL" and candidate.get("hitl_reason"):
            sections.extend(["HITL reason:", candidate["hitl_reason"]])
    combined_constraints = [*global_constraints, *candidate.get("constraints", [])]
    if combined_constraints:
        sections.extend(["", "Constraints:", *[f"- {item}" for item in combined_constraints]])
    if verification:
        sections.extend(["", "Verification:", *[f"- {item}" for item in verification]])
    return "\n".join(sections).strip()


def _textarea_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


async def _description_from_intake_form(
    description: str, markdown_file: UploadFile | None
) -> tuple[str, dict[str, Any]]:
    if markdown_file and markdown_file.filename:
        filename = Path(markdown_file.filename).name
        if Path(filename).suffix.lower() != ".md":
            raise ValueError("Upload a Markdown .md file or paste Markdown text.")
        raw = await markdown_file.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Markdown upload must be UTF-8 text.") from exc
        normalized = text.strip()
        if not normalized:
            raise ValueError("Markdown upload is empty.")
        return normalized, {"intake_source": "markdown_upload", "intake_filename": filename}

    normalized = description.strip()
    if not normalized:
        raise ValueError("Describe a coding task or upload a Markdown .md file.")
    metadata = {"intake_source": "markdown_paste"} if _looks_like_markdown(normalized) else {"intake_source": "plain_text"}
    return normalized, metadata


def _looks_like_markdown(text: str) -> bool:
    markdown_patterns = (
        r"(?m)^\s{0,3}#{1,6}\s+",
        r"(?m)^\s{0,3}(?:[-+*]\s+|\d+[.)]\s+|>\s*)",
        r"(?m)^\s{0,3}(?:```|~~~)",
        r"(?m)^\s{0,3}(?:[-*_]\s*){3,}$",
        r"!?\[[^\]]+\]\([^\)]+\)",
        r"(?:\*\*|__)[^\n]+?(?:\*\*|__)",
        r"(?<!\*)\*[^*\n]+\*(?!\*)|(?<![\w_])_[^\n]+?_(?![\w_])",
        r"`+[^`\n]+`+",
        r"~~[^\n]+?~~",
        r"<(?:https?://|mailto:)[^>\n]+>",
        r"(?m)^\s*\|?.+\|.+\n\s*\|?\s*:?-{3,}",
    )
    return any(re.search(pattern, text) for pattern in markdown_patterns)


def _markdown_task_items(description: str) -> list[str]:
    items: list[str] = []
    for raw_line in description.splitlines():
        line = raw_line.strip()
        if line.startswith("- [ ]") or line.startswith("- [x]"):
            item = line[5:].strip()
        elif line.startswith("* [ ]") or line.startswith("* [x]"):
            item = line[5:].strip()
        elif line.startswith("- ") or line.startswith("* "):
            item = line[2:].strip()
        elif len(line) > 3 and line[0].isdigit() and line[1:3] == ". ":
            item = line[3:].strip()
        else:
            continue
        if item:
            items.append(item)
    return items


def _markdown_source_title(description: str) -> str | None:
    for raw_line in description.splitlines():
        line = raw_line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip() or None
    return None


async def _review_action_payload_from_request(request: Request) -> tuple[TaskReviewActionRequest, bool]:
    content_type = request.headers.get("content-type", "")
    wants_html = _wants_html(request)
    if "application/json" in content_type:
        try:
            return TaskReviewActionRequest.model_validate(await request.json()), False
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        raw = {key: value for key, value in form.items() if value is not None}
        try:
            return TaskReviewActionRequest.model_validate(raw), not _wants_react_json(request)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
    try:
        return TaskReviewActionRequest.model_validate({}), wants_html
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


def _ensure_review_task(task: dict[str, Any], database_path: Path | str) -> None:
    if task.get("status") != "Review":
        raise ValueError("Review actions are only available for tasks in Review.")
    session_id = task.get("session_id")
    has_completed_session = bool(session_id) and _session_status(database_path, session_id) == "completed"
    has_completed_worker_run = any(
        run.get("status") == "completed" for run in db.list_worker_runs(database_path, task_id=task["id"])
    )
    if not has_completed_session and not has_completed_worker_run:
        raise ValueError("Review actions require completed Worker Run evidence.")


def _save_review_prompt(database_path: Path | str, task: dict[str, Any], prompt: str | None) -> dict[str, Any]:
    metadata = {**task.get("metadata", {})}
    metadata["review_prompt"] = (prompt or "").strip()
    metadata["review_prompt_updated_at"] = _now_iso()
    return db.update_task(database_path, task["id"], {"metadata": metadata})


def _mark_review_done(database_path: Path | str, task: dict[str, Any]) -> dict[str, Any]:
    project, _ = resolve_task_project(database_path, task)
    project_root = str(project["root_path"]) if project else None
    metadata = dict(task.get("metadata", {}))
    harness_commit = metadata.get("harness_commit")
    if harness_commit and isinstance(harness_commit, dict) and project_root:
        profile = project.get("profile") or {}
        base_branch = profile.get("base_branch")
        if base_branch:
            success, reason = _fast_forward_base(Path(project_root), base_branch, harness_commit["sha"])
            if not success:
                # Refuse acceptance, leave the commit and task branch intact, surface the divergence.
                metadata["base_divergence"] = {
                    "base_branch": base_branch,
                    "commit_sha": harness_commit["sha"],
                    "reason": reason,
                    "at": _now_iso(),
                }
                metadata["blocked_condition"] = _blocked_condition(reason, "base_divergence")
                db.update_task(database_path, task["id"], {"metadata": metadata})
                raise ValueError(f"Cannot accept task: {reason}")
        _restore_operator_branch(project_root, metadata.get("operator_branch"))
    for key in (
        "blocked_condition",
        "blocked_reason",
        "launch_blocked_reason",
        "launch_guardrail_reasons",
        "budget_override_available",
        "budget_override_reason",
        "base_divergence",
    ):
        metadata.pop(key, None)
    metadata.update({
        "review_decision": "accepted",
        "reviewed_by": "operator",
        "reviewed_at": _now_iso(),
    })
    return db.update_task(database_path, task["id"], {"status": "Done", "metadata": metadata})


def _block_review_task(database_path: Path | str, task: dict[str, Any], reason: str | None) -> dict[str, Any]:
    blocked_reason = (reason or "").strip()
    if not blocked_reason:
        raise ValueError("Blocked Review tasks require a reason.")
    metadata = {
        **task.get("metadata", {}),
        "review_decision": "blocked",
        "blocked_reason": blocked_reason,
        "blocked_condition": _blocked_condition(blocked_reason, "review_disposition"),
        "reviewed_by": "operator",
        "reviewed_at": _now_iso(),
    }
    return db.update_task(database_path, task["id"], {"status": "Review", "metadata": metadata})


def _approve_harness_commit(database_path: Path | str, task: dict[str, Any], reason: str | None) -> dict[str, Any]:
    if not task.get("session_id"):
        raise ValueError("Approve commit requires a Worker Session.")
    session = db.get_session(database_path, task["session_id"])
    project, _ = resolve_task_project(database_path, task)
    project_root = str(project["root_path"]) if project else None
    if not project_root:
        raise ValueError("Approve commit requires a connected project.")
    metadata = dict(task.get("metadata", {}))
    diff_summary = _git_diff_summary(project_root)
    if not diff_summary["has_changes"]:
        raise ValueError("Approve commit requires uncommitted Worker changes.")
    verification = metadata.get("post_run_verification") or {}
    authorization = {
        "authorized_by": "operator",
        "authorized_at": _now_iso(),
        "reason": (reason or "").strip() or None,
        "verification_did_not_clear": (verification.get("passed") is False) or bool(verification.get("reason")),
    }
    commit = _create_harness_commit(
        project_root,
        task,
        session,
        verification_result=verification if isinstance(verification, dict) else None,
        authorization=authorization,
    )
    if commit is None:
        raise ValueError("No uncommitted changes found; the commit may already exist.")
    _restore_operator_branch(project_root, metadata.get("operator_branch"))
    pr_capability = detect_pr_capability(project_root)
    review_state = _review_disposition_state_after_commit(commit, pr_capability)
    for key in ("launch_blocked_reason", "launch_guardrail_reasons", "blocked_condition"):
        metadata.pop(key, None)
    metadata.update({
        "harness_commit": commit,
        "harness_commit_authorization": authorization,
        "review_disposition_state": review_state,
    })
    return db.update_task(database_path, task["id"], {"metadata": metadata})


def _open_pull_request(database_path: Path | str, task: dict[str, Any]) -> dict[str, Any]:
    project, _ = resolve_task_project(database_path, task)
    project_root = str(project["root_path"]) if project else None
    if not project_root:
        raise ValueError("Open PR requires a connected project.")
    metadata = dict(task.get("metadata", {}))
    harness_commit = metadata.get("harness_commit")
    if not isinstance(harness_commit, dict) or not harness_commit.get("sha"):
        raise ValueError("Open PR requires a Harness-owned commit.")
    pr_capability = metadata.get("pr_capability") or detect_pr_capability(project_root)
    if not pr_capability.get("available"):
        reason = pr_capability.get("reason") or "Pull request capability is not available."
        metadata["pr_unavailable_reason"] = reason
        db.update_task(database_path, task["id"], {"metadata": metadata})
        raise ValueError(reason)
    base_branch = (project.get("profile") or {}).get("base_branch") or metadata.get("operator_branch")
    task_branch = metadata.get("task_branch")
    if not task_branch:
        raise ValueError("Open PR requires a Task branch.")
    session_id = task.get("session_id")
    artifact = db.build_session_artifact(database_path, session_id) if session_id else {}
    token_totals = _token_evidence_summary(artifact)
    verification = metadata.get("post_run_verification") or {}
    body = _pr_body(task, harness_commit, token_totals, verification)
    title = f"[{task['id']}] {task['description'][:80]}"
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                title,
                "--body",
                body,
                "--base",
                base_branch,
                "--head",
                task_branch,
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except FileNotFoundError:
        result = None
    if result is None or result.returncode != 0:
        raw = result.stderr if result else "gh CLI is not installed or not on PATH"
        safe_reason = _safe_pr_reason(raw)
        metadata["pr_failure"] = {
            "reason": safe_reason,
            "attempted_at": _now_iso(),
        }
        db.update_task(database_path, task["id"], {"metadata": metadata})
        raise ValueError(f"Pull request creation failed: {safe_reason}")
    pr_url = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else None
    metadata["pull_request"] = {
        "url": pr_url,
        "base_branch": base_branch,
        "head_branch": task_branch,
        "created_at": _now_iso(),
    }
    db.update_task(database_path, task["id"], {"metadata": metadata})
    return db.get_task(database_path, task["id"])


def _token_evidence_summary(artifact: dict[str, Any]) -> dict[str, Any]:
    token_log = artifact.get("token_log") or []
    total = sum(int(turn.get("total_tokens") or 0) for turn in token_log)
    return {
        "total_tokens": total,
        "session_id": (artifact.get("session") or {}).get("id"),
    }


def _pr_body(task: dict[str, Any], commit: dict[str, Any], token_totals: dict[str, Any], verification: dict[str, Any]) -> str:
    lines = [
        f"Task: {task['id']}",
        f"Session: {token_totals.get('session_id') or task.get('session_id')}",
        f"Harness commit: {commit.get('sha')}",
        f"Tokens: {token_totals.get('total_tokens')}",
        "Verification:",
        f"  passed: {verification.get('passed') if isinstance(verification, dict) else None}",
    ]
    if verification.get("command"):
        lines.append(f"  command: {verification['command']}")
    if verification.get("reason"):
        lines.append(f"  reason: {verification['reason']}")
    return "\n".join(lines)


def _safe_pr_reason(text: str) -> str:
    # Keep the reason human-readable and bounded; do not leak token or credential text.
    safe = _safe_review_value(str(text)) if text else "unknown error"
    return str(safe)[:500]


AGENT_REVIEW_TIMEOUT_SECONDS = 120


async def _run_agent_review(request: Request, task: dict[str, Any], prompt: str | None) -> dict[str, Any]:
    database_path = request.app.state.settings.database_path
    settings = request.app.state.settings
    # Gated here rather than on the route: Review Disposition also carries Mark Done
    # and Block, which spend nothing and must stay available when pi is unconfigured.
    require_configured_orchestrator(request)
    metadata = {**task.get("metadata", {})}
    review_prompt = (prompt or metadata.get("review_prompt") or "").strip()
    if review_prompt:
        metadata["review_prompt"] = review_prompt
        metadata["review_prompt_updated_at"] = _now_iso()

    model = settings.orchestrator_model
    task_description = f"Agent review for task {task['id']}: {task['description']}"
    review: dict[str, Any]
    try:
        result = await request.app.state.orchestrator_job_runner(
            database_path,
            instructions="",
            input_payload=_agent_review_input(task, review_prompt, database_path),
            model=model,
            persona_filename="agent_review.md",
            extension_filename="submit-review.ts",
            submit_tool="submit_review",
            usage_kind="reporting",
            task_description=task_description,
            timeout=AGENT_REVIEW_TIMEOUT_SECONDS,
            result_validator=_validate_agent_review_result,
        )
        review = {
            "status": "completed",
            "summary": result.validated["summary"],
            "recommendation": result.validated["recommendation"],
            "findings": result.validated["findings"],
            "reviewed_at": _now_iso(),
            "review_session_id": result.session["id"],
            "model": model,
            "token_totals": token_totals(db.build_session_artifact(database_path, result.session["id"])),
        }
    except (PiStructuredJobError, PiStructuredOutputError, RuntimeError, TypeError, ValueError) as exc:
        review_session_id = getattr(exc, "session_id", None)
        review = {
            "status": "failed",
            "summary": "Agent Review failed; operator can still mark done or block manually.",
            "findings": [],
            "recommendation": "needs_changes",
            "reviewed_at": _now_iso(),
            "review_session_id": review_session_id,
            "model": model,
            "token_totals": (
                token_totals(db.build_session_artifact(database_path, review_session_id))
                if review_session_id
                else {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            ),
            "error_type": type(getattr(exc, "__cause__", None) or exc).__name__,
            "error": _safe_review_value(str(exc)),
        }

    metadata["agent_review"] = review
    return db.update_task(database_path, task["id"], {"metadata": metadata})


def _agent_review_input(task: dict[str, Any], review_prompt: str, database_path: Path | str) -> dict[str, Any]:
    artifact: dict[str, Any] = {}
    worker_runs: list[dict[str, Any]] = []
    if task.get("session_id"):
        try:
            artifact = db.build_session_artifact(database_path, task["session_id"])
        except KeyError:
            artifact = {}
    if artifact.get("worker_runs"):
        worker_runs = artifact.get("worker_runs", [])
    else:
        worker_runs = db.list_worker_runs(database_path, task_id=task["id"])
    # The reviewer sees sanitized, bounded evidence instead of the full raw session log.
    evidence = {
        "task": {
            "id": task.get("id"),
            "description": task.get("description"),
            "status": task.get("status"),
            "estimate_tokens": task.get("estimate_tokens"),
            "actual_tokens": task.get("actual_tokens"),
            "session_id": task.get("session_id"),
            "metadata": task.get("metadata", {}),
        },
        "operator_focus": review_prompt,
        "session": artifact.get("session", {}),
        "token_log": artifact.get("token_log", [])[-5:],
        "checkpoint_results": artifact.get("checkpoint_results", [])[-5:],
        "worker_runs": worker_runs[-3:],
        "task_branch_diff": _agent_review_diff_summary(database_path, task),
    }
    return _safe_review_value(evidence)


def _agent_review_root_path(database_path: Path | str, task: dict[str, Any]) -> str | None:
    """Resolve the project root for a task, preferring the bound project metadata."""
    metadata = task.get("metadata") or {}
    root_path = metadata.get("project_root_path")
    if root_path:
        return str(root_path)
    project_id = metadata.get("connected_project_id")
    if not project_id:
        return None
    try:
        project = db.get_connected_project(database_path, str(project_id))
    except KeyError:
        return None
    return str(project.get("root_path") or "")


def _harness_commit_diff_summary(root_path: str, sha: str) -> dict[str, Any]:
    """Diff evidence for a commit the Harness already created."""

    def _git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=str(root_path),
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    files = [line for line in _git("show", "--pretty=", "--name-only", sha).splitlines() if line]
    return {
        "has_changes": bool(files),
        "files_changed": files[:50],
        "stat": _git("show", "--pretty=", "--stat", sha)[:2000],
        "porcelain": "\n".join(f"C  {name}" for name in files)[:2000],
        "commit_sha": sha,
    }


def _agent_review_diff_summary(database_path: Path | str, task: dict[str, Any]) -> dict[str, Any]:
    """Bounded git diff evidence for the review payload."""
    root_path = _agent_review_root_path(database_path, task)
    if not root_path:
        return {"has_changes": False, "files_changed": [], "stat": ""}
    # Once the Harness owns a commit the working tree is clean and HEAD is back on the
    # operator's branch, so the reviewed change only exists in that commit.
    harness_commit = (task.get("metadata") or {}).get("harness_commit")
    if isinstance(harness_commit, dict) and harness_commit.get("sha"):
        committed = _harness_commit_diff_summary(root_path, str(harness_commit["sha"]))
        if committed["has_changes"]:
            return committed
    summary = _git_diff_summary(root_path)
    files = summary.get("files_changed") or []
    stat = summary.get("stat") or ""
    porcelain = summary.get("porcelain") or ""
    return {
        "has_changes": summary.get("has_changes", False),
        "files_changed": files[:50],
        "stat": stat[:2000],
        "porcelain": porcelain[:2000],
    }


def _strip_review_markdown(value: Any) -> str:
    """Collapse accidental markdown so a review stays readable in plain text."""
    text = str(value or "")
    text = re.sub(r"```(?:\w+)?", "", text)
    text = text.replace("```", "")
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        line = re.sub(r"^#{1,6}\s+", "", line)
        line = re.sub(r"^>\s*", "", line)
        line = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+)", "", line)
        line = line.replace("**", "").replace("__", "").replace("`", "")
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return " ".join(lines).strip()


def _validate_agent_review_result(arguments: dict[str, Any]) -> dict[str, Any]:
    """Sanitize the ``submit_review`` tool output before it reaches task metadata."""
    if not isinstance(arguments, dict):
        raise ValueError("Agent Review result must be an object.")
    summary = _strip_review_markdown(arguments.get("summary")).strip()
    if not summary:
        raise ValueError("Agent Review summary is required.")
    recommendation = (
        _strip_review_markdown(arguments.get("recommendation")).lower().replace(" ", "_").replace("-", "_")
    )
    if recommendation in {"approve", "approved"}:
        recommendation = "approve"
    elif recommendation in {"block", "blocked"}:
        recommendation = "block"
    else:
        recommendation = "needs_changes"
    findings: list[dict[str, Any]] = []
    raw_findings = arguments.get("findings")
    if isinstance(raw_findings, list):
        for raw in raw_findings:
            if not isinstance(raw, dict):
                continue
            message = _strip_review_markdown(raw.get("message")).strip()
            if not message:
                continue
            message = re.sub(r"^(critical|high|medium|low|info)\s*[:\-]\s+", "", message, flags=re.IGNORECASE)
            severity = _strip_review_markdown(raw.get("severity")).lower().strip() or "info"
            if severity not in {"critical", "high", "medium", "low", "info"}:
                severity = "info"
            finding: dict[str, Any] = {"severity": severity, "message": message}
            path = _strip_review_markdown(raw.get("path")).strip()
            if path:
                finding["path"] = path
            line = raw.get("line")
            if isinstance(line, int) and line > 0:
                finding["line"] = line
            findings.append(finding)
    return {"summary": summary, "recommendation": recommendation, "findings": findings}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _current_day_start_iso(timezone: str) -> str:
    return db.current_day_start_iso(timezone)


def _form_project_id(form: Any) -> str | None:
    value = form.get("project_id") if hasattr(form, "get") else None
    return str(value) if value else None


def _ensure_task_project_binding(task: dict[str, Any], project_id: str | None) -> None:
    if not project_id:
        return
    raw_metadata = task.get("metadata")
    metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
    if str(metadata.get("connected_project_id") or "") != str(project_id):
        raise ValueError("Task does not belong to the selected project.")


def _project_board_path(project_id: str | None) -> str:
    if project_id:
        return f"/projects/{project_id}"
    return "/board"


def _board_redirect_for_task(task: dict[str, Any], project_id: str | None = None) -> str:
    task_board_path = task_project_board_path(task)
    if task_board_path != "/board":
        return f"{task_board_path}/floor" if task.get("status") in {"Running", "Review", "Done"} else task_board_path
    return _project_board_path(project_id)


def _with_single_project_default(database_path: Path | str, metadata: dict[str, Any]) -> dict[str, Any]:
    if metadata.get("connected_project_id"):
        return metadata
    projects = db.list_connected_projects(database_path)
    if len(projects) != 1:
        return metadata
    return {**project_task_metadata(projects[0]), **metadata}


def _breakdown_board_path(breakdown: dict[str, Any]) -> str:
    return task_project_board_path(breakdown.get("intake_metadata", {}))


def _breakdown_react_board_path(breakdown: dict[str, Any]) -> str:
    return _breakdown_board_path(breakdown)


async def _launch_payload_from_request(request: Request) -> tuple[TaskLaunchRequest, bool]:
    content_type = request.headers.get("content-type", "")
    wants_html = _wants_html(request)
    if "application/json" in content_type:
        raw = await request.json()
        try:
            return TaskLaunchRequest.model_validate(raw or {}), False
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        raw: dict[str, Any] = {key: value for key, value in form.items() if value not in (None, "")}
        if "estimate_tokens" in raw:
            estimate_value = raw["estimate_tokens"]
            if not isinstance(estimate_value, str) or not estimate_value.isdecimal() or int(estimate_value) <= 0:
                raise HTTPException(
                    status_code=422,
                    detail=[{"loc": ["body", "estimate_tokens"], "msg": "Input should be a positive integer"}],
                )
            raw["estimate_tokens"] = int(estimate_value)
        raw["budget_override"] = "budget_override" in raw
        raw["native_budget_acknowledged"] = "native_budget_acknowledged" in raw
        raw.setdefault("proxy_url", DEFAULT_PROXY_URL)
        try:
            return TaskLaunchRequest.model_validate(raw), not _wants_react_json(request)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc

    return TaskLaunchRequest(proxy_url=DEFAULT_PROXY_URL), wants_html


def _wants_html(request: Request) -> bool:
    return _accepts_media_type(request, "text/html") and not _wants_react_json(request)


def _wants_react_json(request: Request) -> bool:
    return _accepts_media_type(request, "application/json")


def _accepts_media_type(request: Request, media_type: str) -> bool:
    for media_range in request.headers.get("accept", "").split(","):
        parts = [part.strip() for part in media_range.split(";")]
        if not parts or parts[0].lower() != media_type:
            continue
        quality = 1.0
        for parameter in parts[1:]:
            name, separator, value = parameter.partition("=")
            if separator and name.strip().lower() == "q":
                try:
                    quality = float(value.strip())
                except ValueError:
                    quality = 0.0
        if quality > 0:
            return True
    return False


def _react_action_outcome(
    *,
    ok: bool,
    error: str | None = None,
    setup_href: str | None = None,
    next_href: str | None = None,
    task: dict[str, Any] | None = None,
    status_code: int = 200,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": ok,
            "error": str(_safe_review_value(error)) if error else None,
            "setup_href": setup_href,
            "next_href": next_href,
            "task": {"id": task.get("id"), "status": task.get("status")} if task else None,
        },
    )


def _http_exception_message(exc: HTTPException) -> str:
    if not isinstance(exc.detail, list):
        return str(exc.detail)
    messages: list[str] = []
    for item in exc.detail:
        if not isinstance(item, dict):
            messages.append(str(item))
            continue
        location = ".".join(str(part) for part in item.get("loc", []) if part != "body")
        message = str(item.get("msg") or "Invalid value")
        messages.append(f"{location}: {message}" if location else message)
    return "; ".join(messages) or "Invalid request"


def _task_kind_metadata(metadata: dict[str, Any] | None, default: str = DEFAULT_TASK_KIND) -> dict[str, Any]:
    """Validate and normalize task_kind in metadata, defaulting on absence.

    Rejects invalid kinds before Task creation or mutation; preserves valid
    legacy task_breakdown_kind for the canonical reader.
    """

    metadata = dict(metadata or {})
    supplied = metadata.get("task_kind")
    if supplied is not None:
        metadata["task_kind"] = validate_task_kind(supplied)
    elif default:
        metadata["task_kind"] = default
    return metadata


def _initial_task_status_and_metadata(
    payload: TaskCreateRequest, database_path: Path | str
) -> tuple[str, dict[str, Any]]:
    metadata = _task_kind_metadata(payload.metadata, default=DEFAULT_TASK_KIND)
    has_estimate = payload.estimate_tokens is not None and bool(payload.recommended_model)
    if payload.status is not None:
        # Direct task writes cannot bypass the estimate/launch/review lifecycle routes.
        normalized_status = "Estimated" if payload.status == "Ready" else payload.status
        if normalized_status in CANONICAL_TASK_STATUSES:
            lifecycle_status = _constrain_direct_lifecycle_status(
                database_path,
                requested_status=normalized_status,
                session_id=payload.session_id,
                metadata=metadata,
            )
            if lifecycle_status is not None:
                return lifecycle_status, metadata
            if not has_estimate:
                metadata.setdefault("blocked_reason", "Estimate task before launch.")
                metadata.setdefault("requires_manual_estimate", True)
                metadata.setdefault("requested_status", payload.status)
                metadata.setdefault(
                    "blocked_condition",
                    _blocked_condition("Estimate task before launch.", "task_create"),
                )
                return "Estimated", metadata
            return normalized_status, metadata
        metadata.setdefault("blocked_reason", f"Unsupported task status: {payload.status}")
        metadata.setdefault("original_status", payload.status)
        metadata.setdefault(
            "blocked_condition",
            _blocked_condition(f"Unsupported task status: {payload.status}", "task_create"),
        )
        return "Estimated", metadata
    if has_estimate:
        return "Estimated", metadata
    metadata.setdefault("blocked_reason", "Estimate task before launch.")
    metadata.setdefault("requires_manual_estimate", True)
    metadata.setdefault(
        "blocked_condition", _blocked_condition("Estimate task before launch.", "task_create")
    )
    return "Estimated", metadata


def _canonicalize_task_updates(
    database_path: Path | str, current: dict[str, Any], updates: dict[str, Any]
) -> dict[str, Any]:
    metadata = {**current.get("metadata", {}), **updates.get("metadata", {})}
    metadata = _task_kind_metadata(metadata, default=None)
    estimate_tokens = updates.get("estimate_tokens", current.get("estimate_tokens"))
    recommended_model = updates.get("recommended_model", current.get("recommended_model"))
    if (
        ("estimate_tokens" in updates or "recommended_model" in updates)
        and estimate_tokens is not None
        and recommended_model
    ):
        metadata["estimation_source"] = "manual"
        updates["metadata"] = metadata

    if "status" not in updates:
        return updates

    requested_status = "Estimated" if updates["status"] == "Ready" else updates["status"]
    if requested_status not in CANONICAL_TASK_STATUSES:
        updates["status"] = (
            current.get("status") if current.get("status") in CANONICAL_TASK_STATUSES else "Estimated"
        )
        metadata.setdefault("blocked_reason", f"Unsupported task status: {requested_status}")
        metadata.setdefault("original_status", requested_status)
        metadata.setdefault(
            "blocked_condition",
            _blocked_condition(f"Unsupported task status: {requested_status}", "task_update"),
        )
        updates["metadata"] = metadata
        return updates

    updates["status"] = requested_status

    lifecycle_status = _constrain_direct_lifecycle_status(
        database_path,
        requested_status=requested_status,
        session_id=updates.get("session_id", current.get("session_id")),
        metadata=metadata,
    )
    if lifecycle_status is not None:
        updates["status"] = lifecycle_status
        updates["metadata"] = metadata
        return updates

    if requested_status == "Estimated" and (
        estimate_tokens is None or not recommended_model
    ):
        updates["status"] = "Estimated"
        metadata.setdefault("blocked_reason", "Estimate task before launch.")
        metadata.setdefault("requires_manual_estimate", True)
        metadata.setdefault("requested_status", requested_status)
        metadata.setdefault(
            "blocked_condition",
            _blocked_condition("Estimate task before launch.", "task_update"),
        )
        updates["metadata"] = metadata
    return updates


def _constrain_direct_lifecycle_status(
    database_path: Path | str,
    *,
    requested_status: str,
    session_id: str | None,
    metadata: dict[str, Any],
) -> str | None:
    if requested_status == "Running":
        # Running has launch side effects, so callers must use the launch endpoint.
        metadata.setdefault("blocked_reason", "Use launch endpoint to start tasks.")
        metadata.setdefault("requested_status", requested_status)
        metadata.setdefault(
            "blocked_condition",
            _blocked_condition("Use launch endpoint to start tasks.", "lifecycle_guard"),
        )
        return "Estimated"
    if requested_status in {"Done", "Review"}:
        if session_id and _session_status(database_path, session_id) == "completed":
            return None
        metadata.setdefault("blocked_reason", "Use refresh endpoint to finalize completed sessions.")
        metadata.setdefault("requested_status", requested_status)
        metadata.setdefault(
            "blocked_condition",
            _blocked_condition("Use refresh endpoint to finalize completed sessions.", "lifecycle_guard"),
        )
        return "Estimated"
    return None


def _blocked_condition(reason: str, origin: str) -> dict[str, str]:
    return {"reason": reason, "origin": origin, "timestamp": _now_iso()}


def _session_status(database_path: Path | str, session_id: str) -> str | None:
    try:
        return str(db.get_session(database_path, session_id).get("status"))
    except KeyError:
        return None
