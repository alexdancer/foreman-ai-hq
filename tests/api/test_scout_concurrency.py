from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from foreman_ai_hq import db
from foreman_ai_hq.app import create_app
from foreman_ai_hq.estimate_decision import create_scout_for_task
from foreman_ai_hq.guardrails import load_guardrails
from foreman_ai_hq.needs_you import low_confidence_item
from foreman_ai_hq.project_context import project_task_metadata
from foreman_ai_hq.routes import react_shell
from foreman_ai_hq.settings import Settings
from foreman_ai_hq.task_kind import read_task_kind
from tests.fake_orchestrator import FakeOrchestratorJobRunner


ROOT = Path(__file__).resolve().parents[2]


class FakeEstimatorLLM:
    def __init__(self, content=None, *, exc=None, delay=None):
        self.content = content or {
            "drivers": {
                "files_to_read": 2,
                "files_to_modify": 1,
                "expected_turns": 3,
                "needs_test_run": False,
            },
            "shadow_token_estimate": 11000,
            "complexity": "modest",
            "confidence": 0.82,
            "investigation_recommended": False,
            "rationale": "Synthetic estimate.",
            "assumptions": [],
            "risk_flags": [],
            "budget_note": "Within budget.",
            "source": "llm",
        }
        self.exc = exc
        self.delay = delay
        self.requests: list[dict] = []

    async def acompletion(self, request: dict) -> dict:
        self.requests.append(request)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.exc:
            raise self.exc
        return {
            "choices": [{"message": {"content": json.dumps(self.content)}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
        }


def _client(tmp_path: Path):
    settings = Settings(
        database_path=tmp_path / "harness.db",
        guardrails_path=ROOT / "guardrails.yaml",
    )
    db.init_db(settings.database_path)
    app = create_app(settings)
    project_root = tmp_path / "connected-project"
    project_root.mkdir(exist_ok=True)
    db.upsert_connected_project(
        settings.database_path,
        name=project_root.name,
        root_path=str(project_root.resolve()),
        profile={"name": project_root.name, "root_path": str(project_root.resolve()), "test_command": "pytest"},
        capability={"state": "launch_ready", "can_launch": True},
    )
    return TestClient(app)


def _configure_codex(db_path: Path):
    adapter = db.get_worker_adapter(db_path, "codex")
    config = dict(adapter.get("config") or {})
    config["allowed_models_configured"] = True
    db.update_worker_adapter(
        db_path,
        "codex",
        config=config,
        supported_models=["gpt-5.6-terra"],
        is_default=True,
    )
    db.mark_worker_adapter_verification(
        db_path,
        "codex",
        verified=True,
        evidence={"tracking_mode": "native_usage", "tracking_authoritative": True},
    )


def _request(client: TestClient, llm: FakeEstimatorLLM):
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                settings=client.app.state.settings,
                guardrails=load_guardrails(ROOT / "guardrails.yaml"),
                orchestrator_job_runner=FakeOrchestratorJobRunner(llm),
            )
        )
    )


def _low_confidence_task(db_path: Path, project: dict[str, object], *, task_id: str, confidence: float = 0.5):
    return db.create_task(
        db_path,
        task_id=task_id,
        description="DEMO low-confidence fixture",
        status="Estimated",
        estimate_tokens=1000,
        recommended_model="gpt-5.6-terra",
        metadata={
            "task_kind": "implementation",
            "confidence": confidence,
            "estimation_source": "llm",
            "estimate_revision": 1,
            "synthetic_fixture": True,
            **project_task_metadata(project),
        },
    )


@pytest.mark.asyncio
async def test_low_confidence_threshold_and_advisory(tmp_path):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    _configure_codex(db_path)
    project = db.list_connected_projects(db_path)[0]

    for confidence, expected in [(0.59, True), (0.60, False), (0.61, False)]:
        task = _low_confidence_task(db_path, project, task_id=f"task-{confidence}", confidence=confidence)
        item = low_confidence_item(project["id"], task, db_path)
        assert (item is not None) == expected
        if item:
            assert item["advisory"] is True
            assert item["task_kind"] == "implementation"
            assert item["decision_state"] == "decision_required"


def test_explicit_investigation_signal_surfaces_scout_path_at_high_confidence(tmp_path):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    project = db.list_connected_projects(db_path)[0]
    task = _low_confidence_task(db_path, project, task_id="task-investigate", confidence=0.9)
    db.update_task(
        db_path,
        task["id"],
        {"metadata": {**task["metadata"], "investigation_recommended": True}},
    )

    item = low_confidence_item(project["id"], db.get_task(db_path, task["id"]), db_path)

    assert item is not None
    assert item["title"] == "Investigation recommended"
    assert any(action["kind"] == "create_scout" for action in item["actions"])


@pytest.mark.asyncio
async def test_project_isolation_for_needs_you(tmp_path):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    _configure_codex(db_path)
    project_a = db.list_connected_projects(db_path)[0]

    other_root = tmp_path / "other-project"
    other_root.mkdir(exist_ok=True)
    project_b = db.upsert_connected_project(
        db_path,
        name="other-project",
        root_path=str(other_root.resolve()),
        profile={"name": "other-project", "root_path": str(other_root.resolve()), "test_command": "pytest"},
        capability={"state": "launch_ready", "can_launch": True},
    )

    task_a = _low_confidence_task(db_path, project_a, task_id="task-a")
    task_b = _low_confidence_task(db_path, project_b, task_id="task-b")

    needs_a = react_shell._needs_you_state(db_path, project_a["id"])
    needs_b = react_shell._needs_you_state(db_path, project_b["id"])

    assert any(i["task_id"] == task_a["id"] for i in needs_a["items"])
    assert not any(i["task_id"] == task_b["id"] for i in needs_a["items"])
    assert any(i["task_id"] == task_b["id"] for i in needs_b["items"])
    assert not any(i["task_id"] == task_a["id"] for i in needs_b["items"])


@pytest.mark.asyncio
async def test_concurrent_create_scout_creates_one_scout_and_one_estimator_call(tmp_path):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    _configure_codex(db_path)
    project = db.list_connected_projects(db_path)[0]
    task = _low_confidence_task(db_path, project, task_id="task-concurrent")

    llm = FakeEstimatorLLM(delay=0.05)
    request = _request(client, llm)

    async def call():
        return await create_scout_for_task(request, db_path, project["id"], task["id"], 1)

    results = await asyncio.gather(call(), call())
    assert results[0]["scout_task_id"] == results[1]["scout_task_id"]

    scouts = [t for t in db.list_tasks(db_path) if read_task_kind(t.get("metadata")) == "scout"]
    assert len(scouts) == 1
    assert len(llm.requests) == 1


@pytest.mark.asyncio
async def test_create_scout_idempotent_replay(tmp_path):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    _configure_codex(db_path)
    project = db.list_connected_projects(db_path)[0]
    task = _low_confidence_task(db_path, project, task_id="task-replay")

    llm = FakeEstimatorLLM()
    request = _request(client, llm)

    first = await create_scout_for_task(request, db_path, project["id"], task["id"], 1)
    second = await create_scout_for_task(request, db_path, project["id"], task["id"], 1)

    assert first["scout_task_id"] == second["scout_task_id"]
    assert first["decision_state"] == second["decision_state"] == "scout_pending"
    assert len(llm.requests) == 1

    scouts = [t for t in db.list_tasks(db_path) if read_task_kind(t.get("metadata")) == "scout"]
    assert len(scouts) == 1


@pytest.mark.asyncio
async def test_same_scout_estimation_failure_recovery(tmp_path):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    _configure_codex(db_path)
    project = db.list_connected_projects(db_path)[0]
    task = _low_confidence_task(db_path, project, task_id="task-fail")

    llm = FakeEstimatorLLM(exc=RuntimeError("estimator unavailable"))
    request = _request(client, llm)

    result = await create_scout_for_task(request, db_path, project["id"], task["id"], 1)
    scout = db.get_task(db_path, result["scout_task_id"])

    assert scout["status"] == "Pending"
    assert scout["metadata"]["estimation_state"] == "failed"
    assert scout["metadata"]["requires_manual_estimate"] is True
    assert scout["metadata"]["estimator_failure_type"] == "EstimatorUnavailableError"

    parent = db.get_task(db_path, task["id"])
    item = low_confidence_item(project["id"], parent, db_path)
    assert item is not None
    assert item["scout_task_id"] == scout["id"]
    assert any(a["kind"] == "view_scout" for a in item["actions"])


@pytest.mark.asyncio
async def test_needs_you_projection_bounds(tmp_path):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    _configure_codex(db_path)
    project = db.list_connected_projects(db_path)[0]
    task = _low_confidence_task(db_path, project, task_id="task-bounds")

    item = low_confidence_item(project["id"], task, db_path)
    assert item is not None
    assert len(item["id"]) <= 200
    assert len(item["title"]) <= 200
    assert len(item["reason"]) <= 1000
    assert item["confidence"] == pytest.approx(0.5)
    assert item["task_kind"] == "implementation"
    assert len(item["actions"]) == 3
    assert set(item) == {
        "id", "kind", "title", "reason", "created_at", "task_id", "task_kind",
        "advisory", "confidence", "decision_state", "scout_task_id", "session_href", "actions",
    }
    for action in item["actions"]:
        assert set(action) == {"kind", "label", "method", "href"}
        assert action["method"] in ("POST", "GET")
        assert action["href"].startswith("/")


def test_needs_you_fails_closed_for_unresolved_scout_link(tmp_path):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    project = db.list_connected_projects(db_path)[0]
    task = _low_confidence_task(db_path, project, task_id="task-missing-scout")
    db.update_task(
        db_path,
        task["id"],
        {"metadata": {**task["metadata"], "linked_scout_id": "other-project-scout"}},
    )

    item = low_confidence_item(project["id"], db.get_task(db_path, task["id"]), db_path)

    assert item["decision_state"] == "scout_unavailable"
    assert item["scout_task_id"] is None
    assert item["session_href"] is None
    assert [action["kind"] for action in item["actions"]] == [
        "acknowledge_estimate",
        "manual_estimate",
    ]


def test_stale_running_reestimate_projects_explicit_recovery_actions(tmp_path):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    project = db.list_connected_projects(db_path)[0]
    task = _low_confidence_task(db_path, project, task_id="task-stale-reestimate")
    session = db.create_session(
        db_path,
        task_description="stale re-estimate",
        model="gpt-5.6-terra",
        session_key_hash="stale-attempt",
        guardrail_overrides={},
    )
    pending = {
        "attempt_id": "attempt-stale",
        "state": "running",
        "started_at": "2000-01-01T00:00:00+00:00",
        "base_estimate_revision": 1,
        "session_id": session["id"],
    }
    db.update_task(
        db_path,
        task["id"],
        {"metadata": {**task["metadata"], "pending_reestimate": pending}},
    )

    item = low_confidence_item(project["id"], db.get_task(db_path, task["id"]), db_path)

    assert item["decision_state"] == "reestimate_failed"
    assert [action["kind"] for action in item["actions"]] == [
        "view_scout_report",
        "retry_reestimate",
        "dismiss_reestimate",
    ]
    assert item["actions"][1].keys() == {"kind", "label", "method", "href"}

    pending["started_at"] = datetime.now(UTC).isoformat()
    db.update_task(
        db_path,
        task["id"],
        {"metadata": {**task["metadata"], "pending_reestimate": pending}},
    )
    fresh = low_confidence_item(project["id"], db.get_task(db_path, task["id"]), db_path)
    assert fresh["decision_state"] == "reestimate_running"
    assert [action["kind"] for action in fresh["actions"]] == ["view_scout_report"]


def test_direct_task_routes_reject_invalid_kind_with_422(tmp_path):
    client = _client(tmp_path)
    created = client.post(
        "/tasks",
        json={"description": "valid task", "metadata": {"task_kind": "implementation"}},
    )
    assert created.status_code == 200

    invalid_create = client.post(
        "/tasks",
        json={"description": "invalid task", "metadata": {"task_kind": "research"}},
    )
    invalid_update = client.put(
        f"/tasks/{created.json()['id']}",
        json={"metadata": {"task_kind": "research"}},
    )

    assert invalid_create.status_code == 422
    assert invalid_update.status_code == 422
    assert all("task_kind must be one of" in response.json()["detail"] for response in (invalid_create, invalid_update))
    assert len(db.list_tasks(client.app.state.settings.database_path)) == 1


@pytest.mark.asyncio
async def test_create_scout_no_partial_write_on_invalid_revision(tmp_path):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    _configure_codex(db_path)
    project = db.list_connected_projects(db_path)[0]
    task = _low_confidence_task(db_path, project, task_id="task-stale")

    llm = FakeEstimatorLLM()
    request = _request(client, llm)

    with pytest.raises(HTTPException) as exc:
        await create_scout_for_task(request, db_path, project["id"], task["id"], 999)
    assert exc.value.status_code == 409

    parent = db.get_task(db_path, task["id"])
    assert parent["metadata"].get("linked_scout_id") is None
    assert parent["metadata"].get("low_confidence_decision") is None
    assert not any(read_task_kind(t.get("metadata")) == "scout" for t in db.list_tasks(db_path))
    assert len(llm.requests) == 0


@pytest.mark.asyncio
async def test_create_scout_rejects_nested_scout(tmp_path):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    _configure_codex(db_path)
    project = db.list_connected_projects(db_path)[0]
    scout_task = db.create_task(
        db_path,
        task_id="scout-parent",
        description="DEMO scout task",
        status="Estimated",
        estimate_tokens=1000,
        recommended_model="gpt-5.6-terra",
        metadata={
            "task_kind": "scout",
            "confidence": 0.5,
            "estimation_source": "llm",
            "estimate_revision": 1,
            **project_task_metadata(project),
        },
    )

    llm = FakeEstimatorLLM()
    request = _request(client, llm)

    with pytest.raises(HTTPException) as exc:
        await create_scout_for_task(request, db_path, project["id"], scout_task["id"], 1)
    assert exc.value.status_code == 422
    assert "nested" in exc.value.detail.lower()
