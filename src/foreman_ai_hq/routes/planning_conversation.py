from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from foreman_ai_hq import db
from foreman_ai_hq.auth import require_portal_auth
from foreman_ai_hq.orchestrator_gate import require_configured_orchestrator
from foreman_ai_hq.pi_adapter import (
    AcpRuntimeError,
    PiAuthRequired,
    PiConversation,
    open_pi_conversation,
)

router = APIRouter()

DEFAULT_PLANNING_TTL_SECONDS = 300.0
DEFAULT_PLANNING_MAX_CONVERSATIONS = 5


class PlanningMessageRequest(BaseModel):
    message: str = Field(min_length=1)


class PlanningConversationCapacityError(RuntimeError):
    """Raised when the bounded registry cannot make room for a new conversation."""


@dataclass
class LiveConversation:
    conv: PiConversation
    planning_session_id: str
    last_used_at: float


class PlanningConversationRegistry:
    """Bounded, thread-safe registry of held planning conversations keyed by project."""

    def __init__(
        self,
        ttl_seconds: float = DEFAULT_PLANNING_TTL_SECONDS,
        max_size: int = DEFAULT_PLANNING_MAX_CONVERSATIONS,
    ) -> None:
        self._ttl = ttl_seconds
        self._max = max_size
        self._lock = threading.RLock()
        self._live: dict[str, LiveConversation] = {}

    def _sweep(self, now: float) -> None:
        to_close: list[str] = []
        for project_id, live in list(self._live.items()):
            if live.conv.proc.poll() is not None or now - live.last_used_at > self._ttl:
                to_close.append(project_id)
        for project_id in to_close:
            self._live.pop(project_id, None).conv.close()

    def start(
        self,
        project_id: str,
        database_path: Path | str,
        model: str,
        cwd: Path | str,
        timeout: float = 60,
    ) -> str:
        """Return an existing live conversation's session id or open a new one."""
        now = time.monotonic()
        with self._lock:
            self._sweep(now)
            live = self._live.get(project_id)
            if live is not None and live.conv.proc.poll() is None:
                live.last_used_at = now
                return live.planning_session_id
            if live is not None:
                del self._live[project_id]
            if len(self._live) >= self._max:
                idle = [
                    (pid, item)
                    for pid, item in self._live.items()
                    if now - item.last_used_at > self._ttl
                ]
                if not idle:
                    raise PlanningConversationCapacityError(
                        "planning conversation capacity full"
                    )
                lru_pid = min(idle, key=lambda pair: pair[1].last_used_at)[0]
                self._live.pop(lru_pid).conv.close()
            conv = open_pi_conversation(
                database_path,
                model=model,
                cwd=cwd,
                timeout=timeout,
            )
            live = LiveConversation(
                conv=conv,
                planning_session_id=conv.session["id"],
                last_used_at=now,
            )
            self._live[project_id] = live
            return live.planning_session_id

    def get(self, project_id: str) -> LiveConversation:
        """Return the live conversation for a project, refreshing its last-used time."""
        now = time.monotonic()
        with self._lock:
            self._sweep(now)
            if project_id not in self._live:
                raise KeyError(f"no active planning conversation for project: {project_id}")
            live = self._live[project_id]
            live.last_used_at = now
            return live

    def touch(self, project_id: str) -> None:
        """Refresh the last-used timestamp for an active conversation."""
        now = time.monotonic()
        with self._lock:
            if project_id in self._live:
                self._live[project_id].last_used_at = now

    def end(self, project_id: str) -> None:
        """Close and remove a project's conversation."""
        with self._lock:
            live = self._live.pop(project_id, None)
            if live is None:
                raise KeyError(f"no active planning conversation for project: {project_id}")
            live.conv.close()

    def close_all(self) -> None:
        """Terminate every held conversation; used on app shutdown."""
        with self._lock:
            for live in self._live.values():
                live.conv.close()
            self._live.clear()


@router.post("/api/projects/{project_id}/planning/start", dependencies=[Depends(require_portal_auth), Depends(require_configured_orchestrator)])
def start_planning_conversation(project_id: str, request: Request) -> dict[str, Any]:
    database_path = request.app.state.settings.database_path
    try:
        project = db.get_connected_project(database_path, project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc
    registry: PlanningConversationRegistry = request.app.state.planning_registry
    try:
        session_id = registry.start(
            project_id,
            database_path,
            model=request.app.state.settings.orchestrator_model,
            cwd=project["root_path"],
        )
    except PiAuthRequired as exc:
        raise HTTPException(
            status_code=401,
            detail="Provider authentication required; run `pi /login` or add an API key in pi.",
        ) from exc
    except PlanningConversationCapacityError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"planning_session_id": session_id}


@router.post("/api/projects/{project_id}/planning/message", dependencies=[Depends(require_portal_auth), Depends(require_configured_orchestrator)])
def message_planning_conversation(
    project_id: str,
    payload: PlanningMessageRequest,
    request: Request,
) -> dict[str, Any]:
    database_path = request.app.state.settings.database_path
    registry: PlanningConversationRegistry = request.app.state.planning_registry
    try:
        live = registry.get(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="planning conversation not started") from exc
    try:
        text, stop_reason = live.conv.prompt(payload.message)
    except PiAuthRequired as exc:
        raise HTTPException(
            status_code=401,
            detail="Provider authentication required; run `pi /login` or add an API key in pi.",
        ) from exc
    except AcpRuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    registry.touch(project_id)
    db.record_planning_turn_event(
        database_path,
        session_id=live.planning_session_id,
        operator_message=payload.message,
        agent_response=text,
        stop_reason=stop_reason,
    )
    return {
        "planning_session_id": live.planning_session_id,
        "content": text,
        "stop_reason": stop_reason,
    }


@router.get("/api/projects/{project_id}/planning/events", dependencies=[Depends(require_portal_auth)])
def poll_planning_events(
    project_id: str,
    request: Request,
    since_id: int | None = Query(None, ge=0),
) -> dict[str, Any]:
    database_path = request.app.state.settings.database_path
    registry: PlanningConversationRegistry = request.app.state.planning_registry
    try:
        live = registry.get(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="planning conversation not started") from exc
    events = db.list_planning_turn_events(
        database_path,
        session_id=live.planning_session_id,
        since_id=since_id,
        limit=101,
    )
    has_more = len(events) > 100
    events = events[:100]
    next_since_id = events[-1]["id"] if events else since_id
    return {
        "planning_session_id": live.planning_session_id,
        "events": events,
        "next_since_id": next_since_id,
        "has_more": has_more,
    }


@router.post("/api/projects/{project_id}/planning/cancel", dependencies=[Depends(require_portal_auth)])
def cancel_planning_conversation(project_id: str, request: Request) -> dict[str, Any]:
    registry: PlanningConversationRegistry = request.app.state.planning_registry
    try:
        live = registry.get(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="planning conversation not started") from exc
    live.conv.cancel()
    return {"cancelled": True}


@router.post("/api/projects/{project_id}/planning/end", dependencies=[Depends(require_portal_auth)])
def end_planning_conversation(project_id: str, request: Request) -> dict[str, Any]:
    registry: PlanningConversationRegistry = request.app.state.planning_registry
    try:
        registry.end(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="planning conversation not started") from exc
    return {"ended": True}
