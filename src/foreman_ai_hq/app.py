from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from foreman_ai_hq import db, session_handoff, task_breakdown_handoff
from foreman_ai_hq.guardrails import load_guardrails
from foreman_ai_hq.llm import LLMClient
from foreman_ai_hq.execution_backend import LocalExecutionBackend
from foreman_ai_hq.routes import alarms, planning_conversation, portal, proxy, react_shell, sessions, tasks
from foreman_ai_hq.settings import Settings

@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    # Startup owns process-wide resources so tests can inject state before serving requests.
    db.init_db(settings.database_path)
    app.state.guardrails = load_guardrails(settings.guardrails_path)
    if not hasattr(app.state, "llm_client"):
        app.state.llm_client = LLMClient(settings)
    if settings.local_runner_enabled:
        app.state.execution_backend = LocalExecutionBackend(settings.database_path)
        # Touch the backend so startup fails early if the local runner cannot inspect its state.
        app.state.execution_backend.status()
    app.state.planning_registry = planning_conversation.PlanningConversationRegistry()
    yield
    app.state.planning_registry.close_all()


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Foreman AI HQ", lifespan=_lifespan)
    app.state.settings = settings or Settings()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(sessions.router)
    app.include_router(tasks.router)
    app.include_router(alarms.router)
    app.include_router(proxy.router)
    app.include_router(portal.router)
    app.include_router(react_shell.router)
    app.include_router(session_handoff.router)
    app.include_router(task_breakdown_handoff.router)
    app.include_router(planning_conversation.router)
    return app
