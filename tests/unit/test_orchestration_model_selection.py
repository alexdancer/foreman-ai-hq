import asyncio
from types import SimpleNamespace

from foreman_ai_hq import db
from foreman_ai_hq.estimation import EstimatorError
from foreman_ai_hq.pi_adapter import PiStructuredJobError
from foreman_ai_hq.routes import planning_conversation, tasks
from foreman_ai_hq.settings import Settings
from foreman_ai_hq.task_breakdown import TaskBreakdownError
from tests.conftest import seed_orchestrator_inventory


class _Conversation:
    def __init__(self, session_id="sess-planning"):
        self.proc = SimpleNamespace(poll=lambda: None)
        self.session = {"id": session_id}
        self.closed = False

    def close(self):
        self.closed = True


def test_planning_registry_recreates_conversation_when_model_changes(tmp_path, monkeypatch):
    opened = []

    def open_conversation(_database_path, *, model, **_kwargs):
        conversation = _Conversation(f"sess-{len(opened) + 1}")
        opened.append((model, conversation))
        return conversation

    monkeypatch.setattr(planning_conversation, "open_pi_conversation", open_conversation)
    registry = planning_conversation.PlanningConversationRegistry()

    first = registry.start("project-1", tmp_path / "harness.db", "model-a", tmp_path)
    reused = registry.start("project-1", tmp_path / "harness.db", "model-a", tmp_path)
    replaced = registry.start("project-1", tmp_path / "harness.db", "model-b", tmp_path)

    assert (first, reused, replaced) == ("sess-1", "sess-1", "sess-2")
    assert [model for model, _conversation in opened] == ["model-a", "model-b"]
    assert opened[0][1].closed is True
    assert opened[1][1].closed is False


def test_divergent_legacy_models_never_select_an_orchestration_job(tmp_path, monkeypatch):
    database_path = tmp_path / "harness.db"
    model = "anthropic/claude-opus-5"
    settings = Settings(
        database_path=database_path,
        guardrails_path=tmp_path / "guardrails.yaml",
        orchestrator_model=model,
        operator_config={
            "orchestrator_model": model,
            "estimator_model": "openai/gpt-4.1-estimator",
            "task_breakdown_model": "openai/gpt-4.1-breakdown",
        },
    )
    db.init_db(database_path)
    seed_orchestrator_inventory(database_path, model=model)
    app = SimpleNamespace(state=SimpleNamespace(settings=settings, guardrails={}, orchestrator_job_runner=None))
    request = SimpleNamespace(app=app)
    observed: dict[str, str] = {}

    def open_conversation(_database_path, *, model, **_kwargs):
        observed["planning"] = model
        return _Conversation()

    async def intake_runner(_database_path, *, model, submit_tool, **_kwargs):
        observed[submit_tool] = model
        raise PiStructuredJobError("stop after recording selected model")

    async def estimate_source(*_args, estimator_model, **_kwargs):
        observed["estimation"] = estimator_model
        raise EstimatorError("stop after recording selected model")

    async def breakdown_source(*_args, task_breakdown_model, **_kwargs):
        observed["task_breakdown"] = task_breakdown_model
        raise TaskBreakdownError("stop after recording selected model")

    monkeypatch.setattr(planning_conversation, "open_pi_conversation", open_conversation)
    monkeypatch.setattr(tasks, "estimate_task", estimate_source)
    monkeypatch.setattr(tasks, "breakdown_task_source", breakdown_source)
    app.state.orchestrator_job_runner = intake_runner

    registry = planning_conversation.PlanningConversationRegistry()
    registry.start("project-1", database_path, settings.orchestrator_model, tmp_path)

    from foreman_ai_hq import intake

    try:
        asyncio.run(intake.run_intake_decision(request, "Size this work", {"intake_source": "plain_text"}))
    except PiStructuredJobError:
        pass
    asyncio.run(tasks._estimate_and_create_task(request, "Estimate this work"))
    asyncio.run(tasks._task_breakdown_agent_updates(request, "# Break down", {}, source_sha256="a" * 64))

    task = db.create_task(database_path, description="Review this work", status="Review")
    asyncio.run(tasks._run_agent_review(request, task, None))

    assert observed == {
        "planning": model,
        "submit_intake": model,
        "estimation": model,
        "task_breakdown": model,
        "submit_review": model,
    }
