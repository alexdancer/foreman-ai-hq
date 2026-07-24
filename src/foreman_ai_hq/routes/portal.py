from __future__ import annotations

import os
import re
import secrets

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from foreman_ai_hq import db
from foreman_ai_hq.auth import (
    PORTAL_COOKIE_MAX_AGE_SECONDS,
    PORTAL_COOKIE_NAME,
    require_portal_auth,
    sign_portal_cookie,
)
from foreman_ai_hq.board_automation import (
    RUN_NEXT_SOURCE,
    RUN_QUEUE_SOURCE,
    get_run_automation_state,
    list_eligible_estimated_tasks,
    record_automation_event,
    set_active_automation_run,
    start_run_automation,
    stop_run_automation,
)
from foreman_ai_hq.board_workspace import (
    board_page_context as _board_page_context,
    project_board_counts as _project_board_counts,
    project_has_running_work as _project_has_running_work,
    project_task_history_context as _project_task_history_context,
    project_workspace_summary as _project_workspace_summary,
    refresh_project_board_tasks as _refresh_project_board_tasks,
)
from foreman_ai_hq.execution_backend import LocalExecutionBackend
from foreman_ai_hq.evidence_reporting import (
    daily_cap_tokens as _daily_cap_tokens,
    safe_evidence as _safe_worker_evidence,
    session_evidence_summary as _session_evidence_summary,
    token_component_summary_from_log as _token_component_summary_from_log,
    token_totals as _token_totals,
)
from foreman_ai_hq.guardrails import get_budget_zone
from foreman_ai_hq.llm import LLMClient, extract_usage, resolve_cost, response_to_dict
from foreman_ai_hq.operator_config import (
    control_plane_provider_defaults,
    ensure_secret_placeholder,
    load_operator_secrets_env,
    update_operator_config,
    write_control_plane_secret,
)
from foreman_ai_hq.project_context import task_project_id
from foreman_ai_hq.routes.react_shell import _budget_json, react_shell_or_missing_build
from foreman_ai_hq.settings import Settings
from foreman_ai_hq.task_launch import DEFAULT_PROXY_URL, TaskLaunchBlocked, launch_task, refresh_task_from_session
from foreman_ai_hq.routes.tasks import _ensure_review_task, _run_agent_review, _wants_react_json
from foreman_ai_hq.template_context import portal_template_context
from foreman_ai_hq.worker_setup_view import (
    active_adapter_for_request as _active_adapter_for_request,
    validate_worker_tracking_mode as _validate_worker_tracking_mode,
    worker_adapter_view_models as _worker_adapter_view_models,
    worker_setup_next_action as _worker_setup_next_action,
)
from foreman_ai_hq.worker_adapters import (
    detect_worker_adapter,
    discover_worker_models,
    discovered_worker_model_ids,
    verify_worker_adapter,
)



router = APIRouter()
templates = Jinja2Templates(
    directory=Path(__file__).resolve().parents[1] / "templates",
    context_processors=[portal_template_context],
)


def _react_action_outcome(
    request: Request,
    *,
    ok: bool,
    error: str | None = None,
    next_href: str | None = None,
    setup_href: str | None = None,
    task: dict[str, Any] | None = None,
    automation: dict[str, Any] | None = None,
    status_code: int = 200,
) -> JSONResponse:
    content = {
        "ok": ok,
        "error": str(_safe_worker_evidence(error)) if error else None,
        "setup_href": setup_href,
        "next_href": next_href,
        "task": {"id": task.get("id"), "status": task.get("status")} if task else None,
    }
    if automation is not None:
        content["automation"] = automation
    return JSONResponse(status_code=status_code, content=content)


def _react_budget_outcome(
    *,
    ok: bool,
    budget: dict[str, Any] | None = None,
    error: str | None = None,
    status_code: int = 200,
) -> JSONResponse:
    """Bounded JSON outcome for budget save/reset actions."""

    return JSONResponse(
        status_code=status_code,
        content={
            "ok": ok,
            "error": str(_safe_worker_evidence(error)) if error else None,
            "budget": _budget_json(budget) if budget else None,
        },
    )


def _react_worker_settings_outcome(
    *,
    ok: bool,
    error: str | None = None,
    status_code: int = 200,
) -> JSONResponse:
    """Bounded JSON outcome for the Worker Settings redirect-only mutations."""

    return JSONResponse(
        status_code=status_code,
        content={
            "ok": ok,
            "error": str(_safe_worker_evidence(error))[:1000] if error else None,
        },
    )


def _react_restore_outcome(
    *,
    ok: bool,
    project: dict[str, Any] | None = None,
    error: str | None = None,
    status_code: int = 200,
) -> JSONResponse:
    project_id = str(_safe_worker_evidence(project["id"]))[:128] if project else None
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": ok,
            "error": str(_safe_worker_evidence(error))[:1000] if error else None,
            "next_href": f"/projects/{project_id}" if project else None,
            "retry_href": None if project else "/projects",
            "project": {"id": project_id, "archived": False} if project else None,
        },
    )


def _react_unarchive_outcome(task: dict[str, Any]) -> JSONResponse:
    """Bounded JSON outcome for the React Unarchive action."""

    return JSONResponse(
        content={
            "ok": True,
            "task_id": str(task.get("id", ""))[:200],
            "status": str(task.get("status", ""))[:64],
            "archived": bool(db.task_is_archived(task)),
        }
    )


def _react_automation_state(database_path: Path | str, project_id: str) -> dict[str, Any]:
    state = get_run_automation_state(database_path, project_id)
    return {
        "status": state.get("status"),
        "auto_agent_review": bool(state.get("auto_agent_review")),
        "latest_stop_reason": state.get("latest_stop_reason"),
    }


def _task_setup_href(task: dict[str, Any] | None) -> str | None:
    metadata = task.get("metadata") if isinstance(task, dict) else None
    diagnostic = metadata.get("launch_diagnostic") if isinstance(metadata, dict) else None
    setup_href = diagnostic.get("setup_href") if isinstance(diagnostic, dict) else None
    if isinstance(setup_href, str) and setup_href.startswith("/") and not setup_href.startswith("//"):
        return setup_href
    return None

class WorkerVerifyRequest(BaseModel):
    model: str = Field(min_length=1)
    proxy_url: str = Field(default=DEFAULT_PROXY_URL, min_length=1)
    tracking_mode: str = Field(default="proxy_governed", pattern="^(proxy_governed|native_usage|observed_only)$")


class ProjectConnectRequest(BaseModel):
    root_path: str = Field(min_length=1)


class WorkerConfigureRequest(BaseModel):
    is_default: bool = False


class TokenBudgetSettingsRequest(BaseModel):
    daily_cap_tokens: int = Field(gt=0)
    session_cap_tokens: int = Field(gt=0)


class ControlPlaneSettingsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    control_plane_provider: str = Field(min_length=1, pattern="^(openai|anthropic|openai-compatible|openrouter)$")
    orchestrator_model: str = Field(min_length=1, alias="control_plane_model")
    control_plane_base_url: str = ""
    control_plane_api_key_env: str = ""
    control_plane_api_key: str = ""
    apply_to_estimator_breakdown: bool = True

    @field_validator("orchestrator_model")
    @classmethod
    def _model_must_not_be_blank(cls, value: str) -> str:
        model = value.strip()
        if not model:
            raise ValueError("model must not be blank")
        if model == "__custom__":
            raise ValueError("custom model value is required")
        return model

    @field_validator("control_plane_base_url")
    @classmethod
    def _base_url_must_be_http_url(cls, value: str) -> str:
        base_url = value.strip()
        if not base_url:
            return ""
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base URL must be an http(s) URL")
        return base_url.rstrip("/")

    @field_validator("control_plane_api_key")
    @classmethod
    def _api_key_blank_means_keep_existing(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def _compatible_provider_requires_base_url(self) -> "ControlPlaneSettingsRequest":
        defaults = control_plane_provider_defaults(self.control_plane_provider)
        if not self.control_plane_api_key_env:
            self.control_plane_api_key_env = defaults.get("control_plane_api_key_env", "")
        if not self.control_plane_base_url:
            self.control_plane_base_url = defaults.get("control_plane_base_url", "")
        if self.control_plane_provider == "openai-compatible" and not self.control_plane_base_url:
            raise ValueError("openai-compatible provider requires a base URL")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", self.control_plane_api_key_env):
            raise ValueError("API key env name is invalid")
        return self


# Authoritative curated control-plane provider/model choices. Every renderer
# (JSON handoff and React shell) consumes this list so the dropdown cannot drift
# between surfaces.
CURATED_CONTROL_PLANE_MODELS: tuple[tuple[str, str, str], ...] = (
    ("openai", "gpt-5.6-sol", "OpenAI · gpt-5.6-sol"),
    ("openai", "gpt-5.6-terra", "OpenAI · gpt-5.6-terra"),
    ("openai", "gpt-5.6-luna", "OpenAI · gpt-5.6-luna"),
    ("anthropic", "claude-fable-5", "Anthropic · Claude Fable 5"),
    ("anthropic", "claude-sonnet-5", "Anthropic · Claude Sonnet 5"),
    ("anthropic", "claude-opus-4-8", "Anthropic · Claude Opus 4.8"),
    ("anthropic", "claude-haiku-4-5", "Anthropic · Claude Haiku 4.5"),
    ("openrouter", "anthropic/claude-sonnet-5", "OpenRouter · Claude Sonnet 5 (recommended)"),
    ("openrouter", "openai/gpt-5.6-terra", "OpenRouter · GPT-5.6 Terra (recommended)"),
    ("openrouter", "google/gemini-3.5-flash", "OpenRouter · Gemini 3.5 Flash (recommended)"),
)


@router.get("/")
def root(request: Request) -> RedirectResponse:
    if request.app.state.settings.portal_auth_required:
        try:
            require_portal_auth(request)
        except HTTPException:
            return RedirectResponse("/login")
    return RedirectResponse("/dashboard")


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if not request.app.state.settings.portal_auth_required:
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse(request, "login.html", {"active_page": "login"})


_LOGIN_ERROR_MESSAGE = "Invalid portal token. Check the configured portal token and try again."


@router.post("/login")
def login(request: Request, token: str = Form(default="")):
    if not request.app.state.settings.portal_auth_required:
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    expected_token = os.getenv(request.app.state.settings.portal_token_env, "")
    # Constant-time comparison avoids revealing partial token matches.
    # The same sanitized error is shown for every rejection cause.
    if not expected_token or not token or not secrets.compare_digest(token, expected_token):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"active_page": "login", "error": _LOGIN_ERROR_MESSAGE},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    response = RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        PORTAL_COOKIE_NAME,
        sign_portal_cookie(expected_token),
        max_age=PORTAL_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=request.app.state.settings.portal_cookie_secure,
    )
    return response


@router.post("/logout")
def logout(request: Request):
    redirect_to = "/login"
    if not request.app.state.settings.portal_auth_required:
        redirect_to = "/dashboard"
    response = RedirectResponse(redirect_to, status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(
        PORTAL_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=request.app.state.settings.portal_cookie_secure,
    )
    return response


@router.get("/dashboard", response_class=HTMLResponse, dependencies=[Depends(require_portal_auth)])
def dashboard(request: Request):
    return react_shell_or_missing_build()


def _dashboard_context(request: Request) -> dict[str, Any]:
    """Shared dashboard state for the bounded React JSON view."""

    database_path = request.app.state.settings.database_path
    config = request.app.state.guardrails
    budget_since = db.effective_daily_budget_window_start(database_path, timezone=request.app.state.settings.timezone)
    token_breakdown = db.token_usage_breakdown(database_path, since=budget_since)
    worker_token_summary = db.worker_execution_token_summary(database_path, since=budget_since)
    budget_token_total = db.budgeted_token_usage(database_path, since=budget_since)
    budget_settings = _effective_budget_settings(database_path, config, timezone=request.app.state.settings.timezone)
    daily_cap = budget_settings.get("daily_cap_tokens")
    alarms = db.list_alarms(database_path)
    sessions = db.list_sessions(database_path)
    active_sessions = [session for session in sessions if session["status"] in {"active", "running"}]
    open_alarms = [alarm for alarm in alarms if not alarm.get("resolved_at")]
    critical_alarms = [
        alarm
        for alarm in open_alarms
        if str(alarm.get("severity", "")).lower() in {"critical", "high"}
    ]
    tasks = db.list_tasks(database_path)
    ready_task_count = sum(1 for task in tasks if task.get("status") in {"Estimated", "Ready"})
    review_task_count = sum(1 for task in tasks if task.get("status") == "Review")
    has_launchable_worker = any(adapter.get("launchable") for adapter in _worker_adapter_view_models(database_path))
    next_actions = _dashboard_next_actions(
        ready_task_count=ready_task_count,
        review_task_count=review_task_count,
        has_launchable_worker=has_launchable_worker,
        open_alarm_count=len(open_alarms),
        critical_alarm_count=len(critical_alarms),
    )
    accuracy = db.estimation_accuracy(database_path)
    return {
        "active_page": "dashboard",
        "next_actions": next_actions,
        "token_total": budget_token_total,
        "budget_token_total": budget_token_total,
        "worker_token_total": token_breakdown["by_category"]["worker_execution"],
        "worker_token_summary": worker_token_summary,
        "token_breakdown": token_breakdown,
        "budget_since": budget_since,
        "daily_cap": daily_cap,
        "current_zone": get_budget_zone(budget_token_total, daily_cap, config),
        "alarm_count": len(alarms),
        "open_alarm_count": len(open_alarms),
        "critical_alarm_count": len(critical_alarms),
        "active_sessions": list(reversed(active_sessions[-5:])),
        "recent_sessions": list(reversed(sessions[-5:])),
        "recent_alarms": list(reversed(open_alarms[-5:])),
        "estimation_accuracy": accuracy,
    }


def _dashboard_next_actions(
    *,
    ready_task_count: int,
    review_task_count: int,
    has_launchable_worker: bool,
    open_alarm_count: int,
    critical_alarm_count: int,
) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    if not has_launchable_worker:
        actions.append(
            {
                "label": "Set up Worker adapter",
                "detail": "No launchable Worker adapter",
                "href": "/settings/workers",
                "tone": "yellow",
            }
        )
    if review_task_count:
        actions.append(
            {
                "label": f"Review {review_task_count} task{'s' if review_task_count != 1 else ''}",
                "detail": "Awaiting operator review",
                "href": "/board",
                "tone": "purple",
            }
        )
    if ready_task_count:
        actions.append(
            {
                "label": f"Launch {ready_task_count} estimated task{'s' if ready_task_count != 1 else ''}",
                "detail": "Ready on task board",
                "href": "/board",
                "tone": "blue",
            }
        )
    if critical_alarm_count:
        actions.append(
            {
                "label": f"Handle {critical_alarm_count} critical alarm{'s' if critical_alarm_count != 1 else ''}",
                "detail": "High priority alarm inbox",
                "href": "/alarms",
                "tone": "red",
            }
        )
    elif open_alarm_count:
        actions.append(
            {
                "label": f"Review {open_alarm_count} open alarm{'s' if open_alarm_count != 1 else ''}",
                "detail": "Alarm inbox",
                "href": "/alarms",
                "tone": "yellow",
            }
        )
    actions.append(
        {
            "label": "Open task board",
            "detail": "Estimate, launch, refresh, review, or block tasks",
            "href": "/board",
            "tone": "green",
        }
    )
    return actions


@router.get("/projects", response_class=HTMLResponse, dependencies=[Depends(require_portal_auth)])
def projects(request: Request):
    return react_shell_or_missing_build()


@router.get("/projects/{project_id}", response_class=HTMLResponse, dependencies=[Depends(require_portal_auth)])
def project_workspace(project_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    # Existence stays backend-authoritative: an unknown project is a 404 whether
    # or not the frontend is built.
    try:
        db.get_connected_project(database_path, project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="connected project not found") from exc
    return react_shell_or_missing_build()


@router.get("/projects/{project_id}/floor", response_class=HTMLResponse, dependencies=[Depends(require_portal_auth)])
def project_execution_floor(project_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    try:
        db.get_connected_project(database_path, project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="connected project not found") from exc
    return react_shell_or_missing_build()


@router.get("/projects/{project_id}/plan", response_class=HTMLResponse, dependencies=[Depends(require_portal_auth)])
def project_planning_chat(project_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    try:
        db.get_connected_project(database_path, project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="connected project not found") from exc
    return react_shell_or_missing_build()


def _setup_overview_state(request: Request) -> dict[str, Any]:
    """Readiness steps and next action for the Setup Overview surface.

    Both the server-rendered recovery and the React JSON handoff render this one
    computation, so the fallback stays a parity oracle instead of a second
    implementation.
    """

    database_path = request.app.state.settings.database_path
    config = request.app.state.guardrails
    settings = request.app.state.settings
    budget_settings = _effective_budget_settings(database_path, config, timezone=settings.timezone)
    adapters = _worker_adapter_view_models(database_path)
    active_adapter = _active_adapter_for_request(adapters, request.query_params.get("adapter_id"))
    connected_projects = db.list_connected_projects(database_path)
    backend = _local_backend(request)
    projects = [_project_view_model(request, project) for project in connected_projects] if backend else []
    launch_ready_project = next(
        (project for project in projects if (project.get("capability") or {}).get("state") == "launch_ready"),
        None,
    )
    try:
        control_status = db.get_execution_backend_status(database_path, "control_plane_model")
    except KeyError:
        control_status = None

    # Carry the operator's adapter context onward so Worker settings opens the adapter shown here.
    worker_href = "/settings/workers"
    if active_adapter:
        worker_href = f"/settings/workers?adapter_id={active_adapter['id']}"

    steps = [
        {
            "name": "Control plane model",
            "state": _control_plane_setup_state(settings, control_status),
            "href": "/settings/control-plane",
            "detail": settings.orchestrator_model,
        },
        {
            "name": "Token budget",
            "state": "ready" if budget_settings.get("confirmed") else "needs setup",
            "href": "/settings/budget",
            "detail": f"Daily {budget_settings.get('daily_cap_tokens'):,} · Session {budget_settings.get('session_cap_tokens'):,}" if budget_settings.get("daily_cap_tokens") and budget_settings.get("session_cap_tokens") else "No portal budget confirmed",
        },
        {
            "name": "Worker adapter",
            "state": "ready" if active_adapter and active_adapter.get("launchable") else "needs setup",
            "href": worker_href,
            "detail": active_adapter["name"] if active_adapter else "No adapter selected",
        },
        {
            "name": "Projects",
            "state": "ready" if launch_ready_project else "needs setup",
            "href": "/settings/project",
            "detail": (
                launch_ready_project["name"]
                if launch_ready_project
                else "Local Runner is unavailable"
                if connected_projects and not backend
                else "No launch-ready project"
                if connected_projects
                else "Connect a project for local Worker runs"
            ),
        },
    ]
    ready_to_launch = all(step["state"] == "ready" for step in steps)
    next_step = _next_setup_step(steps, launch_ready_project if ready_to_launch else None)

    return {
        "steps": steps,
        "ready_to_launch": ready_to_launch,
        "next_step": next_step,
        "active_adapter": active_adapter,
        "budget_settings": budget_settings,
    }


@router.get("/setup", response_class=HTMLResponse, dependencies=[Depends(require_portal_auth)])
def setup_overview(request: Request):
    return react_shell_or_missing_build()


@router.get("/settings/budget", response_class=HTMLResponse, dependencies=[Depends(require_portal_auth)])
def budget_settings(request: Request):
    return react_shell_or_missing_build()


@router.post("/settings/budget", dependencies=[Depends(require_portal_auth)])
async def save_budget_settings(request: Request):
    try:
        payload, wants_html = await _budget_payload_from_request(request)
    except HTTPException as exc:
        if _wants_react_json(request):
            return _react_budget_outcome(
                ok=False,
                error="daily and session caps must be positive integers",
            )
        raise
    database_path = request.app.state.settings.database_path
    db.set_token_budget_settings(
        database_path,
        daily_cap_tokens=payload.daily_cap_tokens,
        session_cap_tokens=payload.session_cap_tokens,
    )
    budget = _effective_budget_settings(
        database_path,
        request.app.state.guardrails,
        timezone=request.app.state.settings.timezone,
    )
    if wants_html:
        return RedirectResponse("/setup", status_code=status.HTTP_303_SEE_OTHER)
    return _react_budget_outcome(ok=True, budget=budget)


@router.post("/settings/budget/reset", dependencies=[Depends(require_portal_auth)])
async def reset_budget_counter(request: Request):
    database_path = request.app.state.settings.database_path
    db.reset_daily_budget_counter(database_path)
    budget = _effective_budget_settings(
        database_path,
        request.app.state.guardrails,
        timezone=request.app.state.settings.timezone,
    )
    if _wants_react_json(request):
        return _react_budget_outcome(ok=True, budget=budget)
    return RedirectResponse("/settings/budget", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/board", response_class=HTMLResponse, dependencies=[Depends(require_portal_auth)])
def board(request: Request):
    projects = db.list_connected_projects(request.app.state.settings.database_path)
    query = f"?{request.url.query}" if request.url.query else ""
    if projects:
        return RedirectResponse(f"/projects/{projects[0]['id']}{query}", status_code=303)
    return RedirectResponse(f"/projects{query}", status_code=303)


@router.get("/projects/{project_id}/board", response_class=HTMLResponse, dependencies=[Depends(require_portal_auth)])
def project_board(project_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    # Existence stays backend-authoritative: an unknown project is a 404 whether
    # or not the frontend is built.
    try:
        db.get_connected_project(database_path, project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="connected project not found") from exc
    query = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(
        f"/projects/{project_id}{query}", status_code=status.HTTP_301_MOVED_PERMANENTLY
    )


@router.post("/projects/{project_id}/archive", dependencies=[Depends(require_portal_auth)])
def archive_project(project_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    _ensure_project(database_path, project_id)
    block_reason = _project_archive_block_reason(database_path, project_id)
    if block_reason:
        safe_error = str(_safe_worker_evidence(block_reason))[:1000]
        if _wants_react_json(request):
            return JSONResponse(status_code=200, content={"ok": False, "error": safe_error})
        return RedirectResponse(
            f"/settings/project?error={quote(safe_error)}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    db.archive_connected_project(database_path, project_id)
    if _wants_react_json(request):
        return JSONResponse(status_code=200, content={"ok": True, "error": None})
    return RedirectResponse("/projects", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/projects/{project_id}/restore", dependencies=[Depends(require_portal_auth)])
def restore_project(project_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    try:
        _ensure_project(database_path, project_id)
    except HTTPException as exc:
        if _wants_react_json(request):
            return _react_restore_outcome(
                ok=False,
                error=str(exc.detail),
                status_code=exc.status_code,
            )
        raise
    restored = db.restore_connected_project(database_path, project_id)
    if _wants_react_json(request):
        return _react_restore_outcome(ok=True, project=restored)
    return RedirectResponse(f"/projects/{project_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/projects/{project_id}/task-history", response_class=HTMLResponse, dependencies=[Depends(require_portal_auth)])
def project_task_history(project_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    # Existence stays backend-authoritative: an unknown project is a 404 whether
    # or not the frontend is built.
    _ensure_project(database_path, project_id)
    return react_shell_or_missing_build()


@router.post("/projects/{project_id}/tasks/{task_id}/archive", dependencies=[Depends(require_portal_auth)])
def project_archive_task(project_id: str, task_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    try:
        _ensure_project_task(database_path, project_id, task_id)
    except HTTPException as exc:
        if _wants_react_json(request):
            return _react_action_outcome(
                request,
                ok=False,
                error=str(exc.detail),
                status_code=exc.status_code,
            )
        raise
    try:
        db.archive_task(database_path, task_id)
    except ValueError as exc:
        if _wants_react_json(request):
            return _react_action_outcome(request, ok=False, error=str(exc), status_code=409)
        return RedirectResponse(
            f"/projects/{project_id}?error={quote(str(exc))}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    if _wants_react_json(request):
        return _react_action_outcome(request, ok=True, task=db.get_task(database_path, task_id))
    return RedirectResponse(f"/projects/{project_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/projects/{project_id}/tasks/archive-done", dependencies=[Depends(require_portal_auth)])
def project_archive_done_tasks(project_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    project_error = _active_project_action_error(request, database_path, project_id)
    if project_error is not None:
        return project_error
    db.archive_done_tasks_for_project(database_path, project_id)
    if _wants_react_json(request):
        return _react_action_outcome(request, ok=True)
    return RedirectResponse(f"/projects/{project_id}/floor", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/projects/{project_id}/tasks/{task_id}/unarchive", dependencies=[Depends(require_portal_auth)])
def project_unarchive_task(project_id: str, task_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    try:
        _ensure_project_task(database_path, project_id, task_id)
    except HTTPException as exc:
        if _wants_react_json(request):
            return _react_action_outcome(
                request,
                ok=False,
                error=str(exc.detail),
                status_code=exc.status_code,
            )
        raise
    db.unarchive_task(database_path, task_id)
    task = db.get_task(database_path, task_id)
    if _wants_react_json(request):
        return _react_unarchive_outcome(task)
    return RedirectResponse(f"/projects/{project_id}/task-history", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/projects/{project_id}/run-next", dependencies=[Depends(require_portal_auth)])
def project_run_next(project_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    project_error = _active_project_action_error(request, database_path, project_id)
    if project_error is not None:
        return project_error
    task = _next_eligible_task(database_path, project_id)
    if task is None:
        record_automation_event(
            database_path,
            project_id=project_id,
            kind="automation_skipped",
            title="Run next found no eligible task",
            detail={"reason": "no_eligible_tasks", "source": RUN_NEXT_SOURCE},
        )
        if _wants_react_json(request):
            return _react_action_outcome(
                request,
                ok=False,
                error="No eligible Estimated tasks",
                automation=_react_automation_state(database_path, project_id),
                status_code=409,
            )
        return RedirectResponse(f"/projects/{project_id}/floor?error=No%20eligible%20Estimated%20tasks", status_code=303)
    try:
        result = _launch_project_automation_task(request, project_id=project_id, task=task, source=RUN_NEXT_SOURCE)
    except TaskLaunchBlocked as exc:
        record_automation_event(
            database_path,
            project_id=project_id,
            kind="automation_stopped",
            title="Run next blocked before launch",
            detail={"reason": _automation_stop_reason(exc.task, exc.reasons), "reasons": exc.reasons, "source": RUN_NEXT_SOURCE},
            task_id=exc.task["id"],
            level="warning",
        )
        if _wants_react_json(request):
            return _react_action_outcome(
                request,
                ok=False,
                error="; ".join(exc.reasons),
                setup_href=_task_setup_href(exc.task),
                automation=_react_automation_state(database_path, project_id),
                status_code=exc.status_code,
            )
        return RedirectResponse(f"/projects/{project_id}/floor?error={';%20'.join(exc.reasons)}", status_code=303)
    if _wants_react_json(request):
        return _react_action_outcome(
            request,
            ok=True,
            task=result.task,
            automation=_react_automation_state(database_path, project_id),
        )
    return RedirectResponse(f"/projects/{project_id}/floor", status_code=303)


@router.post("/projects/{project_id}/queue/start", dependencies=[Depends(require_portal_auth)])
async def project_queue_start(project_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    project_error = _active_project_action_error(request, database_path, project_id)
    if project_error is not None:
        return project_error
    form = await request.form()
    start_run_automation(
        database_path,
        project_id=project_id,
        source=RUN_QUEUE_SOURCE,
        auto_agent_review="auto_agent_review" in form,
    )
    await _advance_project_queue(request, project_id)
    if _wants_react_json(request):
        automation = _react_automation_state(database_path, project_id)
        stop_reason = automation.get("latest_stop_reason")
        if automation.get("status") == "stopped" and stop_reason not in {
            None,
            "completed_no_eligible_tasks",
        }:
            task = _next_eligible_task(database_path, project_id)
            setup_href = _task_setup_href(task)
            if setup_href is None and stop_reason == "launch_guardrail_blocked":
                setup_href = "/settings/workers"
            return _react_action_outcome(
                request,
                ok=False,
                error=f"Queue stopped: {str(stop_reason).replace('_', ' ')}",
                setup_href=setup_href,
                automation=automation,
                status_code=409,
            )
        return _react_action_outcome(request, ok=True, automation=automation)
    return RedirectResponse(f"/projects/{project_id}/floor", status_code=303)


@router.post("/projects/{project_id}/queue/stop", dependencies=[Depends(require_portal_auth)])
def project_queue_stop(project_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    project_error = _active_project_action_error(request, database_path, project_id)
    if project_error is not None:
        return project_error
    stop_run_automation(database_path, project_id=project_id, reason="operator_stop")
    if _wants_react_json(request):
        return _react_action_outcome(
            request,
            ok=True,
            automation=_react_automation_state(database_path, project_id),
        )
    return RedirectResponse(f"/projects/{project_id}/floor", status_code=303)


@router.get("/projects/{project_id}/board/status", dependencies=[Depends(require_portal_auth)])
async def project_board_status(project_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    try:
        project = db.get_connected_project(database_path, project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="connected project not found") from exc
    if db.project_is_archived(project):
        raise HTTPException(status_code=409, detail="restore archived project before refreshing active board")
    before = _project_board_counts(database_path, project_id)
    refreshed_ids = _refresh_project_board_tasks(database_path, project_id)
    await _advance_project_queue(request, project_id)
    after = _project_board_counts(database_path, project_id)
    queue_state = get_run_automation_state(database_path, project_id)
    return {
        "project_id": project_id,
        "counts": after,
        "queue": queue_state,
        "has_active_runs": after["Running"] > 0,
        "queue_active": queue_state.get("status") == "running",
        "refreshed_task_ids": refreshed_ids,
        "reload_required": bool(refreshed_ids) or before != after,
    }




def _next_setup_step(
    steps: list[dict[str, Any]], launch_ready_project: dict[str, Any] | None
) -> dict[str, Any]:
    if launch_ready_project:
        return {
            "label": "Open task board",
            "href": f"/projects/{launch_ready_project['id']}",
            "detail": "Governed Worker launch is ready.",
        }
    next_step = next((step for step in steps if step["state"] != "ready"), steps[0])
    return {"label": f"Open {next_step['name']}", "href": next_step["href"], "detail": next_step["detail"]}


def _ensure_project(database_path: Path | str, project_id: str) -> dict[str, Any]:
    try:
        return db.get_connected_project(database_path, project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="connected project not found") from exc


def _ensure_active_project(database_path: Path | str, project_id: str) -> dict[str, Any]:
    project = _ensure_project(database_path, project_id)
    if db.project_is_archived(project):
        raise HTTPException(status_code=409, detail="restore archived project before launching active work")
    return project


def _active_project_action_error(
    request: Request, database_path: Path | str, project_id: str
) -> JSONResponse | None:
    try:
        _ensure_active_project(database_path, project_id)
    except HTTPException as exc:
        if _wants_react_json(request):
            return _react_action_outcome(
                request,
                ok=False,
                error=str(exc.detail),
                status_code=exc.status_code,
            )
        raise
    return None


def _project_archive_block_reason(database_path: Path | str, project_id: str) -> str:
    # Archiving is blocked while automation could still mutate project tasks.
    if _project_has_running_work(database_path, project_id):
        return "Project has Running work. Stop or finish active Worker runs before archiving."
    queue_state = get_run_automation_state(database_path, project_id)
    if queue_state.get("status") == "running":
        return "Project run queue is active. Stop the queue before archiving."
    return ""


def _ensure_project_task(database_path: Path | str, project_id: str, task_id: str) -> dict[str, Any]:
    _ensure_project(database_path, project_id)
    try:
        task = db.get_task(database_path, task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="task not found") from exc
    if task_project_id(task) != project_id:
        raise HTTPException(status_code=404, detail="task not found for selected project")
    return task


def _next_eligible_task(database_path: Path | str, project_id: str) -> dict[str, Any] | None:
    tasks = list_eligible_estimated_tasks(database_path, project_id)
    return tasks[0] if tasks else None


def _launch_project_automation_task(
    request: Request,
    *,
    project_id: str,
    task: dict[str, Any],
    source: str,
):
    database_path = request.app.state.settings.database_path
    runner = getattr(request.app.state, "task_launch_runner", None)
    automation_metadata = {
        "automation_source": source,
        "automation_policy": get_run_automation_state(database_path, project_id).get("policy"),
    }
    db.update_task(database_path, task["id"], {"metadata": {**task.get("metadata", {}), **automation_metadata}})
    result = launch_task(
        database_path,
        task["id"],
        adapter_id=None,
        model=None,
        proxy_url=DEFAULT_PROXY_URL,
        project_id=project_id,
        budget_since=db.effective_daily_budget_window_start(database_path, timezone=request.app.state.settings.timezone),
        runner=runner,
    )
    worker_run_id = result.worker_run["id"] if result.worker_run else None
    record_automation_event(
        database_path,
        project_id=project_id,
        kind="automation_launched",
        title="Run automation launched task",
        detail={"source": source, "task_id": result.task["id"], "worker_run_id": worker_run_id},
        task_id=result.task["id"],
        worker_run_id=worker_run_id,
    )
    if source == RUN_QUEUE_SOURCE:
        set_active_automation_run(
            database_path,
            project_id=project_id,
            task_id=result.task["id"],
            worker_run_id=worker_run_id,
        )
    return result


async def _advance_project_queue(request: Request, project_id: str) -> None:
    database_path = request.app.state.settings.database_path
    queue_state = get_run_automation_state(database_path, project_id)
    if queue_state.get("status") != "running":
        return

    active_automation_run = _active_automation_run(queue_state)
    active_run_id = active_automation_run.get("worker_run_id")
    if active_run_id:
        try:
            active_run = db.get_worker_run(database_path, str(active_run_id))
        except KeyError:
            active_run = None
            active_run_id = None
        if active_run and active_run.get("status") in {"queued", "running"}:
            # One active Worker run owns the queue slot until it leaves flight.
            return

    active_task_id = active_automation_run.get("task_id")
    if active_task_id:
        try:
            active_task = db.get_task(database_path, str(active_task_id))
        except KeyError:
            active_task = None
        if active_task and active_task.get("status") == "Running":
            return
        if active_task and active_task.get("status") == "Estimated" and active_task.get("metadata", {}).get("launch_retryable"):
            # Retryable launch failures pause automation so the operator can choose the retry.
            stop_run_automation(
                database_path,
                project_id=project_id,
                reason="retryable_failure",
                task_id=active_task["id"],
                worker_run_id=str(active_run_id) if active_run_id else None,
            )
            return
        if active_task and (active_task.get("metadata") or {}).get("blocked_condition"):
            stop_run_automation(
                database_path,
                project_id=project_id,
                reason="hard_blocker",
                task_id=active_task["id"],
                worker_run_id=str(active_run_id) if active_run_id else None,
            )
            return
        if active_task and active_task.get("status") == "Review":
            active_task = await _maybe_run_auto_agent_review(request, project_id, active_task)

    if get_run_automation_state(database_path, project_id).get("status") != "running":
        return
    # Re-check running work after review/stop side effects before launching the next task.
    if _project_has_running_work(database_path, project_id):
        return

    retryable_task = next(
        (
            candidate
            for candidate in list_eligible_estimated_tasks(database_path, project_id)
            if candidate.get("metadata", {}).get("launch_retryable")
        ),
        None,
    )
    if retryable_task:
        # Retryable failures must pause automation even if the active queue pointer
        # has not been persisted yet; otherwise a fast failing Worker can be relaunched.
        worker_run_id = retryable_task.get("metadata", {}).get("active_worker_run_id")
        if worker_run_id:
            try:
                db.get_worker_run(database_path, str(worker_run_id))
            except KeyError:
                worker_run_id = None
        stop_run_automation(
            database_path,
            project_id=project_id,
            reason="retryable_failure",
            task_id=retryable_task["id"],
            worker_run_id=str(worker_run_id) if worker_run_id else None,
        )
        return

    task = _next_eligible_task(database_path, project_id)
    if task is None:
        stop_run_automation(database_path, project_id=project_id, reason="completed_no_eligible_tasks")
        return
    if get_run_automation_state(database_path, project_id).get("status") != "running":
        return
    if _project_has_running_work(database_path, project_id):
        return
    try:
        _launch_project_automation_task(request, project_id=project_id, task=task, source=RUN_QUEUE_SOURCE)
    except TaskLaunchBlocked as exc:
        stop_run_automation(
            database_path,
            project_id=project_id,
            reason=_automation_stop_reason(exc.task, exc.reasons),
            detail={"reasons": exc.reasons},
            task_id=exc.task["id"],
        )


async def _maybe_run_auto_agent_review(request: Request, project_id: str, task: dict[str, Any]) -> dict[str, Any]:
    database_path = request.app.state.settings.database_path
    queue_state = get_run_automation_state(database_path, project_id)
    worker_run_id = _active_automation_run(queue_state).get("worker_run_id")
    if not queue_state.get("auto_agent_review"):
        return task
    metadata = task.get("metadata") or {}
    if metadata.get("agent_review"):
        return task
    try:
        _ensure_review_task(task, database_path)
    except ValueError as exc:
        record_automation_event(
            database_path,
            project_id=project_id,
            kind="auto_agent_review_skipped",
            title="Auto Agent Review skipped",
            task_id=task["id"],
            worker_run_id=worker_run_id,
            detail={"review_status": "skipped", "reason": str(exc)},
            level="warning",
        )
        return task
    claimed = db.claim_task_agent_review(
        database_path,
        task["id"],
        {"status": "running", "source": "auto_agent_review", "started_at": datetime.now(UTC).isoformat()},
    )
    if claimed is None:
        return db.get_task(database_path, task["id"])
    reviewed = await _run_agent_review(request, claimed, metadata.get("review_prompt"))
    record_automation_event(
        database_path,
        project_id=project_id,
        kind="auto_agent_review",
        title="Auto Agent Review completed",
        task_id=task["id"],
        worker_run_id=worker_run_id,
        detail={"review_status": reviewed.get("metadata", {}).get("agent_review", {}).get("status")},
    )
    return reviewed


def _automation_stop_reason(task: dict[str, Any], reasons: list[str]) -> str:
    metadata = task.get("metadata") or {}
    if metadata.get("native_usage_override_ack_required"):
        return "native_usage_ack_required"
    if metadata.get("budget_override_available"):
        return "budget_approval_required"
    if metadata.get("launch_retryable"):
        return "retryable_failure"
    if reasons:
        return "launch_guardrail_blocked"
    return "automation_blocked"


def _active_automation_run(queue_state: dict[str, Any]) -> dict[str, Any]:
    runs = queue_state.get("active_runs")
    return runs[0] if isinstance(runs, list) and runs and isinstance(runs[0], dict) else {}


@router.get("/settings/workers", response_class=HTMLResponse, dependencies=[Depends(require_portal_auth)])
def worker_settings(request: Request):
    return react_shell_or_missing_build()


def _worker_settings_url(adapter_id: str, *, error: str | None = None) -> str:
    url = f"/settings/workers?adapter_id={quote(adapter_id)}"
    if error:
        url = f"{url}&error={quote(error)}"
    return url


@router.post("/settings/workers/{adapter_id}/configure", dependencies=[Depends(require_portal_auth)])
async def configure_worker_adapter(adapter_id: str, request: Request):
    """Accept adapter settings form fields, update adapter, redirect to workers page."""
    database_path = request.app.state.settings.database_path
    payload, _ = await _config_payload_from_request(request)
    try:
        db.update_worker_adapter(
            database_path,
            adapter_id,
            is_default=payload.is_default,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="worker adapter not found") from exc
    if _wants_react_json(request):
        return _react_worker_settings_outcome(ok=True)
    return RedirectResponse(_worker_settings_url(adapter_id), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/settings/workers/{adapter_id}/allowed-models", dependencies=[Depends(require_portal_auth)])
async def configure_worker_allowed_models(adapter_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    try:
        adapter = db.get_worker_adapter(database_path, adapter_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="worker adapter not found") from exc

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        raw = await request.json()
        allowed_models = [str(model) for model in (raw or {}).get("allowed_models", []) if model]
    else:
        form = await request.form()
        allowed_models = [str(model) for model in form.getlist("allowed_models")]
    discovered_models = discovered_worker_model_ids(adapter)
    invalid = [model for model in allowed_models if model not in discovered_models]
    if invalid:
        safe_error = "Allowed models must be discovered first."
        if _wants_react_json(request):
            return _react_worker_settings_outcome(ok=False, error=safe_error)
        return RedirectResponse(_worker_settings_url(adapter_id, error=safe_error), status_code=status.HTTP_303_SEE_OTHER)

    config = {**(adapter.get("config") or {}), "allowed_models_configured": True}
    db.update_worker_adapter(database_path, adapter_id, config=config, supported_models=allowed_models)
    if _wants_react_json(request):
        return _react_worker_settings_outcome(ok=True)
    return RedirectResponse(_worker_settings_url(adapter_id), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/settings/workers/{adapter_id}/refresh-diagnostics", dependencies=[Depends(require_portal_auth)])
def refresh_worker_diagnostics(adapter_id: str, request: Request):
    """Force re-detection of adapter binary on PATH."""
    database_path = request.app.state.settings.database_path
    try:
        adapter = db.get_worker_adapter(database_path, adapter_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="worker adapter not found") from exc
    config = dict(adapter.get("config") or {})
    try:
        diag = detect_worker_adapter(adapter)
    except Exception as exc:
        safe_error = "Could not refresh adapter diagnostics."
        if _wants_react_json(request):
            return _react_worker_settings_outcome(ok=False, error=safe_error)
        return RedirectResponse(_worker_settings_url(adapter_id, error=safe_error), status_code=status.HTTP_303_SEE_OTHER)
    config["_diagnostics"] = diag
    config["_diagnostics_at"] = datetime.now(UTC).timestamp()
    db.update_worker_adapter(database_path, adapter_id, config=config)
    if _wants_react_json(request):
        return _react_worker_settings_outcome(ok=True)
    return RedirectResponse(_worker_settings_url(adapter_id), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/settings/control-plane", response_class=HTMLResponse, dependencies=[Depends(require_portal_auth)])
def control_plane_settings(request: Request):
    return react_shell_or_missing_build()


@router.post("/settings/control-plane", dependencies=[Depends(require_portal_auth)])
async def save_control_plane_settings(request: Request):
    payload, wants_html = await _control_plane_payload_from_request(request)
    current: Settings = request.app.state.settings
    updates: dict[str, Any] = {
        "control_plane_provider": payload.control_plane_provider,
        "control_plane_model": payload.orchestrator_model,
        "control_plane_base_url": payload.control_plane_base_url.strip(),
        "control_plane_api_key_env": payload.control_plane_api_key_env,
    }
    if payload.apply_to_estimator_breakdown:
        updates["estimator_model"] = payload.orchestrator_model
        updates["task_breakdown_model"] = payload.orchestrator_model
    try:
        config = update_operator_config(**updates)
        if payload.control_plane_api_key:
            write_control_plane_secret(payload.control_plane_api_key_env, payload.control_plane_api_key)
        else:
            ensure_secret_placeholder(payload.control_plane_api_key_env)
            load_operator_secrets_env(config)
        _sync_control_plane_env(payload)
    except OSError as exc:
        safe_message = "Could not save control-plane config."
        if _wants_react_json(request):
            return _react_control_plane_outcome(ok=False, error=safe_message, status_code=500)
        # Non-JSON callers previously got this message rendered into the
        # server-rendered settings page. That page is retired, and the control-plane
        # handoff does not read an ``?error=`` query parameter, so a redirect would
        # drop the message silently. The sanitized message stays in the response body.
        return JSONResponse(status_code=500, content={"detail": safe_message})

    new_settings = Settings(
        database_path=current.database_path,
        guardrails_path=current.guardrails_path,
        timezone=current.timezone,
        portal_token_env=current.portal_token_env,
        portal_cookie_secure=current.portal_cookie_secure,
        local_runner_enabled=current.local_runner_enabled,
        provider_api_key_env=current.provider_api_key_env,
        operator_config=config,
    )
    request.app.state.settings = new_settings
    request.app.state.llm_client = LLMClient(new_settings)
    status_record = db.upsert_execution_backend_status(
        new_settings.database_path,
        "control_plane_model",
        name="Orchestrator Model",
        online=False,
        details={
            # A saved config is not trusted until the explicit connection test passes.
            "status": "needs_test",
            "reason": "configuration changed; test required",
            "provider": new_settings.control_plane_provider,
            "model": new_settings.orchestrator_model,
            "api_key_env": new_settings.control_plane_api_key_env,
        },
    )
    status_with_state = {**status_record, "state": _control_plane_connection_state(status_record)}
    settings_json = {
        "control_plane_provider": new_settings.control_plane_provider,
        "orchestrator_model": new_settings.orchestrator_model,
        "control_plane_base_url": new_settings.control_plane_base_url,
        "control_plane_api_key_env": new_settings.control_plane_api_key_env,
        "estimator_model": new_settings.estimator_model,
        "task_breakdown_model": new_settings.task_breakdown_model,
    }
    if wants_html:
        return RedirectResponse("/settings/control-plane", status_code=status.HTTP_303_SEE_OTHER)
    if _wants_react_json(request):
        return _react_control_plane_outcome(
            ok=True,
            settings=settings_json,
            status=status_with_state,
            shadowed_settings=_control_plane_shadowed_settings(new_settings),
        )
    return {
        "settings": settings_json,
        "status": status_with_state,
        "shadowed_settings": _control_plane_shadowed_settings(new_settings),
    }


@router.post("/settings/control-plane/test", dependencies=[Depends(require_portal_auth)])
async def test_control_plane_connection(request: Request):
    settings = request.app.state.settings
    accept = request.headers.get("accept", "")
    wants_html = "text/html" in accept and "application/json" not in accept
    payload = {
        "model": settings.orchestrator_model,
        "messages": [{"role": "user", "content": "Return exactly FOREMAN_AI_HQ_CONTROL_PLANE_OK."}],
    }
    try:
        response = await request.app.state.llm_client.acompletion(payload)
        status_record = db.upsert_execution_backend_status(
            settings.database_path,
            "control_plane_model",
            name="Orchestrator Model",
            online=True,
            details={
                "provider": settings.control_plane_provider,
                "model": settings.orchestrator_model,
                "api_key_env": settings.control_plane_api_key_env,
                "usage": extract_usage(response),
                "cost": resolve_cost(settings.orchestrator_model, response),
                "response": _safe_worker_evidence(response_to_dict(response)),
            },
        )
        status_with_state = {**status_record, "state": _control_plane_connection_state(status_record)}
        if wants_html:
            return RedirectResponse("/settings/control-plane", status_code=status.HTTP_303_SEE_OTHER)
        return JSONResponse(status_code=200, content={"passed": True, "status": status_with_state, "error": None})
    except Exception as exc:
        status_record = db.upsert_execution_backend_status(
            settings.database_path,
            "control_plane_model",
            name="Orchestrator Model",
            online=False,
            details={
                "provider": settings.control_plane_provider,
                "model": settings.orchestrator_model,
                "api_key_env": settings.control_plane_api_key_env,
                "error_type": type(exc).__name__,
                "error": _safe_worker_evidence(str(exc)),
            },
        )
        status_with_state = {**status_record, "state": _control_plane_connection_state(status_record)}
        if wants_html:
            return RedirectResponse("/settings/control-plane", status_code=status.HTTP_303_SEE_OTHER)
        error_summary = (status_with_state.get("details") or {}).get("error") or "control-plane connection test failed"
        return JSONResponse(status_code=503, content={"passed": False, "status": status_with_state, "error": error_summary})


@router.get("/settings/project", response_class=HTMLResponse, dependencies=[Depends(require_portal_auth)])
def project_settings(request: Request):
    return react_shell_or_missing_build()


@router.post("/settings/project/connect", dependencies=[Depends(require_portal_auth)])
async def connect_project_route(request: Request):
    payload, wants_html = await _project_connect_payload_from_request(request)
    backend = _local_backend(request)
    if backend is None:
        message = "Local Runner backend is disabled. Run foremanctl init, then foremanctl serve."
        if wants_html:
            return _project_settings_with_error(request, message)
        return JSONResponse(status_code=409, content={"detail": message})

    result = backend.connect_project(payload.root_path)
    if result.error:
        if wants_html:
            return _project_settings_with_error(request, result.error)
        return JSONResponse(status_code=422, content={"detail": result.error})

    if wants_html and request.query_params.get("redirect") == "workspace" and result.project:
        return RedirectResponse(f"/projects/{result.project['id']}", status_code=status.HTTP_303_SEE_OTHER)
    if wants_html:
        return RedirectResponse("/settings/project", status_code=status.HTTP_303_SEE_OTHER)
    return JSONResponse(status_code=200, content={"project": result.project})


@router.post("/settings/project/{project_id}/read-only-proof", dependencies=[Depends(require_portal_auth)])
async def launch_read_only_proof_route(project_id: str, request: Request):
    backend = _local_backend(request)
    if backend is None:
        return JSONResponse(status_code=409, content={"detail": "Local Runner backend is disabled."})
    database_path = request.app.state.settings.database_path
    project = next((item for item in db.list_connected_projects(database_path) if item["id"] == project_id), None)
    if project is None:
        raise HTTPException(status_code=404, detail="connected project not found")
    capability = backend.project_capability(project)
    if capability.get("state") != "launch_ready":
        return JSONResponse(status_code=409, content={"detail": "Project is not Launch-ready via Local Runner.", "capability": capability})

    task = backend.create_read_only_proof_task({**project, "capability": capability})
    try:
        result = launch_task(
            database_path,
            task["id"],
            adapter_id="opencode",
            model=task.get("recommended_model"),
            proxy_url=DEFAULT_PROXY_URL,
            budget_since=db.effective_daily_budget_window_start(database_path, timezone=request.app.state.settings.timezone),
            runner=getattr(request.app.state, "local_runner_proof_runner", None)
            or getattr(request.app.state, "task_launch_runner", None),
        )
    except TaskLaunchBlocked as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"task": exc.task, "launch_guardrails": {"passed": False, "reasons": exc.reasons}},
        )
    return JSONResponse(status_code=200, content=result.as_response())


@router.post("/settings/workers/{adapter_id}/verify", dependencies=[Depends(require_portal_auth)])
async def verify_worker_adapter_route(adapter_id: str, request: Request):
    payload, wants_html = await _worker_verify_payload_from_request(request)
    database_path = request.app.state.settings.database_path
    try:
        _validate_worker_tracking_mode(database_path, adapter_id, payload.tracking_mode)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="worker adapter not found") from exc
    except ValueError as exc:
        if wants_html:
            return RedirectResponse(_worker_settings_url(adapter_id, error=str(exc)), status_code=status.HTTP_303_SEE_OTHER)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        result = verify_worker_adapter(
            database_path,
            adapter_id,
            model=payload.model,
            proxy_url=payload.proxy_url or DEFAULT_PROXY_URL,
            tracking_mode=payload.tracking_mode,
            runner=getattr(request.app.state, "worker_adapter_verification_runner", None),
            token_recorder=getattr(request.app.state, "worker_adapter_verification_token_recorder", None),
        )
    except KeyError as exc:
        if "worker adapter not found" in str(exc):
            raise HTTPException(status_code=404, detail="worker adapter not found") from exc
        raise HTTPException(
            status_code=422,
            detail=f"worker adapter configuration invalid: missing template variable {exc}",
        ) from exc
    if wants_html:
        return RedirectResponse(_worker_settings_url(adapter_id), status_code=status.HTTP_303_SEE_OTHER)
    return JSONResponse(
        status_code=200 if result.passed else 409,
        content={
            "passed": result.passed,
            "adapter_id": result.adapter_id,
            "session_id": result.session_id,
            "reasons": result.reasons,
            "evidence": _safe_worker_evidence(result.evidence),
        },
    )


@router.post("/settings/workers/{adapter_id}/discover-models", dependencies=[Depends(require_portal_auth)])
async def discover_worker_models_route(adapter_id: str, request: Request):
    try:
        result = discover_worker_models(
            request.app.state.settings.database_path,
            adapter_id,
            runner=getattr(request.app.state, "worker_model_discovery_runner", None),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="worker adapter not found") from exc
    accept = request.headers.get("accept", "")
    if "text/html" in accept and "application/json" not in accept:
        return RedirectResponse(_worker_settings_url(adapter_id), status_code=status.HTTP_303_SEE_OTHER)
    return JSONResponse(
        status_code=200 if result.passed else 409,
        content={
            "passed": result.passed,
            "adapter_id": result.adapter_id,
            "models": result.models,
            "reasons": result.reasons,
            "evidence": _safe_worker_evidence(result.evidence),
        },
    )


@router.get("/sessions", response_class=HTMLResponse, dependencies=[Depends(require_portal_auth)])
def sessions_index(request: Request):
    return react_shell_or_missing_build()


@router.get("/sessions/{session_id}", response_class=HTMLResponse, dependencies=[Depends(require_portal_auth)])
def session_report_view(session_id: str, request: Request):
    # Existence stays backend-authoritative: an unknown session is a 404 whether
    # or not the frontend is built. A single-row lookup is enough here; the full
    # artifact is built by the JSON handoff the shell then calls.
    try:
        db.get_session(request.app.state.settings.database_path, session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    return react_shell_or_missing_build()


def _related_agent_review(database_path: Path | str, session_id: str) -> dict[str, Any] | None:
    for task in reversed(db.list_tasks(database_path)):
        if task.get("session_id") != session_id:
            continue
        review = (task.get("metadata") or {}).get("agent_review")
        if isinstance(review, dict):
            return {"task_id": task.get("id"), **review, "review_total_tokens": _agent_review_total_tokens(database_path, review)}
    return None


def _agent_review_total_tokens(database_path: Path | str, review: dict[str, Any]) -> int | None:
    raw_token_totals = review.get("token_totals")
    if not isinstance(raw_token_totals, dict):
        return None
    total_tokens = raw_token_totals.get("total_tokens")
    if not isinstance(total_tokens, int):
        return None
    review_session_id = review.get("review_session_id")
    if not review_session_id:
        return total_tokens
    try:
        artifact = db.build_session_artifact(database_path, str(review_session_id))
    except KeyError:
        return None
    if not artifact.get("token_log"):
        return None
    return total_tokens


async def _control_plane_payload_from_request(request: Request) -> tuple[ControlPlaneSettingsRequest, bool]:
    content_type = request.headers.get("content-type", "")
    accept = request.headers.get("accept", "")
    wants_html = "text/html" in accept and "application/json" not in accept
    if "application/json" in content_type:
        raw = await request.json()
        try:
            return ControlPlaneSettingsRequest.model_validate(raw or {}), False
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=_validation_error_details(exc)) from exc
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        raw: dict[str, Any] = {key: value for key, value in form.items() if value not in (None, "")}
        if raw.get("control_plane_model") == "__custom__":
            raw["control_plane_model"] = str(form.get("custom_control_plane_model") or "").strip()
        raw.pop("custom_control_plane_model", None)
        raw["apply_to_estimator_breakdown"] = "apply_to_estimator_breakdown" in raw
        try:
            return ControlPlaneSettingsRequest.model_validate(raw), True
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=_validation_error_details(exc)) from exc
    raise HTTPException(status_code=422, detail="control-plane settings are required")


def _validation_error_details(exc: ValidationError) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = [dict(detail) for detail in exc.errors()]
    for detail in details:
        detail.pop("input", None)
        ctx = detail.get("ctx")
        if isinstance(ctx, dict) and "error" in ctx:
            ctx["error"] = str(ctx["error"])
    return details


def _control_plane_setup_state(settings: Settings, control_status: dict[str, Any] | None) -> str:
    if control_status and (control_status.get("details") or {}).get("status") == "needs_test":
        return "needs test"
    if bool(os.getenv(settings.control_plane_api_key_env)) or (control_status and control_status.get("online")):
        return "ready"
    return "needs setup"


def _control_plane_connection_state(control_status: dict[str, Any] | None) -> str:
    if control_status is None:
        return "offline"
    details = control_status.get("details") or {}
    if details.get("status") == "needs_test":
        return "needs_test"
    if control_status.get("online"):
        return "online"
    return "offline"


def _control_plane_connection_details(control_status: dict[str, Any] | None) -> dict[str, Any] | None:
    if control_status is None:
        return {"state": "offline", "checked_at": None, "details": None}
    details = _safe_worker_evidence(control_status.get("details") or {})
    return {
        "state": _control_plane_connection_state(control_status),
        "checked_at": control_status.get("checked_at"),
        "details": details,
    }


def _react_control_plane_outcome(
    *,
    ok: bool,
    settings: dict[str, Any] | None = None,
    status: dict[str, Any] | None = None,
    shadowed_settings: dict[str, str] | None = None,
    error: str | None = None,
    status_code: int = 200,
) -> JSONResponse:
    """Bounded, key-free JSON outcome for control-plane save/test actions."""

    return JSONResponse(
        status_code=status_code,
        content={
            "ok": ok,
            "error": str(_safe_worker_evidence(error)) if error else None,
            "settings": settings,
            "status": status,
            "shadowed_settings": shadowed_settings,
        },
    )


def _control_plane_shadowed_settings(settings: Settings) -> dict[str, str]:
    shadowed: dict[str, str] = {}
    checks = {
        "control_plane_provider": ["FOREMAN_AI_HQ_CONTROL_PROVIDER", "TOKEN_TRACKER_CONTROL_PLANE_PROVIDER"],
        "orchestrator_model": [
            "FOREMAN_AI_HQ_ORCHESTRATOR_MODEL",
            "TOKEN_TRACKER_ORCHESTRATOR_MODEL",
            "FOREMAN_AI_HQ_CONTROL_MODEL",
            "TOKEN_TRACKER_CONTROL_PLANE_MODEL",
        ],
        "control_plane_base_url": ["FOREMAN_AI_HQ_CONTROL_BASE_URL", "TOKEN_TRACKER_CONTROL_PLANE_BASE_URL"],
        "control_plane_api_key_env": ["FOREMAN_AI_HQ_CONTROL_API_KEY_ENV", "TOKEN_TRACKER_CONTROL_PLANE_API_KEY_ENV"],
        "estimator_model": ["FOREMAN_AI_HQ_ESTIMATOR_MODEL", "TOKEN_TRACKER_ESTIMATOR_MODEL"],
        "task_breakdown_model": ["FOREMAN_AI_HQ_TASK_BREAKDOWN_MODEL", "TOKEN_TRACKER_TASK_BREAKDOWN_MODEL"],
    }
    for field, env_names in checks.items():
        for env_name in env_names:
            value = os.getenv(env_name)
            if value is not None and value == str(getattr(settings, field)):
                shadowed[field] = env_name
                break
    return shadowed


def _sync_control_plane_env(payload: ControlPlaneSettingsRequest) -> None:
    values = {
        "FOREMAN_AI_HQ_CONTROL_PROVIDER": payload.control_plane_provider,
        "TOKEN_TRACKER_CONTROL_PLANE_PROVIDER": payload.control_plane_provider,
        "FOREMAN_AI_HQ_ORCHESTRATOR_MODEL": payload.orchestrator_model,
        "TOKEN_TRACKER_ORCHESTRATOR_MODEL": payload.orchestrator_model,
        "FOREMAN_AI_HQ_CONTROL_MODEL": payload.orchestrator_model,
        "TOKEN_TRACKER_CONTROL_PLANE_MODEL": payload.orchestrator_model,
        "FOREMAN_AI_HQ_CONTROL_BASE_URL": payload.control_plane_base_url,
        "TOKEN_TRACKER_CONTROL_PLANE_BASE_URL": payload.control_plane_base_url,
        "FOREMAN_AI_HQ_CONTROL_API_KEY_ENV": payload.control_plane_api_key_env,
        "TOKEN_TRACKER_CONTROL_PLANE_API_KEY_ENV": payload.control_plane_api_key_env,
    }
    if payload.apply_to_estimator_breakdown:
        values["FOREMAN_AI_HQ_ESTIMATOR_MODEL"] = payload.orchestrator_model
        values["TOKEN_TRACKER_ESTIMATOR_MODEL"] = payload.orchestrator_model
        values["FOREMAN_AI_HQ_TASK_BREAKDOWN_MODEL"] = payload.orchestrator_model
        values["TOKEN_TRACKER_TASK_BREAKDOWN_MODEL"] = payload.orchestrator_model
    for name, value in values.items():
        if name in os.environ:
            os.environ[name] = value


def _local_backend(request: Request) -> LocalExecutionBackend | None:
    if not request.app.state.settings.local_runner_enabled:
        return None
    backend = getattr(request.app.state, "execution_backend", None)
    if backend is None:
        # Cache the backend on app state so route calls share project capability probes.
        backend = LocalExecutionBackend(request.app.state.settings.database_path)
        request.app.state.execution_backend = backend
    return backend


def _project_view_models(request: Request) -> list[dict[str, Any]]:
    return [_project_view_model(request, project) for project in db.list_connected_projects(request.app.state.settings.database_path)]


def _archived_project_view_models(request: Request) -> list[dict[str, Any]]:
    return [
        _project_view_model(request, project)
        for project in db.list_archived_connected_projects(request.app.state.settings.database_path)
    ]


def _project_view_model(request: Request, project: dict[str, Any]) -> dict[str, Any]:
    backend = _local_backend(request)
    capability = backend.project_capability(project) if backend else project.get("capability", {})
    return {**project, "capability": capability}


def _project_settings_with_error(request: Request, error: str):
    """Carry a connect/backend failure back to the canonical Project Settings URL.

    This used to re-render the server-rendered page with the error inline.
    Retirement removed that page, so the reason travels as a query parameter
    instead — the same path the archive block already uses, and one the Project
    Settings JSON handoff sanitizes before React surfaces it.
    """

    return RedirectResponse(
        f"/settings/project?error={quote(str(_safe_worker_evidence(error))[:1000])}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


async def _budget_payload_from_request(request: Request) -> tuple[TokenBudgetSettingsRequest, bool]:
    content_type = request.headers.get("content-type", "")
    wants_html = not _wants_react_json(request)
    if "application/json" in content_type:
        raw = await request.json()
        try:
            return TokenBudgetSettingsRequest.model_validate(raw or {}), wants_html
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        raw = {key: int(str(value)) for key, value in form.items() if value not in (None, "")}
        try:
            return TokenBudgetSettingsRequest.model_validate(raw), wants_html
        except (ValidationError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="daily and session caps must be positive integers") from exc
    raise HTTPException(status_code=422, detail="budget settings are required")


async def _config_payload_from_request(request: Request) -> tuple[WorkerConfigureRequest, bool]:
    """Extract worker configure payload from JSON or form-encoded request."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        raw = await request.json()
        try:
            return WorkerConfigureRequest.model_validate(raw or {}), False
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        raw: dict[str, Any] = {key: value for key, value in form.items() if value not in (None, "")}
        raw["is_default"] = "is_default" in raw
        try:
            return WorkerConfigureRequest.model_validate(raw), True
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
    return WorkerConfigureRequest(), True


async def _project_connect_payload_from_request(request: Request) -> tuple[ProjectConnectRequest, bool]:
    content_type = request.headers.get("content-type", "")
    accept = request.headers.get("accept", "")
    wants_html = "text/html" in accept and "application/json" not in accept
    if "application/json" in content_type:
        raw = await request.json()
        try:
            return ProjectConnectRequest.model_validate(raw or {}), False
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        raw = {key: value for key, value in form.items() if value not in (None, "")}
        try:
            return ProjectConnectRequest.model_validate(raw), True
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
    raise HTTPException(status_code=422, detail="root_path is required")


async def _worker_verify_payload_from_request(request: Request) -> tuple[WorkerVerifyRequest, bool]:
    content_type = request.headers.get("content-type", "")
    accept = request.headers.get("accept", "")
    wants_html = "text/html" in accept and "application/json" not in accept
    if "application/json" in content_type:
        raw = await request.json()
        try:
            return WorkerVerifyRequest.model_validate(raw or {}), False
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        raw = {key: value for key, value in form.items() if value not in (None, "")}
        raw.setdefault("proxy_url", DEFAULT_PROXY_URL)
        try:
            return WorkerVerifyRequest.model_validate(raw), True
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
    raise HTTPException(status_code=422, detail="model is required")


def _effective_budget_settings(database_path: Path | str, config: Any, *, timezone: str = "local") -> dict[str, Any]:
    stored = db.get_token_budget_settings(database_path)
    daily_cap = stored.get("daily_cap_tokens")
    session_cap = stored.get("session_cap_tokens")
    if daily_cap is None and config.daily_cap.enabled:
        daily_cap = config.daily_cap.tokens
    if session_cap is None and config.session_cap.enabled:
        session_cap = config.session_cap.tokens
    budget_since = db.effective_daily_budget_window_start(database_path, timezone=timezone)
    token_breakdown = db.token_usage_breakdown(database_path, since=budget_since)
    used_tokens = int(token_breakdown["total_tokens"])
    remaining_tokens = max(int(daily_cap) - used_tokens, 0) if daily_cap is not None else None
    return {
        "daily_cap_tokens": daily_cap,
        "session_cap_tokens": session_cap,
        "confirmed": bool(stored.get("confirmed")),
        "daily_usage_reset_at": stored.get("daily_usage_reset_at"),
        "budget_since": budget_since,
        "current_window_used_tokens": used_tokens,
        "current_window_remaining_tokens": remaining_tokens,
        "current_window_breakdown": token_breakdown,
    }


def _current_day_start_iso(timezone: str) -> str:
    return db.current_day_start_iso(timezone)
