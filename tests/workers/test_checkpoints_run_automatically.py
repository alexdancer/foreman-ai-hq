from __future__ import annotations

import time
from pathlib import Path

from foreman_ai_hq import db
from foreman_ai_hq.guardrails import load_guardrails
from foreman_ai_hq.project_context import project_task_metadata
from foreman_ai_hq.task_kind import with_task_kind
from foreman_ai_hq.task_launch import launch_task
from tests.conftest import git_project_profile


def _wait_for_worker_run_status(db_path: Path, task_id: str, status: str):
    deadline = time.time() + 5
    while time.time() < deadline:
        runs = db.list_worker_runs(db_path, task_id=task_id)
        if runs and runs[-1]["status"] == status:
            return runs[-1]
        time.sleep(0.01)
    raise AssertionError(f"worker run did not reach status {status}")


def _make_runner(db_path: Path):
    def runner(plan):
        db.record_token_turn(
            db_path,
            session_id=plan.metadata["session_id"],
            usage_kind="task_execution",
            model="opencode/gpt-5.1",
            prompt_tokens=10,
            completion_tokens=5,
            cost=0,
            raw_usage={"total_tokens": 15},
        )
        return {"returncode": 0, "stdout": "done", "stderr": ""}

    return runner


def _ready_read_only_task(db_path: Path, tmp_path: Path):
    root = tmp_path / "checkpoints-project"
    profile = git_project_profile(root)
    project = db.upsert_connected_project(
        db_path,
        name="Checkpoint Project",
        root_path=str(root.resolve()),
        profile=profile,
        capability={"state": "launch_ready", "can_launch": True},
    )
    db.update_worker_adapter(
        db_path,
        "opencode",
        workdir=str(root),
        config={"launch_template": ["python", "-c", "print('worker')"]},
        supported_models=["opencode/gpt-5.1"],
        is_default=True,
    )
    db.mark_worker_adapter_verification(db_path, "opencode", verified=True, evidence={"ok": True})
    return db.create_task(
        db_path,
        description="Check checkpoints",
        status="Ready",
        estimate_tokens=1000,
        recommended_model="opencode/gpt-5.1",
        metadata=with_task_kind({**project_task_metadata(project)}, "acceptance_verification"),
    )


def test_completed_worker_run_has_checkpoint_results(tmp_path, monkeypatch):
    """2.1 A completed Worker Run has non-empty checkpoint_results with no operator action."""
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    task = _ready_read_only_task(db_path, tmp_path)

    launch_task(
        db_path,
        task["id"],
        adapter_id="opencode",
        model=None,
        proxy_url=None,
        runner=_make_runner(db_path),
        guardrail_config=load_guardrails("guardrails.yaml"),
    )
    worker_run = _wait_for_worker_run_status(db_path, task["id"], "completed")

    session = db.get_session(db_path, worker_run["session_id"])
    assert session["status"] == "completed"
    artifact = db.build_session_artifact(db_path, session["id"])
    assert artifact["checkpoint_results"]
    assert all(result["name"] for result in artifact["checkpoint_results"])
    assert {result["name"] for result in artifact["checkpoint_results"]} == {
        "budget_health",
        "stuck_loop_score",
        "tool_diversity",
        "timeout_respect",
    }


def test_checkpoint_evaluation_failure_leaves_worker_run_intact(tmp_path, monkeypatch):
    """2.2 An evaluation failure leaves the Worker Run completed with its other evidence intact."""
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    task = _ready_read_only_task(db_path, tmp_path)

    def _failing_eval(*args, **kwargs):
        raise RuntimeError("simulated checkpoint evaluator failure")

    monkeypatch.setattr("foreman_ai_hq.checkpoints.evaluate_checkpoints", _failing_eval)

    launch_task(
        db_path,
        task["id"],
        adapter_id="opencode",
        model=None,
        proxy_url=None,
        runner=_make_runner(db_path),
        guardrail_config=load_guardrails("guardrails.yaml"),
    )
    worker_run = _wait_for_worker_run_status(db_path, task["id"], "completed")

    session = db.get_session(db_path, worker_run["session_id"])
    assert session["status"] == "completed"
    artifact = db.build_session_artifact(db_path, session["id"])
    # Other run evidence is preserved.
    assert sum(int(turn.get("total_tokens", 0)) for turn in artifact["token_log"]) == 15
    # No checkpoint results were persisted because evaluation failed.
    assert artifact["checkpoint_results"] == []

    events = db.list_worker_run_events(db_path, worker_run_id=worker_run["id"])
    failure_events = [event for event in events if event["title"] == "Checkpoint evaluation failed"]
    assert len(failure_events) == 1
    assert failure_events[0]["level"] == "error"
    assert "simulated checkpoint evaluator failure" in str(failure_events[0]["detail"])
