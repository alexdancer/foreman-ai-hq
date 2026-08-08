"""FastAPI serving for the React Portal shell.

This module keeps FastAPI as the only backend authority. It:

- serves the built Vite React shell and its static assets (``/static/react/*``)
  from a deterministic build directory,
- returns the missing-build recovery response instead of a blank shell when the
  frontend has not been built,
- redirects the retired ``/app`` aliases to their canonical URLs,
- exposes the authenticated JSON handoffs the React surfaces read.

React owns every operator-facing canonical route. The only server-rendered
pages left are the recovery surfaces: the login page and the missing-build
response below. Every workflow rule (auth, guardrails, launch, budget, review
disposition) is unchanged and remains the source of truth.
"""

from __future__ import annotations

import json
import math
import os
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from foreman_ai_hq import db
from foreman_ai_hq.auth import require_portal_auth
from foreman_ai_hq.board_workspace import (
    BOARD_COLUMNS,
    board_page_context,
    project_bound_tasks,
    project_board_counts,
    project_task_history_context,
    project_workspace_summary,
)
from foreman_ai_hq.evidence_reporting import safe_evidence
from foreman_ai_hq.estimation_coefficients import CoefficientLoadError, resolve_coefficients
from foreman_ai_hq.needs_you import low_confidence_item
from foreman_ai_hq.pi_adapter import (
    DISCOVERY_NEEDS_AUTHENTICATION,
    orchestrator_verification_is_stale,
    persisted_orchestrator_discovery,
    persisted_orchestrator_verification,
)
from foreman_ai_hq.task_kind import read_task_kind
from foreman_ai_hq.task_launch import DEFAULT_PROXY_URL
from foreman_ai_hq.template_context import portal_template_context
from foreman_ai_hq.worker_setup_view import (
    active_adapter_for_request as _active_adapter_for_request,
    worker_adapter_view_models as _worker_adapter_view_models,
    worker_setup_next_action as _worker_setup_next_action,
)

router = APIRouter()

# The Portal Recovery Surface for frontend boot failure. Self-contained by
# design, like login.html: a recovery surface cannot share machinery with the
# thing that might be broken. It deliberately offers no link — every Portal
# route returns this same document while the build is missing, so any link here
# would point back at the error it is apologizing for.
_MISSING_BUILD_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Frontend build missing</title>
  </head>
  <body style="font-family: sans-serif; max-width: 40rem; margin: 4rem auto; color: #222;">
    <h1>React Portal shell is not built</h1>
    <p>
      The Portal assets have not been built yet. Build the frontend with
      <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code>, then reload
      this page.
    </p>
  </body>
</html>
"""


def react_build_dir() -> Path:
    """Deterministic directory the built React shell is served from."""

    return Path(__file__).resolve().parents[1] / "static" / "react"


def _react_index() -> Path | None:
    index = react_build_dir() / "index.html"
    if not index.is_file():
        return None
    return index if _referenced_assets_available(index) else None


def react_shell_available() -> bool:
    """Return whether the complete built React shell can serve the default landing."""

    return _react_index() is not None


class _ReactAssetReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.asset_paths: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del tag
        for name, value in attrs:
            if name in {"src", "href"} and value and value.startswith("/static/react/"):
                self.asset_paths.append(value)


def _referenced_assets_available(index: Path) -> bool:
    build_dir = react_build_dir().resolve()
    try:
        html = index.read_text(encoding="utf-8")
    except OSError:
        return False
    parser = _ReactAssetReferenceParser()
    parser.feed(html)
    asset_paths = parser.asset_paths
    if not asset_paths:
        return False
    for asset_path in asset_paths:
        relative = asset_path.removeprefix("/static/react/")
        relative = relative.split("?", 1)[0].split("#", 1)[0]
        target = (build_dir / relative).resolve()
        if (
            (target != build_dir and build_dir not in target.parents)
            or not target.is_file()
        ):
            return False
    return True


@router.get("/static/react/{asset_path:path}")
def react_asset(asset_path: str):
    """Serve built React assets. No auth: these are inert JS/CSS, not data."""

    build_dir = react_build_dir().resolve()
    target = (build_dir / asset_path).resolve()
    # Guard against path traversal escaping the build directory.
    if target != build_dir and build_dir not in target.parents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return FileResponse(target)


def missing_build_response() -> HTMLResponse:
    """The recovery response for a missing or partial React build."""

    return HTMLResponse(
        _MISSING_BUILD_HTML,
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def react_shell_or_missing_build():
    """Serve the built React shell, or the recovery response when it is absent.

    Every React-owned canonical route ends here, so a missing build produces one
    answer at one status code rather than a per-route decision. Callers that must
    stay backend-authoritative about existence (unknown project, session, or
    breakdown ids) do their lookup first: an unknown id is a ``404``, never a
    recovery response about a resource that never existed.
    """

    index = _react_index()
    if index is None:
        return missing_build_response()
    return FileResponse(index)


@router.get("/app", dependencies=[Depends(require_portal_auth)])
def react_app_alias(request: Request) -> RedirectResponse:
    """Permanent redirect for the retired ``/app`` alias.

    Nothing links here — slice 11b moved every target onto the canonical URLs.
    The redirect exists for operator bookmarks and external links only.
    """

    query = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(f"/dashboard{query}", status_code=status.HTTP_301_MOVED_PERMANENTLY)


@router.get("/app/projects/{project_id}", dependencies=[Depends(require_portal_auth)])
def react_app_project_alias(project_id: str, request: Request) -> RedirectResponse:
    query = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(
        f"/projects/{project_id}{query}", status_code=status.HTTP_301_MOVED_PERMANENTLY
    )


@router.get("/app/projects/{project_id}/board", dependencies=[Depends(require_portal_auth)])
def react_app_board_alias(project_id: str, request: Request) -> RedirectResponse:
    query = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(
        f"/projects/{project_id}{query}", status_code=status.HTTP_301_MOVED_PERMANENTLY
    )


@router.get("/app/projects/{project_id}/floor", dependencies=[Depends(require_portal_auth)])
def react_app_floor_alias(project_id: str, request: Request) -> RedirectResponse:
    query = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(
        f"/projects/{project_id}/floor{query}", status_code=status.HTTP_301_MOVED_PERMANENTLY
    )


@router.get("/api/portal/nav", dependencies=[Depends(require_portal_auth)])
def react_portal_nav(request: Request):
    """Authenticated sidebar navigation context for the React shell.

    Reuses the ``portal_template_context`` helper, which also guards the login
    page against exposing project data before authentication. Returns only the
    fields the sidebar needs.
    """

    context = portal_template_context(request)
    database_path = request.app.state.settings.database_path
    return {
        "portal_auth_required": bool(context.get("portal_auth_required")),
        "sidebar_projects": [
            {
                "id": str(project["id"]),
                "name": project.get("name", ""),
                "task_count": project.get("task_count", 0),
                "needs_you_count": _needs_you_state(
                    database_path, str(project["id"])
                )["count"],
            }
            for project in context.get("sidebar_projects", [])
        ],
    }


def _dashboard_cost(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) and value >= 0 else None


_DASHBOARD_COEFFICIENT_LABELS = {
    "a": "Input per file read",
    "b": "Input per file modified",
    "g": "Context growth per turn",
    "p": "Output per turn",
    "k": "Test-run overhead",
}


def _dashboard_coefficient_provenance() -> dict[str, Any]:
    try:
        coefficients = resolve_coefficients(None, None)
    except CoefficientLoadError:
        # Dashboard evidence must degrade safely without exposing package paths or parser detail.
        return {"available": False, "scope": "default", "factors": []}
    return {
        "available": True,
        "scope": "default",
        "factors": [
            {
                "key": key,
                "label": label,
                "value": coefficients.values[key],
                "provenance": coefficients.provenance[key],
            }
            for key, label in _DASHBOARD_COEFFICIENT_LABELS.items()
        ],
    }


def _dashboard_pricing_coverage(
    token_breakdown: dict[str, Any], *category_names: str
) -> dict[str, Any]:
    category_coverage = token_breakdown["pricing_coverage_by_category"]
    priced_tokens = sum(category_coverage[name]["priced_tokens"] for name in category_names)
    unpriced_tokens = sum(category_coverage[name]["unpriced_tokens"] for name in category_names)
    total_tokens = priced_tokens + unpriced_tokens
    if total_tokens == 0:
        state = "no_usage"
        cost: float | None = 0.0
    elif priced_tokens == 0:
        state = "unpriced"
        cost = None
    else:
        state = "fully_priced" if unpriced_tokens == 0 else "partially_priced"
        cost = _dashboard_cost(
            sum(
                float(value)
                for name in category_names
                if (value := token_breakdown["cost_by_category"][name]) is not None
            )
        )
    return {
        "state": state,
        "cost": cost,
        "priced_tokens": priced_tokens,
        "unpriced_tokens": unpriced_tokens,
        "coverage_percent": round((priced_tokens / total_tokens) * 100) if total_tokens else 0,
    }


@router.get("/api/dashboard", dependencies=[Depends(require_portal_auth)])
def react_dashboard_state(request: Request):
    """Bounded read-only dashboard state reusing the existing backend calculation."""

    # Imported lazily because portal imports router-adjacent modules while the
    # app wires routes. The canonical route and React handoff must share this state.
    from foreman_ai_hq.routes.portal import _dashboard_context

    context = _dashboard_context(request)
    token_breakdown = context["token_breakdown"]
    categories = token_breakdown["by_category"]
    worker_summary = context["worker_token_summary"]
    components = worker_summary.get("components") or {}
    sidebar_projects = portal_template_context(request).get("sidebar_projects", [])
    projects = [_dashboard_project_entry(request, project) for project in sidebar_projects]
    needs_you_count = sum(project["needs_you_count"] for project in projects)
    pricing_coverage = {
        "worker_execution": _dashboard_pricing_coverage(token_breakdown, "worker_execution"),
        "agent_review_reporting": _dashboard_pricing_coverage(token_breakdown, "reporting_summary"),
        "planning_estimation": _dashboard_pricing_coverage(
            token_breakdown, "control_plane", "task_breakdown"
        ),
        "setup_verification": _dashboard_pricing_coverage(token_breakdown, "adapter_verification"),
        "other": _dashboard_pricing_coverage(token_breakdown, "other"),
        "orchestration": _dashboard_pricing_coverage(
            token_breakdown,
            "control_plane",
            "task_breakdown",
            "reporting_summary",
            "adapter_verification",
        ),
        "total": _dashboard_pricing_coverage(token_breakdown, *categories),
    }

    return {
        "next_actions": [
            {
                "label": action["label"],
                "detail": action["detail"],
                "href": action["href"],
                "tone": action["tone"],
            }
            for action in context["next_actions"]
        ],
        "budget": {
            "total_tokens": context["budget_token_total"],
            "daily_cap": context["daily_cap"],
            "current_zone": context["current_zone"],
            "since": context["budget_since"],
        },
        "worker_execution": {
            "token_total": context["worker_token_total"],
            "status_split": {
                name: worker_summary["status_split"][name]
                for name in ("completed", "failed_retry", "unknown")
            },
            "components": {
                "available": bool(components.get("available")),
                "items": [
                    {"label": item.get("label", ""), "value": item.get("value", 0)}
                    for item in components.get("items", [])
                ],
                "cost": components.get("cost"),
            },
        },
        "spend": {
            "worker_execution": context["worker_token_total"],
            "orchestration": sum(
                categories[name]
                for name in (
                    "control_plane",
                    "task_breakdown",
                    "reporting_summary",
                    "adapter_verification",
                )
            ),
            "agent_review_reporting": categories["reporting_summary"],
            "planning_estimation": categories["control_plane"] + categories["task_breakdown"],
            "setup_verification": categories["adapter_verification"],
            "other": categories["other"],
            "pricing_coverage": pricing_coverage,
            "cost_by_category": {
                key: _dashboard_cost(token_breakdown["cost_by_category"][key])
                for key in categories
            },
            "total_cost": _dashboard_cost(token_breakdown["total_cost"]),
            "priced_tokens": token_breakdown["priced_tokens"],
            "unpriced_tokens": token_breakdown["unpriced_tokens"],
        },
        "alarms": {
            "total": context["alarm_count"],
            "open": context["open_alarm_count"],
            "critical": context["critical_alarm_count"],
            "recent": [
                {
                    "id": alarm["id"],
                    "type": alarm["type"],
                    "severity": alarm["severity"],
                    "session_id": alarm["session_id"],
                    "recommended_action": alarm["recommended_action"],
                }
                for alarm in context["recent_alarms"]
            ],
        },
        "active_sessions": [
            {
                "id": session["id"],
                "task_description": session["task_description"],
                "model": session["model"],
                "status": session["status"],
            }
            for session in context["active_sessions"]
        ],
        "estimation_accuracy": {
            "completed_count": context["estimation_accuracy"]["completed_count"],
            "median_error_ratio": context["estimation_accuracy"]["median_error_ratio"],
            "within_2x_pct": context["estimation_accuracy"]["within_2x_pct"],
        },
        "estimation_coefficients": _dashboard_coefficient_provenance(),
        "needs_you": {
            "count": needs_you_count,
            "project_count": len(projects),
            "projects_with_needs_you": sum(
                1 for project in projects if project["needs_you_count"] > 0
            ),
        },
        "projects": projects,
    }


def _budget_json(budget: dict) -> dict:
    """Bounded, canonical budget projection shared by the JSON endpoint and action outcomes."""

    return {
        "daily_cap_tokens": budget.get("daily_cap_tokens"),
        "session_cap_tokens": budget.get("session_cap_tokens"),
        "current_window_used_tokens": budget.get("current_window_used_tokens"),
        "current_window_remaining_tokens": budget.get("current_window_remaining_tokens"),
        "budget_since": budget.get("budget_since"),
        "daily_usage_reset_at": budget.get("daily_usage_reset_at"),
    }


@router.get("/api/settings/budget", dependencies=[Depends(require_portal_auth)])
def react_budget_settings(request: Request):
    """Bounded, authenticated budget-setup state for the React Budget Settings view.

    Reuses the same ``_effective_budget_settings`` helper that powers the canonical
    budget setup route so the React surface never recomputes budget rules.
    """

    from foreman_ai_hq.routes.portal import _effective_budget_settings

    database_path = request.app.state.settings.database_path
    budget = _effective_budget_settings(
        database_path,
        request.app.state.guardrails,
        timezone=request.app.state.settings.timezone,
    )
    return _budget_json(budget)


@router.get("/api/settings/workers", dependencies=[Depends(require_portal_auth)])
def react_worker_settings(request: Request):
    """Bounded, authenticated Worker Settings handoff for the React shell.

    Reuses the same view-model builders and active-adapter selection that power
    the canonical Worker Settings route. The projection is allow-listed and
    already sanitized through the shared evidence helpers so React never
    recomputes Worker adapter rules.
    """

    database_path = request.app.state.settings.database_path
    adapters = _worker_adapter_view_models(database_path)
    active_adapter = _active_adapter_for_request(
        adapters, request.query_params.get("adapter_id")
    )
    projects = db.list_connected_projects(database_path)
    next_action = _worker_setup_next_action(active_adapter, bool(projects))
    return {
        "adapters": [_react_worker_settings_adapter(adapter) for adapter in adapters],
        "active_adapter_id": active_adapter["id"] if active_adapter else None,
        "next_action": {
            "label": next_action["label"],
            "detail": next_action["detail"],
            "href": next_action["href"],
        },
    }


@router.get("/api/setup", dependencies=[Depends(require_portal_auth)])
def react_setup_state(request: Request):
    """Bounded, authenticated Setup Overview handoff for the React shell.

    Reuses the same readiness builders and next-step derivation that power the
    canonical Setup Overview route. The projection is allow-listed and the full
    Worker verification evidence is not serialized.
    """

    from foreman_ai_hq.routes.portal import _setup_overview_state

    state = _setup_overview_state(request)
    next_step = state["next_step"]
    active_adapter = state["active_adapter"]

    return {
        "steps": [
            {
                "name": step["name"],
                "state": step["state"],
                "href": step["href"],
                "detail": step["detail"],
            }
            for step in state["steps"]
        ],
        "ready_to_launch": state["ready_to_launch"],
        "next_step": {
            "label": next_step["label"],
            "href": next_step["href"],
            "detail": next_step["detail"],
        },
        "active_adapter": {
            "name": active_adapter["name"],
            "verification_status": active_adapter.get("verification_status"),
            "launchable": bool(active_adapter.get("launchable")),
            "tracking_mode": (active_adapter.get("tracking") or {}).get("mode"),
        } if active_adapter else None,
    }


@router.get("/api/settings/control-plane", dependencies=[Depends(require_portal_auth)])
def react_control_plane_settings(request: Request):
    """Bounded, authenticated Orchestrator Model state for the React shell.

    Projects pi's discovered inventory and verification evidence. It reads
    persisted evidence only and never invokes pi, so rendering this page cannot
    depend on the runtime being reachable.
    """

    from foreman_ai_hq.routes.portal import (
        ORCHESTRATOR_STATUS_RECORD_ID,
        _control_plane_connection_details,
        _control_plane_shadowed_settings,
        _orchestrator_job_divergence,
        orchestrator_is_configured,
    )

    settings = request.app.state.settings
    try:
        connection_status = db.get_execution_backend_status(
            settings.database_path, ORCHESTRATOR_STATUS_RECORD_ID
        )
    except KeyError:
        connection_status = None
    discovery = persisted_orchestrator_discovery(settings.database_path)
    verification = persisted_orchestrator_verification(settings.database_path)
    models = [str(model) for model in (discovery.get("models") or [])]
    return {
        "model": settings.orchestrator_model,
        "configured": orchestrator_is_configured(settings.database_path, settings.orchestrator_model),
        "inventory": {
            "models": models,
            "discovered_at": discovery.get("discovered_at"),
            "state": discovery.get("state"),
            # Distinct from "discovery failed": the operator's action is `pi /login`.
            "needs_authentication": discovery.get("state") == DISCOVERY_NEEDS_AUTHENTICATION,
            "reasons": discovery.get("reasons") or [],
        },
        "verification": {
            "passed": bool(verification.get("passed")),
            "verified_at": verification.get("verified_at"),
            "model": verification.get("model"),
            "stale": orchestrator_verification_is_stale(verification, settings.orchestrator_model),
            "reasons": verification.get("reasons") or [],
        },
        "diverging_jobs": _orchestrator_job_divergence(settings),
        "shadowed_settings": _control_plane_shadowed_settings(settings),
        "connection_status": _control_plane_connection_details(connection_status),
    }


@router.get("/api/settings/project", dependencies=[Depends(require_portal_auth)])
def react_project_settings(request: Request):
    """Bounded, authenticated project settings handoff for the React shell.

    Reuses the same Local Runner backend, project capability evaluation, and
    connected/archived project listings that power the canonical project settings
    route. The projection is allow-listed and sanitized so React never
    recomputes project rules or leaks raw backend/capability evidence.
    """

    from foreman_ai_hq.routes.portal import _local_backend

    database_path = request.app.state.settings.database_path
    local_runner_enabled = request.app.state.settings.local_runner_enabled
    backend = None
    backend_status = None
    if local_runner_enabled:
        try:
            backend = _local_backend(request)
            backend_status = _react_project_settings_backend_status(backend)
        except Exception:
            # Never leak raw exception text for backend evaluation failures.
            backend_status = None

    connected_projects = _react_project_settings_list(
        request, db.list_connected_projects(database_path), backend
    )
    archived_projects = _react_project_settings_list(
        request, db.list_archived_connected_projects(database_path), backend
    )

    error = request.query_params.get("error") or None
    if error:
        error = str(safe_evidence(error, max_length=1000))[:1000] or None

    return {
        "local_runner_enabled": local_runner_enabled,
        "backend_status": backend_status,
        "connected_projects": connected_projects,
        "archived_projects": archived_projects,
        "error": error,
    }


def _react_project_settings_list(
    request: Request, projects: list[dict[str, Any]], backend
) -> list[dict[str, Any]]:
    """Project list with bounded, sanitized capability projection."""

    result = []
    for project in projects:
        try:
            result.append(_react_project_settings_project(project, backend))
        except Exception:
            # Skip projects whose capability evaluation fails unexpectedly.
            continue
    return result


def _safe_optional_text(value: Any, max_length: int) -> str | None:
    """Return bounded text or None, without turning None into the string 'None'."""
    if value is None:
        return None
    return str(safe_evidence(value, max_length=max_length))[:max_length]


def _react_project_settings_project(
    project: dict[str, Any], backend
) -> dict[str, Any]:
    """Bounded project entry for the Project Settings React handoff."""

    capability = _react_project_settings_capability(project, backend)
    profile = project.get("profile") or {}
    return {
        "id": str(safe_evidence(project.get("id", ""), max_length=128))[:128],
        "name": str(safe_evidence(project.get("name", ""), max_length=200))[:200],
        "root_path": str(safe_evidence(project.get("root_path", ""), max_length=4096))[:4096],
        "capability": capability,
        "profile": {
            "test_command_suggested": _safe_optional_text(profile.get("test_command_suggested"), 256),
            "test_command": _safe_optional_text(profile.get("test_command"), 256),
            "test_command_confirmed": bool(profile.get("test_command_confirmed")),
            "base_branch_suggested": _safe_optional_text(profile.get("base_branch_suggested"), 128),
            "base_branch": _safe_optional_text(profile.get("base_branch"), 128),
            "base_branch_confirmed": bool(profile.get("base_branch_confirmed")),
        },
    }


def _react_project_settings_capability(
    project: dict[str, Any], backend
) -> dict[str, Any]:
    """Sanitized capability projection limited to state + reasons."""

    raw = None
    if backend is not None:
        try:
            raw = backend.project_capability(project)
        except Exception:
            raw = {"state": "unknown", "reasons": ["Could not evaluate project capability."]}
    if raw is None:
        raw = project.get("capability") or {}
    if not isinstance(raw, dict):
        raw = {}
    state = raw.get("state")
    if not isinstance(state, str) or not state:
        state = "unknown"
    reasons = raw.get("reasons")
    if not isinstance(reasons, list):
        reasons = []
    safe_reasons = [
        str(safe_evidence(reason, max_length=1000))[:1000]
        for reason in reasons
        if isinstance(reason, str)
    ]
    return {"state": state, "reasons": safe_reasons[:20]}


def _react_project_settings_backend_status(backend) -> dict[str, Any] | None:
    """Sanitized Local Runner backend status for the React handoff."""

    if backend is None:
        return None
    try:
        status = backend.status()
    except Exception:
        return None
    if not isinstance(status, dict):
        return None
    safe = safe_evidence(status, max_length=2000)
    return {
        "online": bool(safe.get("online")),
        "name": str(safe_evidence(safe.get("name", ""), max_length=200))[:200] or None,
        "checked_at": str(safe_evidence(safe.get("checked_at", ""), max_length=64))[:64] or None,
        "details": safe.get("details") if isinstance(safe.get("details"), dict) else None,
    }


def _dashboard_project_entry(request: Request, project: dict) -> dict:
    """Project-card fields only; never return workspace path or configuration."""

    capability = _project_view_model(request, project).get("capability") or {}
    project_id = str(project["id"])
    return {
        "id": project_id,
        "name": project.get("name", ""),
        "task_count": project.get("task_count", 0),
        "needs_you_count": _needs_you_state(
            request.app.state.settings.database_path, project_id
        )["count"],
        "capability": {"state": capability.get("state", "unknown")},
    }


_ALARM_FILTER_OPTIONS = [
    {"value": "open", "label": "Open"},
    {"value": "resolved", "label": "Resolved"},
    {"value": "all", "label": "All"},
]


@router.get("/api/alarms", dependencies=[Depends(require_portal_auth)])
def react_alarms_state(
    request: Request,
    filter_param: str = Query(default="open", alias="filter"),
):
    """Bounded, authenticated JSON handoff for the React Alarms inbox."""

    database_path = request.app.state.settings.database_path
    selected_filter = filter_param if filter_param in {"open", "resolved", "all"} else "open"
    # Fetch every alarm once; derive counts and the selected subset in Python so
    # the endpoint issues one alarm query instead of one per filter option.
    all_alarms = db.list_alarms(database_path)
    open_alarms = [alarm for alarm in all_alarms if not alarm.get("resolved_at")]
    resolved_alarms = [alarm for alarm in all_alarms if alarm.get("resolved_at")]
    by_filter = {"open": open_alarms, "resolved": resolved_alarms, "all": all_alarms}
    counts = {"open": len(open_alarms), "resolved": len(resolved_alarms), "all": len(all_alarms)}
    selected = by_filter[selected_filter]
    # Batch the resolved-action lookup for the projected alarms into one query.
    actions_by_alarm = db.latest_actions_for_alarms(
        database_path, [alarm["id"] for alarm in selected if alarm.get("resolved_at")]
    )
    return {
        "filters": [
            {
                "label": option["label"],
                "value": option["value"],
                "selected": option["value"] == selected_filter,
                "count": counts[option["value"]],
            }
            for option in _ALARM_FILTER_OPTIONS
        ],
        "selected_filter": selected_filter,
        "alarms": [_react_alarm(alarm, actions_by_alarm.get(alarm["id"])) for alarm in selected],
    }


def _react_alarm(alarm: dict[str, Any], resolved_action: dict[str, Any] | None) -> dict[str, Any]:
    """Bounded projection of an alarm for the React inbox."""

    session_id = alarm.get("session_id")
    resolved = alarm.get("resolved_at") is not None
    resolved_action_name = None
    resolved_payload_summary = None
    if resolved and resolved_action:
        resolved_action_name = _bounded_scalar(resolved_action.get("action"), 100)
        resolved_payload_summary = _bounded_redacted_text(resolved_action.get("payload"), 2000)
    return {
        "id": _bounded_scalar(alarm.get("id"), 200),
        "type": _bounded_scalar(alarm.get("type"), 100),
        "severity": _bounded_scalar(alarm.get("severity"), 100),
        "session_id": _bounded_scalar(session_id, 200),
        "session_href": _safe_local_href(f"/sessions/{session_id}") if session_id else None,
        "context": _bounded_redacted_text(alarm.get("context"), 2000),
        "recommended_action": _bounded_scalar(alarm.get("recommended_action"), 1000),
        "available_actions": db.available_actions_for_alarm(alarm),
        "resolved_action": resolved_action_name,
        "resolved_payload_summary": resolved_payload_summary,
        "resolved_at": _optional_scalar(alarm.get("resolved_at"), 64),
    }


@router.get("/api/projects", dependencies=[Depends(require_portal_auth)])
def react_projects_state(request: Request):
    """JSON connected-project list for the shell home / project picker.

    Reuses the same project-list and task-count helpers that feed the canonical
    projects route; no new schema and no parallel API semantics.
    """

    database_path = request.app.state.settings.database_path
    projects = []
    for project in db.list_connected_projects(database_path):
        view = _project_view_model(request, project)
        counts = project_board_counts(database_path, str(project["id"]))
        projects.append({**view, "counts": counts, "total_tasks": sum(counts.values())})
    archived_projects = [
        _react_projects_archived_project(request, project)
        for project in db.list_archived_connected_projects(database_path)
    ]
    return {
        "projects": projects,
        "archived_projects": archived_projects,
        "local_runner_enabled": request.app.state.settings.local_runner_enabled,
    }


@router.get(
    "/api/projects/{project_id}/workspace",
    dependencies=[Depends(require_portal_auth)],
)
def react_project_workspace_state(project_id: str, request: Request):
    """Bounded project workspace state derived from existing Portal helpers."""

    database_path = request.app.state.settings.database_path
    stored_project = _ensure_project(database_path, project_id)
    # Stored profile/capability JSON is operator-controlled evidence. Normalize
    # malformed containers before invoking shared capability/summary helpers.
    helper_project = {
        **stored_project,
        "profile": _mapping(stored_project.get("profile")),
        "capability": _mapping(stored_project.get("capability")),
    }
    project = _project_view_model(request, helper_project)
    project = {
        **project,
        "profile": _mapping(project.get("profile")),
        "capability": _mapping(project.get("capability")),
    }
    summary = project_workspace_summary(database_path, project)
    return _react_workspace_projection(project, summary)


def _react_workspace_projection(project: dict, summary: dict) -> dict:
    """Convert broad workspace state into the fixed browser-safe contract."""

    project_id = _workspace_string(project.get("id"), 128)
    profile = _mapping(project.get("profile"))
    capability = _mapping(project.get("capability"))
    summary = _mapping(summary)
    archived_at = _workspace_optional_string(project.get("archived_at"), 64)
    archived = archived_at is not None
    board_href = None if archived else f"/projects/{project_id}"
    restore_href = f"/projects/{project_id}/restore" if archived else None
    counts = _workspace_counts(summary.get("counts"))

    return {
        "project": {
            "id": project_id,
            "name": _workspace_string(project.get("name"), 200),
            "root_path": _workspace_string(project.get("root_path"), 4096),
            "archived_at": archived_at,
            "capability": {
                "state": _workspace_string(capability.get("state"), 64),
                "label": _workspace_string(capability.get("label"), 200),
                "reasons": _workspace_string_list(capability.get("reasons"), 20, 1000),
            },
            "profile": {
                "git_branch": _workspace_optional_string(profile.get("git_branch"), 500),
                "language_hints": _workspace_string_list(profile.get("language_hints"), 20, 200),
                "framework_hints": _workspace_string_list(profile.get("framework_hints"), 20, 200),
                "package_manager_hints": _workspace_string_list(
                    profile.get("package_manager_hints"), 20, 200
                ),
                "test_command": _workspace_optional_string(profile.get("test_command"), 4000),
                # A detected command stays visible before confirmation so the overview
                # shows why a write-capable launch is still blocked.
                "test_command_suggested": _workspace_optional_string(profile.get("test_command_suggested"), 4000),
                "test_command_confirmed": _workspace_bool(profile.get("test_command_confirmed")),
                "run_command": _workspace_optional_string(profile.get("run_command"), 4000),
                "relevant_docs": _workspace_string_list(profile.get("relevant_docs"), 50, 1000),
            },
        },
        "summary": {
            "counts": counts,
            "total_tasks": sum(counts.values()),
            "launch_ready": _workspace_bool(summary.get("launch_ready")) and not archived,
            "capability_state": _workspace_string(summary.get("capability_state"), 64),
            "attention_actions": _workspace_attention_actions(
                summary.get("attention_actions"), project_id
            ),
        },
        "controls": {
            "can_open_board": not archived,
            "can_restore": archived,
        },
        "links": {
            "board_href": board_href,
            "floor_href": None if archived else f"/projects/{project_id}/floor",
            "task_history_href": f"/projects/{project_id}/task-history",
            "sessions_href": "/sessions",
            "worker_setup_href": "/settings/workers",
            "project_settings_href": "/settings/project",
            "restore_href": restore_href,
        },
    }


def _workspace_string(value, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return str(safe_evidence(value, max_length=limit))[:limit]


def _workspace_optional_string(value, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = _workspace_string(value, limit)
    return text or None


def _workspace_string_list(value, item_limit: int, text_limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        _workspace_string(item, text_limit)
        for item in value[:item_limit]
        if isinstance(item, str)
    ]


def _workspace_counts(value) -> dict[str, int]:
    counts = _mapping(value)
    bounded = {}
    for column in BOARD_COLUMNS:
        count = counts.get(column)
        bounded[column] = (
            count
            if isinstance(count, int) and not isinstance(count, bool) and count >= 0
            else 0
        )
    return bounded


def _workspace_bool(value) -> bool:
    return value if isinstance(value, bool) else False


def _workspace_attention_actions(value, project_id: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    actions = []
    for raw_action in value:
        if not isinstance(raw_action, dict):
            continue
        href = _workspace_action_href(raw_action.get("href"), project_id)
        if href is None:
            continue
        actions.append(
            {
                "label": _workspace_string(raw_action.get("label"), 200),
                "detail": _workspace_string(raw_action.get("detail"), 1000),
                "href": href[:2048],
                "tone": _workspace_string(raw_action.get("tone"), 32),
            }
        )
        if len(actions) == 20:
            break
    return actions


def _workspace_action_href(value, project_id: str) -> str | None:
    if not isinstance(value, str):
        return None
    board_href = f"/projects/{project_id}"
    allowed = {
        f"/projects/{project_id}/board": board_href,
        f"/app/projects/{project_id}/board": board_href,
        f"/projects/{project_id}": board_href,
        f"/projects/{project_id}/needs-you": f"/projects/{project_id}/needs-you",
        f"/projects/{project_id}/floor": f"/projects/{project_id}/floor",
        f"/projects/{project_id}/task-history": f"/projects/{project_id}/task-history",
        "/sessions": "/sessions",
        "/settings/workers": "/settings/workers",
        "/settings/project": "/settings/project",
    }
    return allowed.get(value)


@router.get(
    "/api/projects/{project_id}/board",
    dependencies=[Depends(require_portal_auth)],
)
def react_project_board_state(project_id: str, request: Request):
    """Bounded operator board state; existing backend context stays source of truth."""

    database_path = request.app.state.settings.database_path
    project = _ensure_project(database_path, project_id)
    if db.project_is_archived(project):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="restore archived project before opening its active board",
        )
    project = _project_view_model(request, project)
    context = board_page_context(
        database_path,
        active_project=project,
        default_proxy_url=DEFAULT_PROXY_URL,
    )
    return _react_board_projection(project, context)


@router.get(
    "/api/projects/{project_id}/needs-you",
    dependencies=[Depends(require_portal_auth)],
)
def react_project_needs_you(project_id: str, request: Request):
    database_path = request.app.state.settings.database_path
    _ensure_project(database_path, project_id)
    return _needs_you_state(database_path, project_id)


def _needs_you_state(database_path, project_id: str) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for breakdown in db.list_task_breakdowns_for_project(database_path, project_id):
        failed = breakdown.get("status") == "failed"
        intake_metadata = _mapping(breakdown.get("intake_metadata"))
        candidates = breakdown.get("candidates")
        items.append(
            {
                "id": f"breakdown:{breakdown['id']}",
                "kind": "breakdown_review",
                "title": "Task breakdown needs recovery" if failed else "Task breakdown awaits review",
                "reason": _bounded_scalar(
                    breakdown.get("error") or "Review proposed vertical slices before creating tasks.",
                    1000,
                ),
                "action_label": "Retry or replace" if failed else "Review breakdown",
                "href": f"/task-breakdowns/{breakdown['id']}/review",
                "created_at": _optional_scalar(breakdown.get("created_at"), 64),
                "source": _bounded_scalar(
                    intake_metadata.get("source_name") or "Pasted task description",
                    500,
                ),
                "candidate_count": len(candidates) if isinstance(candidates, list) else 0,
                "status": _bounded_scalar(breakdown.get("status"), 64),
                "breakdown_id": str(breakdown["id"]),
                "task_id": None,
            }
        )

    tasks = project_bound_tasks(db.list_tasks(database_path), project_id)
    for task in tasks:
        if db.task_is_archived(task):
            continue
        metadata = _mapping(task.get("metadata"))
        blocked_condition = _mapping(metadata.get("blocked_condition"))
        item = _needs_you_task_item(database_path, project_id, task, metadata, blocked_condition)
        if item:
            items.append(item)
    priority = {
        "breakdown_review": 0,
        "manual_estimate": 1,
        "low_confidence_estimate": 2,
        "launch_guardrail": 3,
        "review_disposition": 4,
        "budget_override": 5,
    }
    items.sort(key=lambda item: priority[item["kind"]])
    return {"project_id": project_id, "count": len(items), "items": items}


def _needs_you_task_item(
    database_path,
    project_id: str,
    task: dict[str, Any],
    metadata: dict[str, Any],
    blocked_condition: dict[str, Any],
) -> dict[str, Any] | None:
    lc_item = low_confidence_item(project_id, task, database_path)
    if lc_item:
        return lc_item
    kind = title = action_label = None
    href = f"/projects/{project_id}#task-{task['id']}"
    reason = blocked_condition.get("reason") or metadata.get("blocked_reason")
    if task.get("status") == "Estimated" and metadata.get("budget_override_available"):
        kind, title, action_label = "budget_override", "Budget override awaits approval", "Review budget override"
    elif task.get("status") == "Estimated" and metadata.get("requires_manual_estimate"):
        kind, title, action_label = "manual_estimate", "Task needs manual estimate", "Estimate task"
    elif task.get("status") == "Estimated" and blocked_condition:
        kind, title, action_label = "launch_guardrail", "Launch guardrail needs resolution", "Resolve launch blocker"
    elif task.get("status") == "Review" and not metadata.get("review_decision"):
        kind, title, action_label = "review_disposition", "Worker run awaits review", "Review evidence"
        href = f"/projects/{project_id}/floor#task-{task['id']}"
        reason = reason or "Choose Mark Done or Block after reviewing Worker evidence."
    if kind is None:
        return None
    return {
        "id": f"task:{task['id']}:{kind}",
        "kind": kind,
        "title": title,
        "reason": _bounded_scalar(reason or title, 1000),
        "action_label": action_label,
        "href": href,
        "created_at": _optional_scalar(task.get("created_at"), 64),
        "breakdown_id": None,
        "task_id": str(task["id"]),
    }


@router.get(
    "/api/projects/{project_id}/task-history",
    dependencies=[Depends(require_portal_auth)],
)
def react_project_task_history(project_id: str, request: Request):
    """Bounded, read-only project task history for the React shell.

    Reuses the same backend context builder and projection helpers so filter
    counts, archive state, and per-task evidence stay single-sourced.
    """

    database_path = request.app.state.settings.database_path
    project = _project_view_model(request, _ensure_project(database_path, project_id))
    context = project_task_history_context(
        database_path,
        active_project=project,
        selected_filter=request.query_params.get("filter", "all"),
    )
    return _react_history_projection(context)


def _react_board_projection(project: dict, context: dict) -> dict:
    """Convert broad backend board context into an explicit browser-safe allowlist."""

    board_summary = context["board_summary"]
    automation = context.get("automation_summary") or {}
    return {
        "project": {"id": str(project["id"]), "name": project.get("name", "")},
        "columns": list(BOARD_COLUMNS),
        "board_summary": {
            "launch_ready": bool(board_summary.get("launch_ready")),
            "total_tasks": int(board_summary.get("total_tasks") or 0),
            "counts": _canonical_counts(board_summary.get("counts") or {}),
            "archived_count": int(board_summary.get("archived_count") or 0),
            "history_total_tasks": int(board_summary.get("history_total_tasks") or 0),
        },
        "history_href": f"/projects/{project['id']}/task-history",
        "board_empty_states": {
            column: str((context.get("board_empty_states") or {}).get(column) or "")
            for column in BOARD_COLUMNS
        },
        "automation": {
            "counts": _canonical_counts(automation.get("counts") or {}),
            "eligible_count": int(automation.get("eligible_count") or 0),
            "queue": {
                "status": (automation.get("queue") or {}).get("status") or "idle",
                "auto_agent_review": bool((automation.get("queue") or {}).get("auto_agent_review")),
                "latest_stop_reason": (automation.get("queue") or {}).get("latest_stop_reason"),
            },
            "live_refresh_enabled": bool(automation.get("live_refresh_enabled")),
        },
        "adapters": [_react_adapter(adapter) for adapter in context.get("adapters") or []],
        "tasks_by_status": {
            column: [_react_task(task) for task in (context.get("tasks_by_status") or {}).get(column, [])]
            for column in BOARD_COLUMNS
        },
    }


def _react_history_projection(context: dict) -> dict:
    """Convert the project task history context into a bounded JSON contract."""

    return {
        "filters": [_react_history_filter(filter) for filter in context["history_filters"]],
        "selected_filter": _bounded_scalar(context.get("selected_filter"), 32),
        "tasks": [_react_history_task(task) for task in context.get("tasks", [])],
    }


def _react_history_filter(filter: dict) -> dict:
    return {
        "label": _bounded_scalar(filter.get("label"), 32),
        "value": _bounded_scalar(filter.get("value"), 32),
        "count": int(filter.get("count") or 0),
        "active": bool(filter.get("active")),
    }


def _react_history_task(task: dict) -> dict:
    metadata = _mapping(task.get("metadata"))
    session_id = task.get("session_id")
    session_href = _safe_local_href(f"/sessions/{session_id}") if session_id else None
    return {
        "id": str(task.get("id", ""))[:200],
        "description": _bounded_scalar(task.get("description"), 12000),
        "status": str(task.get("status", ""))[:64],
        "task_kind": read_task_kind(metadata),
        "archived": bool(db.task_is_archived(task)),
        "archived_at": _optional_scalar(metadata.get("archived_at"), 64),
        "estimate_tokens": _optional_number(
            task.get("estimate_tokens"), integer=True, minimum=0, maximum=10**15
        ),
        "actual_tokens": _optional_number(
            task.get("actual_tokens"), integer=True, minimum=0, maximum=10**15
        ),
        "recommended_model": _optional_scalar(task.get("recommended_model"), 200),
        "session_href": session_href,
        "worker_run_id": _optional_scalar(metadata.get("active_worker_run_id"), 200),
        "blocked_reason": _bounded_scalar(metadata.get("blocked_reason"), 1000),
        "requires_manual_estimate": bool(metadata.get("requires_manual_estimate")),
    }


def _canonical_counts(value: dict) -> dict[str, int]:
    return {column: int(value.get(column) or 0) for column in BOARD_COLUMNS}


def _react_adapter(adapter: dict) -> dict:
    tracking = adapter.get("tracking") or {}
    return {
        "id": adapter.get("id"),
        "name": adapter.get("name") or "",
        "is_default": bool(adapter.get("is_default")),
        "launchable": bool(adapter.get("launchable")),
        "allowed_models": list(adapter.get("supported_models") or []),
        "tracking": {
            "mode": tracking.get("mode"),
            "label": adapter.get("tracking_label") or tracking.get("label"),
            "runtime_request_guardrails": tracking.get("runtime_request_guardrails"),
            "accounting": tracking.get("accounting"),
            "budget_authoritative": tracking.get("budget_authoritative"),
            "launchable_for_board": tracking.get("launchable_for_board"),
        },
    }


def _react_worker_settings_adapter(adapter: dict) -> dict:
    """Allow-listed, sanitized projection for the Worker Settings React handoff."""

    tracking = adapter.get("tracking") or {}
    diagnostics = _worker_settings_diagnostics(adapter.get("diagnostics") or {})
    verification_evidence = adapter.get("verification_evidence") or {}
    if not verification_evidence:
        verification_evidence = None
    verification_diagnostic = adapter.get("verification_diagnostic")
    if not isinstance(verification_diagnostic, dict) or not verification_diagnostic:
        verification_diagnostic = None
    return {
        "id": adapter.get("id"),
        "kind": adapter.get("kind"),
        "configured": bool(adapter.get("configured")),
        "is_default": bool(adapter.get("is_default")),
        "connection_type": adapter.get("connection_type"),
        "tracking": {
            "mode": tracking.get("mode"),
            "label": adapter.get("tracking_label") or tracking.get("label"),
            "runtime_request_guardrails": tracking.get("runtime_request_guardrails"),
            "accounting": tracking.get("accounting"),
            "budget_authoritative": tracking.get("budget_authoritative"),
            "launchable_for_board": tracking.get("launchable_for_board"),
        },
        "tracking_mode_options": [
            {
                "mode": option.get("mode"),
                "label": option.get("label"),
                "runtime_request_guardrails": option.get("runtime_request_guardrails"),
                "accounting": option.get("accounting"),
                "budget_authoritative": option.get("budget_authoritative"),
                "launchable_for_board": option.get("launchable_for_board"),
            }
            for option in (adapter.get("tracking_mode_options") or [])
            if isinstance(option, dict)
        ],
        "discovered_models": list(adapter.get("discovered_models") or []),
        "supported_models": list(adapter.get("supported_models") or []),
        "launchable": bool(adapter.get("launchable")),
        "diagnostics": diagnostics,
        "verification_evidence": verification_evidence,
        "verification_diagnostic": verification_diagnostic,
        "model_discovery_label": adapter.get("model_discovery_label"),
    }


def _worker_settings_diagnostics(diagnostics: dict) -> dict | None:
    """Return sanitized diagnostics without raw filesystem paths or exception text."""

    safe = safe_evidence(diagnostics)
    if not safe:
        return None
    # Never leak raw executable filesystem paths; command name alone is safe.
    safe.pop("executable", None)
    return safe


def _bounded_text(value, limit: int) -> dict:
    text = str(safe_evidence(value or ""))
    return {"text": text[:limit], "truncated": len(text) > limit}


def _bounded_redacted_text(value, limit: int) -> dict:
    """Redact secrets from a dict/list, then serialize and bound for display.

    Preserves budget-token keys such as ``session_cap_tokens`` that are
    evidence, not credentials, by using the key-aware ``db._sanitize_evidence``
    before string-level redaction.
    """
    cleaned = db._sanitize_evidence(value or "")
    text = str(safe_evidence(json.dumps(cleaned, sort_keys=True, separators=(",", ":")), max_length=limit * 4))
    return {"text": text[:limit], "truncated": len(text) > limit}


def _bounded_scalar(value, limit: int) -> str:
    return str(safe_evidence(value or ""))[:limit]


def _optional_scalar(value, limit: int) -> str | None:
    return None if value is None else _bounded_scalar(value, limit)


def _optional_number(
    value,
    *,
    integer: bool = False,
    minimum: int | float,
    maximum: int | float,
) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value < minimum or value > maximum:
        return None
    if integer:
        if isinstance(value, float) and not value.is_integer():
            return None
        return int(value)
    return value


def _safe_local_href(value) -> str | None:
    href = _optional_scalar(value, 500)
    return href if href and href.startswith("/") and not href.startswith("//") else None


def _mapping(value) -> dict:
    return value if isinstance(value, dict) else {}


def _react_task(task: dict) -> dict:
    metadata = _mapping(task.get("metadata"))
    raw_events = metadata.get("worker_run_events")
    events = [event for event in raw_events if isinstance(event, dict)] if isinstance(raw_events, list) else []
    blocked_condition = _mapping(metadata.get("blocked_condition"))
    launch_diagnostic = _mapping(metadata.get("launch_diagnostic"))
    launch_failure = _mapping(metadata.get("last_launch_failure"))
    # A retryable run failure (not a guardrail block, which uses blocked_condition)
    # keeps the task Estimated and launchable, so the card must still say why the
    # last launch failed and let the operator retry — "show, don't reassure".
    has_launch_failure = bool(metadata.get("last_launch_failure") or metadata.get("launch_error"))
    return {
        "id": task.get("id"),
        "status": task.get("status"),
        "summary": _bounded_text(task.get("description"), 400),
        "task_kind": read_task_kind(metadata),
        "estimate_tokens": task.get("estimate_tokens"),
        "actual_tokens": task.get("actual_tokens"),
        "recommended_model": _optional_scalar(task.get("recommended_model"), 200),
        "launch_model": _optional_scalar(metadata.get("launch_model"), 200),
        "session_href": f"/sessions/{task['session_id']}" if task.get("session_id") else None,
        "review_prompt": _bounded_text(metadata.get("review_prompt"), 4000),
        "timeline": [
            {
                "id": _optional_number(event.get("id"), integer=True, minimum=0, maximum=10**15),
                "created_at": _bounded_scalar(event.get("created_at"), 100),
                "kind": _bounded_scalar(event.get("kind"), 100),
                "layer": _bounded_scalar(event.get("layer"), 100),
                "title": _bounded_scalar(event.get("title"), 400),
                "detail_summary": _bounded_text(event.get("detail_summary") or event.get("detail"), 1000),
            }
            for event in events[-6:]
        ],
        "task_branch": _optional_scalar(metadata.get("task_branch"), 256),
        "harness_commit": _react_harness_commit(metadata.get("harness_commit")),
        "pull_request": _react_pull_request(metadata.get("pull_request")),
        "intake_decision": _optional_scalar(metadata.get("intake_decision"), 32),
        "intake_decision_reason": _bounded_text(metadata.get("intake_decision_reason"), 240),
        "blocked_condition": {
            "reason": _bounded_scalar(blocked_condition.get("reason"), 1000),
            "origin": _bounded_scalar(blocked_condition.get("origin"), 100),
            "timestamp": _optional_scalar(blocked_condition.get("timestamp"), 64),
        } if blocked_condition else None,
        # Slim, card-sized failure annotation only. The runner summary is a short
        # preview (truncated flag set when longer); the full verbose stderr/stdout
        # stays deferred to the session report, never inlined on the board card.
        "launch_failure": {
            "error": _bounded_text(metadata.get("launch_error"), 400),
            "summary": _bounded_text(launch_failure.get("error") or launch_failure.get("stderr") or "", 240),
            "returncode": _optional_number(
                launch_failure.get("returncode"), integer=True, minimum=-(2**31), maximum=2**31 - 1
            ),
            "retryable": bool(metadata.get("launch_retryable")),
            "diagnostic": _bounded_text(launch_diagnostic.get("summary"), 400),
            "next_action": _bounded_text(launch_diagnostic.get("next_action"), 400),
            "setup_href": _safe_local_href(launch_diagnostic.get("setup_href")),
        } if has_launch_failure else None,
        "controls": _task_controls(task, metadata, blocked_condition),
    }


def _react_harness_commit(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or not value.get("sha"):
        return None
    return {
        "sha": _optional_scalar(value.get("sha"), 64),
        "message": _bounded_text(value.get("message"), 240),
    }


def _react_pull_request(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or not value.get("url"):
        return None
    return {
        "url": _optional_scalar(value.get("url"), 512),
        "base_branch": _optional_scalar(value.get("base_branch"), 128),
        "head_branch": _optional_scalar(value.get("head_branch"), 256),
    }


def _task_controls(task: dict[str, Any], metadata: dict[str, Any], blocked_condition: dict[str, Any] | None) -> dict[str, Any]:
    """Compute operator-visible controls for a task card and evidence drawer."""
    review_state = _mapping(metadata.get("review_disposition_state"))
    available = set(review_state.get("available_actions") or [])
    in_review = task.get("status") == "Review"
    review_actions_available = bool(metadata.get("review_actions_available"))
    return {
        "can_launch": task.get("status") == "Estimated",
        "requires_manual_estimate": bool(metadata.get("requires_manual_estimate")),
        "can_refresh": task.get("status") == "Running",
        "can_save_review_prompt": review_actions_available,
        "can_agent_review": review_actions_available,
        "can_mark_done": review_actions_available,
        "can_block": review_actions_available,
        "can_approve_commit": in_review and "approve_commit" in available,
        "can_open_pr": in_review and "open_pr" in available,
        # A determined PR capability must render an action or a stated reason, never nothing.
        "pr_unavailable_reason": _optional_scalar(review_state.get("pr_unavailable_reason"), 300)
        if in_review and metadata.get("harness_commit")
        else None,
        "can_archive": task.get("status") == "Done",
        "can_dismiss": task.get("status") == "Estimated"
        or (in_review and bool(blocked_condition)),
        "budget_override_available": bool(metadata.get("budget_override_available")),
        "native_usage_override_ack_required": bool(metadata.get("native_usage_override_ack_required")),
        "native_usage_override_ack_text": _optional_scalar(
            metadata.get("native_usage_override_ack_text"), 1000
        ),
        "setup_href": _safe_local_href(_mapping(metadata.get("launch_diagnostic")).get("setup_href"))
        or "/settings/workers",
    }


def _ensure_project(database_path, project_id: str) -> dict:
    try:
        return db.get_connected_project(database_path, project_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="connected project not found",
        ) from exc


def _project_view_model(request: Request, project: dict) -> dict:
    # Reuse the Portal's project view model so capability enrichment matches the
    # server-rendered pages. Imported lazily to avoid an import cycle at module
    # load (portal imports from tasks; app wires all routers together).
    from foreman_ai_hq.routes.portal import _project_view_model as portal_view_model

    return portal_view_model(request, project)


def _react_projects_archived_project(request: Request, project: dict) -> dict:
    """Bounded, sanitized archived-project row for the Projects JSON handoff."""

    view = _project_view_model(request, project)
    capability = view.get("capability") or {}
    if not isinstance(capability, dict):
        capability = {}
    raw_reasons = capability.get("reasons")
    if not isinstance(raw_reasons, list):
        raw_reasons = []
    safe_reasons = [
        str(safe_evidence(reason, max_length=1000))[:1000]
        for reason in raw_reasons
        if isinstance(reason, str)
    ]
    archived_at = project.get("archived_at")
    if not isinstance(archived_at, str):
        archived_at = None
    return {
        "id": str(safe_evidence(project.get("id", ""), max_length=128))[:128],
        "name": str(safe_evidence(project.get("name", ""), max_length=200))[:200],
        "root_path": str(safe_evidence(project.get("root_path", ""), max_length=4096))[:4096],
        "archived_at": archived_at,
        "capability": {
            "state": _optional_scalar(capability.get("state"), 64) or "unknown",
            "label": _optional_scalar(capability.get("label"), 200) or None,
            "reasons": safe_reasons[:20] or None,
        },
    }
