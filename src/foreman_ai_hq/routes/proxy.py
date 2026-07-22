from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from foreman_ai_hq import db
from foreman_ai_hq.alarms import detect_budget_alarms
from foreman_ai_hq.governance import GovernanceDecision, apply_governance
from foreman_ai_hq.guardrails import get_budget_zone
from foreman_ai_hq.llm import LLMClientError, extract_cost, extract_usage, resolve_cost, response_to_dict

router = APIRouter()


@router.post("/v1/chat/completions")
async def chat_completions(payload: dict[str, Any], request: Request):
    session = _session_from_auth(request)
    database_path = request.app.state.settings.database_path
    config = request.app.state.guardrails
    budget = session.get("guardrail_overrides", {}).get("budget", {})

    # Budget governance combines persisted daily spend with any per-session override.
    daily_used_before = int(budget.get("daily_used_tokens", 0)) + _current_day_budgeted_token_usage(request)
    zone = get_budget_zone(daily_used_before, _daily_cap_tokens(budget, config, database_path), config)
    decision = apply_governance(payload, zone, config)

    if decision.request.get("stream") is True:
        # Ask providers for usage in the stream tail so streamed turns can be logged.
        decision.request["stream_options"] = {"include_usage": True}
        try:
            stream = await request.app.state.llm_client.acompletion(decision.request)
        except LLMClientError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return StreamingResponse(
            _stream_chunks(stream, request, session, decision),
            media_type="text/event-stream",
        )

    try:
        llm_response = await request.app.state.llm_client.acompletion(decision.request)
    except LLMClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    response_body = response_to_dict(llm_response)
    usage = extract_usage(response_body)
    _persist_turn(request, session, decision, usage, response_body)
    _persist_budget_alarms(request, session, budget)
    return response_body


def _session_from_auth(request: Request) -> dict[str, Any]:
    authorization = request.headers.get("authorization", "")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="missing session bearer token")
    key_hash = hashlib.sha256(authorization[len(prefix) :].encode("utf-8")).hexdigest()
    try:
        session = db.get_session_by_key_hash(request.app.state.settings.database_path, key_hash)
    except KeyError as exc:
        raise HTTPException(status_code=401, detail="invalid session bearer token") from exc
    if session["status"] == "aborted":
        raise HTTPException(status_code=403, detail="session is aborted")
    return session


async def _stream_chunks(
    stream: AsyncIterator[Any],
    request: Request,
    session: dict[str, Any],
    decision: GovernanceDecision,
) -> AsyncIterator[str]:
    final_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    final_response: dict[str, Any] | None = None
    async for chunk in stream:
        chunk_body = response_to_dict(chunk)
        chunk_usage = extract_usage(chunk_body)
        if any(chunk_usage.values()):
            # Usage may arrive only in the final provider chunk; keep the last non-zero value.
            final_usage = chunk_usage
            final_response = chunk_body
        elif extract_cost(chunk_body) is not None:
            # A provider may emit the reported cost in a separate usage tail with no tokens.
            final_response = chunk_body
        yield f"data: {json.dumps(chunk_body, separators=(',', ':'))}\n\n"
    _persist_turn(request, session, decision, final_usage, final_response)
    _persist_budget_alarms(request, session, session.get("guardrail_overrides", {}).get("budget", {}))
    yield "data: [DONE]\n\n"


def _persist_turn(
    request: Request,
    session: dict[str, Any],
    decision: GovernanceDecision,
    usage: dict[str, int],
    response: dict[str, Any] | None,
) -> None:
    database_path = request.app.state.settings.database_path
    model = decision.request.get("model", session["model"])
    cost = resolve_cost(model, response or {"usage": usage})
    db.record_token_turn(
        database_path,
        session_id=session["id"],
        usage_kind=db.read_session_kind(session),
        model=model,
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
        cost=cost,
        raw_usage=usage,
    )
    db.record_guardrail_snapshot(
        database_path,
        session_id=session["id"],
        zone=decision.zone,
        decision={
            "zone": decision.zone,
            "blocked_tools": decision.blocked_tools,
            "max_tokens": decision.max_tokens,
        },
    )


def _persist_budget_alarms(request: Request, session: dict[str, Any], budget: dict[str, Any]) -> None:
    database_path = request.app.state.settings.database_path
    config = request.app.state.guardrails
    daily_used_tokens = int(budget.get("daily_used_tokens", 0)) + _current_day_budgeted_token_usage(request)
    session_used_tokens = db.session_token_breakdown(database_path, session["id"])["by_category"]["worker_execution"]
    daily_cap_tokens = _daily_cap_tokens(budget, config, database_path)
    zone = get_budget_zone(daily_used_tokens, daily_cap_tokens, config)
    previous_alarms = [
        {**alarm, "session_id": session["id"]}
        for alarm in db.build_session_artifact(database_path, session["id"])["alarms"]
    ]
    # Existing alarms are passed back in so detection can avoid duplicate noise.
    alarms = detect_budget_alarms(
        session_id=session["id"],
        zone=zone,
        daily_used_tokens=daily_used_tokens,
        daily_cap_tokens=daily_cap_tokens,
        session_used_tokens=session_used_tokens,
        session_cap_tokens=_session_cap_tokens(budget, config, database_path),
        previous_alarms=previous_alarms,
    )
    for alarm in alarms:
        db.record_alarm(database_path, session_id=session["id"], alarm=alarm.as_dict())


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


def _current_day_budgeted_token_usage(request: Request) -> int:
    database_path = request.app.state.settings.database_path
    return db.budgeted_token_usage(
        database_path,
        since=db.effective_daily_budget_window_start(
            database_path,
            timezone=request.app.state.settings.timezone,
        ),
    )


def _current_day_start_iso(timezone: str) -> str:
    return db.current_day_start_iso(timezone)


def _session_cap_tokens(budget: dict[str, Any], config, database_path=None) -> int | None:
    if "session_cap_tokens" in budget:
        return int(budget["session_cap_tokens"])
    if database_path is not None:
        stored = db.get_token_budget_settings(database_path)
        if stored.get("session_cap_tokens") is not None:
            return int(stored["session_cap_tokens"])
    if config.session_cap.enabled:
        return config.session_cap.tokens
    return None
