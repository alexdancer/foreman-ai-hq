from __future__ import annotations

import hashlib
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from foreman_ai_hq import db
from foreman_ai_hq.auth import require_portal_auth
from foreman_ai_hq.checkpoints import evaluate_checkpoints
from foreman_ai_hq.guardrails import get_budget_zone

router = APIRouter()


class SessionStartRequest(BaseModel):
    task_description: str = Field(min_length=1)
    model: str = Field(min_length=1)
    budget: dict[str, Any] | None = None
    guardrail_overrides: dict[str, Any] | None = None


def _database_path(request: Request):
    return request.app.state.settings.database_path


def _guardrails(request: Request):
    return request.app.state.guardrails


@router.post("/session/start", dependencies=[Depends(require_portal_auth)])
def start_session(payload: SessionStartRequest, request: Request) -> dict[str, Any]:
    session_api_key = f"sk_sess_{secrets.token_urlsafe(24)}"
    database_path = _database_path(request)
    budget = payload.budget or {}
    guardrail_overrides = dict(payload.guardrail_overrides or {})
    if budget:
        # Persist budget overrides inside guardrails so the proxy can enforce them later.
        guardrail_overrides["budget"] = budget
    session = db.create_session(
        database_path,
        task_description=payload.task_description,
        model=payload.model,
        # Only the hash is stored; the raw bearer key is returned once to the caller.
        session_key_hash=_hash_key(session_api_key),
        guardrail_overrides=guardrail_overrides,
    )
    config = _guardrails(request)
    daily_used_tokens = int(budget.get("daily_used_tokens", 0)) + db.budgeted_token_usage(
        database_path,
        since=db.effective_daily_budget_window_start(database_path, timezone=request.app.state.settings.timezone),
    )
    starting_zone = get_budget_zone(
        daily_used_tokens,
        _daily_cap_tokens(budget, config, database_path),
        config,
    )
    return {
        "session_id": session["id"],
        "session_api_key": session_api_key,
        "starting_zone": starting_zone,
        "report_url": f"/session/{session['id']}/report",
    }


@router.get("/session/{session_id}/report", dependencies=[Depends(require_portal_auth)])
def session_report(session_id: str, request: Request) -> dict[str, Any]:
    artifact = _artifact_or_404(request, session_id)
    token_totals = _token_totals(artifact)
    token_breakdown = db.session_token_breakdown(_database_path(request), session_id)
    config = _guardrails(request)
    budget = artifact["session"].get("guardrail_overrides", {}).get("budget", {})
    # Reports show the session's own spend plus any daily usage supplied at launch time.
    daily_used_tokens = int(budget.get("daily_used_tokens", 0)) + int(token_breakdown["total_tokens"])
    current_zone = get_budget_zone(daily_used_tokens, _daily_cap_tokens(budget, config), config)
    return {
        "session": artifact["session"],
        "task_metadata": {
            "description": artifact["session"]["task_description"],
            "model": artifact["session"]["model"],
            "status": artifact["session"]["status"],
        },
        "token_totals": token_totals,
        "current_zone": current_zone,
        "alarms": artifact["alarms"],
        "checkpoints": artifact["checkpoint_results"],
        "tool_breakdown": _tool_breakdown(artifact),
    }


@router.get("/session/{session_id}/artifact", dependencies=[Depends(require_portal_auth)])
def session_artifact(session_id: str, request: Request) -> dict[str, Any]:
    return _artifact_or_404(request, session_id)


@router.post("/session/{session_id}/checkpoint/evaluate", dependencies=[Depends(require_portal_auth)])
def evaluate_session_checkpoints(session_id: str, request: Request) -> dict[str, Any]:
    artifact = _artifact_or_404(request, session_id)
    results = [result.as_dict() for result in evaluate_checkpoints(artifact, _guardrails(request))]
    # Store checkpoint results so later reports and alarm views use the same evaluation.
    for result in results:
        db.record_checkpoint_result(_database_path(request), session_id=session_id, checkpoint=result)
    return {"session_id": session_id, "checkpoint_results": results}


def _artifact_or_404(request: Request, session_id: str) -> dict[str, Any]:
    try:
        return db.build_session_artifact(_database_path(request), session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc


def _token_totals(artifact: dict[str, Any]) -> dict[str, int]:
    return {
        "prompt_tokens": sum(int(turn.get("prompt_tokens", 0)) for turn in artifact["token_log"]),
        "completion_tokens": sum(int(turn.get("completion_tokens", 0)) for turn in artifact["token_log"]),
        "total_tokens": sum(int(turn.get("total_tokens", 0)) for turn in artifact["token_log"]),
    }


def _tool_breakdown(artifact: dict[str, Any]) -> dict[str, dict[str, int]]:
    breakdown: dict[str, dict[str, int]] = {}
    for call in artifact["tool_trace"]:
        tool_name = call["tool_name"]
        breakdown.setdefault(tool_name, {"calls": 0})["calls"] += 1
    return breakdown


def _daily_cap_tokens(budget: dict[str, Any], config, database_path=None) -> int | None:
    if "daily_cap_tokens" in budget:
        return int(budget["daily_cap_tokens"])
    if database_path is not None:
        stored = db.get_token_budget_settings(database_path)
        if stored.get("daily_cap_tokens") is not None:
            return int(stored["daily_cap_tokens"])
    if config.daily_cap.enabled:
        return config.daily_cap.tokens
    return None


def _hash_key(session_api_key: str) -> str:
    return hashlib.sha256(session_api_key.encode("utf-8")).hexdigest()
