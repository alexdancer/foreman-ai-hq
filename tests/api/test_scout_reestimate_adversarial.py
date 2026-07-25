from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from foreman_ai_hq import db
from foreman_ai_hq.app import create_app
from foreman_ai_hq.estimate_decision import (
    apply_reestimate,
    dismiss_reestimate,
    request_scout_reestimate,
    retry_reestimate,
)
from foreman_ai_hq.estimation_calibration import build_calibration_selection
from foreman_ai_hq.guardrails import load_guardrails
from foreman_ai_hq.needs_you import _redact_findings_text, build_findings_excerpt
from foreman_ai_hq.project_context import project_task_metadata
from foreman_ai_hq.settings import Settings
from foreman_ai_hq.task_kind import read_task_kind
from tests.fake_orchestrator import FakeOrchestratorJobRunner


ROOT = Path(__file__).resolve().parents[2]


class FakeEstimatorLLM:
    def __init__(self, content=None, *, exc=None, delay=None):
        self.content = content or {
            "drivers": {
                "files_to_read": 1,
                "files_to_modify": 0,
                "expected_turns": 1,
                "needs_test_run": False,
            },
            "shadow_token_estimate": 9000,
            "complexity": "modest",
            "confidence": 0.85,
            "investigation_recommended": False,
            "rationale": "Scout findings reduce uncertainty.",
            "assumptions": ["Findings are representative."],
            "risk_flags": [],
            "budget_note": "Within budget.",
            "source": "scout_findings",
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


def _scout_fixture(db_path: Path, project: dict[str, object], *, status: str = "Review"):
    scout = db.create_task(
        db_path,
        task_id="scout-1",
        description="DEMO scout investigation",
        status=status,
        estimate_tokens=500,
        recommended_model="gpt-5.6-terra",
        metadata={
            "task_kind": "scout",
            "confidence": 0.82,
            "estimation_source": "llm",
            "estimate_revision": 1,
            **project_task_metadata(project),
        },
    )
    return scout


def _completed_run(db_path: Path, scout: dict[str, object], *, run_id: str, event_texts: list[str], completed_at: str | None = None):
    session = db.create_session(
        db_path,
        task_description=f"DEMO scout run {run_id}",
        model="gpt-5.6-terra",
        session_key_hash="deadbeef",
        guardrail_overrides={},
        status="completed",
    )
    run = db.create_worker_run(
        db_path,
        task_id=scout["id"],
        session_id=session["id"],
        adapter_id="codex",
        model="gpt-5.6-terra",
        tracking_mode="native_usage",
        command_plan={"command": ["codex"], "cwd": "/tmp", "metadata": {}},
        metadata={"run_id": run_id},
    )
    for text in event_texts:
        db.record_worker_run_event(
            db_path,
            worker_run_id=run["id"],
            session_id=session["id"],
            task_id=scout["id"],
            kind="agent_message",
            title="Scout finding",
            layer="worker_harness",
            detail={"text": text},
        )
    db.mark_worker_run_completed(
        db_path,
        run["id"],
        returncode=0,
        stdout='',
        stderr='',
        metadata={"completed_at": completed_at or "2099-01-01T00:00:00Z"},
    )
    return run


def _parent_task(db_path: Path, project: dict[str, object]):
    return db.create_task(
        db_path,
        task_id="parent-1",
        description="DEMO parent task",
        status="Estimated",
        estimate_tokens=1000,
        recommended_model="gpt-5.6-terra",
        metadata={
            "task_kind": "implementation",
            "confidence": 0.5,
            "estimation_source": "llm",
            "estimate_revision": 1,
            "linked_scout_id": "scout-1",
            **project_task_metadata(project),
        },
    )


def _seed_scout_with_findings(tmp_path, event_texts: list[str], run_id: str = "run-1"):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    _configure_codex(db_path)
    project = db.list_connected_projects(db_path)[0]
    scout = _scout_fixture(db_path, project)
    run = _completed_run(db_path, scout, run_id=run_id, event_texts=event_texts)
    return db_path, project, scout, client, run


def test_build_findings_excerpt_ignores_malformed_and_non_allowlisted_events(tmp_path):
    db_path, project, scout, _, run = _seed_scout_with_findings(
        tmp_path,
        [
            "valid finding one",
            "",
            "   ",
        ],
        run_id="run-malformed",
    )
    for malformed in [
        {"kind": "agent_message", "layer": "worker_harness", "detail": "not a dict"},
        {"kind": "agent_message", "layer": "worker_harness", "detail": {"text": 12345}},
        {"kind": "system", "layer": "worker_harness", "detail": {"text": "system noise"}},
        {"kind": "agent_message", "layer": "control_plane", "detail": {"text": "control plane noise"}},
        {"kind": "not-a-dict"},
    ]:
        db.record_worker_run_event(
            db_path,
            worker_run_id=run["id"],
            session_id=run["session_id"],
            task_id=scout["id"],
            kind=str(malformed.get("kind", "unknown")),
            title="event",
            layer=str(malformed.get("layer", "control_plane")),
            detail=malformed.get("detail") or {},
        )

    excerpt = build_findings_excerpt(db_path, scout, project)
    assert excerpt["findings"] == ["valid finding one"]
    assert excerpt["truncated"] is False


def test_build_findings_excerpt_bounds_length_and_item_count(tmp_path):
    long_item = "x" * 2100
    many_short = [f"finding-{i}" for i in range(8)]
    db_path, project, scout, _, _ = _seed_scout_with_findings(
        tmp_path,
        [long_item] + many_short,
        run_id="run-bounds",
    )

    excerpt = build_findings_excerpt(db_path, scout, project)
    assert len(excerpt["findings"]) == 6
    assert len(excerpt["findings"][0].encode("utf-8")) <= 2000
    assert excerpt["truncated"] is True

    aggregate = sum(len(f.encode("utf-8")) for f in excerpt["findings"])
    assert aggregate <= 12_000


def test_build_findings_excerpt_redacts_secrets_and_paths(tmp_path):
    home = str(Path.home())
    project_root = str(tmp_path / "connected-project")
    secret_text = (
        f"Looked at {home}/.env and {project_root}/src/demo.py. "
        "Bearer abc.def.ghj API key sk-abc123OPENAI. "
        "Authorization: Basic abc=="
    )
    db_path, project, scout, _, _ = _seed_scout_with_findings(tmp_path, [secret_text], run_id="run-redact")
    project["root_path"] = project_root

    excerpt = build_findings_excerpt(db_path, scout, project)
    assert len(excerpt["findings"]) == 1
    redacted = excerpt["findings"][0]
    assert "<home>" in redacted
    assert "<project-root>" in redacted
    assert "sk-abc123" not in redacted
    assert "Bearer" not in redacted or "***REDACTED***" in redacted


def test_findings_path_replacement_happens_before_item_truncation(tmp_path):
    project_root = str(tmp_path / "connected-project")
    text = "x" * 1980 + project_root + "/secret.py"

    redacted = _redact_findings_text(text, {"root_path": project_root})

    assert "<project-root>" in redacted
    assert project_root not in redacted
    assert len(redacted) <= 2000


def test_build_findings_excerpt_uses_only_latest_completed_worker_run(tmp_path):
    db_path, project, scout, _, _ = _seed_scout_with_findings(tmp_path, ["second run finding"], run_id="run-2")
    _completed_run(db_path, scout, run_id="run-1", event_texts=["first run finding"], completed_at="2099-01-01T00:00:00Z")
    _completed_run(db_path, scout, run_id="run-2", event_texts=["second run finding"], completed_at="2099-01-02T00:00:00Z")

    excerpt = build_findings_excerpt(db_path, scout, project)
    assert len(excerpt["findings"]) == 1
    assert excerpt["findings"][0] == "second run finding"


@pytest.mark.asyncio
async def test_concurrent_request_reestimate_races_to_one_attempt(tmp_path):
    db_path, project, scout, client, _ = _seed_scout_with_findings(tmp_path, ["finding"], run_id="run-race")
    _configure_codex(db_path)
    parent = _parent_task(db_path, project)
    llm = FakeEstimatorLLM(delay=0.05)
    request = _request(client, llm)
    sessions_before = len(db.list_sessions(db_path, kind=None))

    async def call():
        try:
            return await request_scout_reestimate(request, db_path, project["id"], parent["id"], 1)
        except HTTPException as exc:
            return {"error": exc.status_code, "detail": exc.detail}

    results = await asyncio.gather(call(), call())
    states = [r.get("decision_state") for r in results if "decision_state" in r]
    errors = [r for r in results if "error" in r]

    assert "reestimate_ready" in states
    assert len(errors) == 1
    assert errors[0]["error"] == 409
    assert "re-estimation already" in errors[0]["detail"]

    parent = db.get_task(db_path, parent["id"])
    pending = parent["metadata"].get("pending_reestimate")
    assert pending is not None
    assert pending["state"] in ("ready", "running")
    assert "started_at" in pending
    assert len(db.list_sessions(db_path, kind=None)) == sessions_before + 1


@pytest.mark.asyncio
async def test_request_reestimate_records_estimation_token_turn(tmp_path):
    db_path, project, scout, client, _ = _seed_scout_with_findings(tmp_path, ["finding"], run_id="run-tokens")
    _configure_codex(db_path)
    parent = _parent_task(db_path, project)
    llm = FakeEstimatorLLM()
    request = _request(client, llm)

    await request_scout_reestimate(request, db_path, project["id"], parent["id"], 1)

    pending = db.get_task(db_path, parent["id"])["metadata"]["pending_reestimate"]
    session_id = pending["session_id"]
    artifact = db.build_session_artifact(db_path, session_id)
    assert len(artifact["token_log"]) == 1
    assert artifact["token_log"][0]["usage_kind"] == "estimation"
    assert artifact["token_log"][0]["raw_usage"]["spend_category"] == "control_plane"
    assert artifact["token_log"][0]["raw_usage"]["usage_source"] == "native_usage"
    assert artifact["token_log"][0]["total_tokens"] == 70


@pytest.mark.asyncio
async def test_retry_reestimate_requires_duplicate_spend_acknowledgement(tmp_path):
    db_path, project, scout, client, _ = _seed_scout_with_findings(tmp_path, ["finding"], run_id="run-retry")
    _configure_codex(db_path)
    parent = _parent_task(db_path, project)

    retry_session = db.create_session(
        db_path,
        task_description="Retry re-estimate session",
        model="gpt-5.6-terra",
        session_key_hash="retry-deadbeef",
        guardrail_overrides={},
        status="completed",
    )
    pending = {
        "attempt_id": "attempt-1",
        "state": "failed",
        "base_estimate_revision": 1,
        "scout_task_id": scout["id"],
        "session_id": retry_session["id"],
        "worker_run_id": "run-retry",
        "findings": ["finding"],
        "truncated": False,
    }
    db.update_task(db_path, parent["id"], {"metadata": {**parent["metadata"], "pending_reestimate": pending}})

    llm = FakeEstimatorLLM()
    request = _request(client, llm)

    with pytest.raises(HTTPException) as exc:
        await retry_reestimate(request, db_path, project["id"], parent["id"], 1, "attempt-1", acknowledge_duplicate_spend=False)
    assert exc.value.status_code == 422

    result = await retry_reestimate(request, db_path, project["id"], parent["id"], 1, "attempt-1", acknowledge_duplicate_spend=True)
    assert result["decision_state"] == "reestimate_ready"

    with pytest.raises(HTTPException) as exc:
        await retry_reestimate(request, db_path, project["id"], parent["id"], 1, "wrong-attempt", acknowledge_duplicate_spend=True)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_retry_reestimate_fails_closed_before_spend_when_findings_are_empty(tmp_path):
    db_path, project, scout, client, _ = _seed_scout_with_findings(tmp_path, [], run_id="run-empty")
    parent = _parent_task(db_path, project)
    pending = {
        "attempt_id": "attempt-empty",
        "state": "failed",
        "base_estimate_revision": 1,
        "scout_task_id": scout["id"],
    }
    db.update_task(
        db_path,
        parent["id"],
        {"metadata": {**parent["metadata"], "pending_reestimate": pending}},
    )
    llm = FakeEstimatorLLM()

    with pytest.raises(HTTPException) as exc:
        await retry_reestimate(
            _request(client, llm), db_path, project["id"], parent["id"], 1,
            "attempt-empty", acknowledge_duplicate_spend=True,
        )

    assert exc.value.status_code == 422
    assert llm.requests == []
    assert db.get_task(db_path, parent["id"])["metadata"]["pending_reestimate"]["state"] == "failed"


def test_apply_reestimate_rejects_stale_or_mismatched_state(tmp_path):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    _configure_codex(db_path)
    project = db.list_connected_projects(db_path)[0]
    parent = _parent_task(db_path, project)

    # No pending
    with pytest.raises(HTTPException) as exc:
        apply_reestimate(db_path, project["id"], parent["id"], 1, "attempt-1")
    assert exc.value.status_code == 409


def test_apply_reestimate_rejects_stale_query_revision(tmp_path):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    _configure_codex(db_path)
    project = db.list_connected_projects(db_path)[0]
    parent = _parent_task(db_path, project)
    db.update_task(
        db_path,
        parent["id"],
        {"metadata": {**parent["metadata"], "pending_reestimate": {
            "attempt_id": "attempt-1",
            "state": "ready",
            "base_estimate_revision": 1,
            "result": _reestimate_result(),
        }}},
    )

    with pytest.raises(HTTPException) as exc:
        apply_reestimate(db_path, project["id"], parent["id"], 999, "attempt-1")

    assert exc.value.status_code == 409
    assert db.get_task(db_path, parent["id"])["estimate_tokens"] == 1000

    # Pending but not ready
    db.update_task(
        db_path,
        parent["id"],
        {"metadata": {**parent["metadata"], "pending_reestimate": {"attempt_id": "attempt-1", "state": "running", "base_estimate_revision": 1, "result": {}}}},
    )
    with pytest.raises(HTTPException) as exc:
        apply_reestimate(db_path, project["id"], parent["id"], 1, "attempt-1")
    assert exc.value.status_code == 409

    # Ready but attempt id mismatch
    db.update_task(
        db_path,
        parent["id"],
        {
            "metadata": {
                **parent["metadata"],
                "pending_reestimate": {
                    "attempt_id": "attempt-1",
                    "state": "ready",
                    "base_estimate_revision": 1,
                    "result": _reestimate_result(),
                },
            }
        },
    )
    with pytest.raises(HTTPException) as exc:
        apply_reestimate(db_path, project["id"], parent["id"], 1, "attempt-2")
    assert exc.value.status_code == 409

    # Ready but estimate revision changed
    db.update_task(db_path, parent["id"], {"estimate_tokens": 2000, "metadata": {**parent["metadata"], "estimate_revision": 2}})
    with pytest.raises(HTTPException) as exc:
        apply_reestimate(db_path, project["id"], parent["id"], 1, "attempt-1")
    assert exc.value.status_code == 409


def test_dismiss_reestimate_clears_pending_and_rejects_further_apply(tmp_path):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    _configure_codex(db_path)
    project = db.list_connected_projects(db_path)[0]
    parent = _parent_task(db_path, project)

    db.update_task(
        db_path,
        parent["id"],
        {
            "metadata": {
                **parent["metadata"],
                "pending_reestimate": {
                    "attempt_id": "attempt-1",
                    "state": "ready",
                    "base_estimate_revision": 1,
                    "result": _reestimate_result(),
                },
            }
        },
    )

    result = dismiss_reestimate(db_path, project["id"], parent["id"], 1, "attempt-1")
    assert result["decision_state"] == "resolved"

    parent = db.get_task(db_path, parent["id"])
    assert parent["metadata"].get("pending_reestimate") is None
    assert parent["metadata"]["last_dismissed_reestimate"] == {
        "attempt_id": "attempt-1",
        "state": "ready",
        "base_estimate_revision": 1,
        "scout_task_id": None,
        "dismissed_at": parent["metadata"]["last_dismissed_reestimate"]["dismissed_at"],
    }

    with pytest.raises(HTTPException) as exc:
        apply_reestimate(db_path, project["id"], parent["id"], 1, "attempt-1")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_no_silent_rewrite_on_apply_with_disallowed_model(tmp_path):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    _configure_codex(db_path)
    project = db.list_connected_projects(db_path)[0]
    parent = _parent_task(db_path, project)

    result = _reestimate_result()
    result["recommended_model"] = "disallowed/model"
    db.update_task(
        db_path,
        parent["id"],
        {
            "metadata": {
                **parent["metadata"],
                "pending_reestimate": {
                    "attempt_id": "attempt-1",
                    "state": "ready",
                    "base_estimate_revision": 1,
                    "result": result,
                },
            }
        },
    )

    with pytest.raises(HTTPException) as exc:
        apply_reestimate(db_path, project["id"], parent["id"], 1, "attempt-1")
    assert exc.value.status_code == 409

    parent = db.get_task(db_path, parent["id"])
    assert parent["estimate_tokens"] == 1000
    assert parent["metadata"].get("estimate_revision") == 1


def test_estimation_accuracy_excludes_scout_tasks(tmp_path):
    client = _client(tmp_path)
    db_path = client.app.state.settings.database_path
    project = db.list_connected_projects(db_path)[0]

    db.create_task(
        db_path,
        task_id="impl-done",
        description="implementation done",
        status="Done",
        estimate_tokens=100,
        actual_tokens=120,
        recommended_model="gpt-5.6-terra",
        metadata={"task_kind": "implementation", "confidence": 0.8, "estimation_source": "llm"},
    )
    db.create_task(
        db_path,
        task_id="scout-done",
        description="scout done",
        status="Done",
        estimate_tokens=100,
        actual_tokens=300,
        recommended_model="gpt-5.6-terra",
        metadata={"task_kind": "scout", "confidence": 0.8, "estimation_source": "llm"},
    )

    accuracy = db.estimation_accuracy(db_path)
    assert accuracy["completed_count"] == 1
    assert accuracy["median_error_ratio"] == pytest.approx(1.2)


def test_calibration_selection_excludes_scout_cases_from_implementation(tmp_path):
    project_root = tmp_path / "cal-project"
    catalog_dir = project_root / ".foreman"
    catalog_dir.mkdir(parents=True)
    catalog_dir.joinpath("estimation_calibration.yaml").write_text(
        "cases:\n"
        "  - id: impl-1\n"
        "    task_description: Add endpoint\n"
        "    complexity: modest\n"
        "    task_kind: implementation\n"
        "    recommended_model: gpt-5.6-terra\n"
        "    rationale: base case\n"
        "    expected_tokens_min: 100\n"
        "    expected_tokens_max: 200\n"
        "    project_profile: {}\n"
        "  - id: scout-1\n"
        "    task_description: Investigate config\n"
        "    complexity: modest\n"
        "    task_kind: scout\n"
        "    recommended_model: gpt-5.6-terra\n"
        "    rationale: scout case\n"
        "    expected_tokens_min: 50\n"
        "    expected_tokens_max: 150\n"
        "    project_profile: {}\n"
    )

    impl_selection = build_calibration_selection(
        task_description="Add endpoint",
        project_root=str(project_root),
        task_kind="implementation",
    )
    assert all(case.task_kind == "implementation" for case in impl_selection.cases)
    assert not any(case.task_kind == "scout" for case in impl_selection.cases)

    scout_selection = build_calibration_selection(
        task_description="Investigate config",
        project_root=str(project_root),
        task_kind="scout",
    )
    assert all(case.task_kind == "scout" for case in scout_selection.cases)
    assert not any(case.task_kind == "implementation" for case in scout_selection.cases)


def _reestimate_result():
    return {
        "token_estimate": 1500,
        "complexity": "modest",
        "confidence": 0.85,
        "rationale": "Better now.",
        "assumptions": [],
        "risk_flags": [],
        "budget_note": "OK.",
        "source": "scout_findings",
        "drivers": {"files_to_read": 1, "files_to_modify": 0, "expected_turns": 1, "needs_test_run": False},
        "shadow_token_estimate": 1400,
        "estimate_disagreement": 0.0,
        "coefficient_provenance": {},
        "recommended_model": "gpt-5.6-terra",
    }
