from __future__ import annotations

from datetime import UTC, datetime
import json
import threading
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from foreman_ai_hq import db
from foreman_ai_hq.project_context import project_task_metadata
from foreman_ai_hq.routes.tasks import _current_day_start_iso as _portal_launch_day_start_iso
from foreman_ai_hq.task_launch import TaskLaunchBlocked, abort_worker_session, launch_task
from tests.conftest import git_project_profile


def _connect_project(db_path: Path, root: Path) -> dict:
    return db.upsert_connected_project(
        db_path,
        name=root.name,
        root_path=str(root.resolve()),
        profile=git_project_profile(root),
        capability={"state": "launch_ready", "can_launch": True},
    )


def _verified_budget_task(db_path: Path, tmp_path: Path, *, estimate: int = 50, budget: dict | None = None):
    db.init_db(db_path)
    project = _connect_project(db_path, tmp_path)
    db.update_worker_adapter(
        db_path,
        "opencode",
        workdir=str(tmp_path),
        config={"launch_template": ["python", "-c", "print('worker')"]},
        supported_models=["opencode/gpt-5.1"],
        is_default=True,
    )
    db.mark_worker_adapter_verification(db_path, "opencode", verified=True, evidence={"ok": True})
    return db.create_task(
        db_path,
        description="Budgeted launch",
        status="Estimated",
        estimate_tokens=estimate,
        recommended_model="opencode/gpt-5.1",
        metadata={
            **project_task_metadata(project),
            "budget": budget or {"daily_used_tokens": 0, "daily_cap_tokens": 100, "session_cap_tokens": 100},
        },
    )


def _wait_for_worker_run(db_path: Path, task_id: str, status: str | None = None):
    deadline = time.time() + 2
    while time.time() < deadline:
        runs = db.list_worker_runs(db_path, task_id=task_id)
        if runs and (status is None or runs[-1]["status"] == status):
            return runs[-1]
        time.sleep(0.01)
    raise AssertionError("worker run did not reach expected status")


def _write_worker_change(plan) -> None:
    (Path(plan.cwd) / "worker_change.txt").write_text(f"changed by {plan.metadata['session_id']}\n")


def _runner_recording(db_path: Path, *, total_tokens: int = 10):
    def runner(plan):
        # A write-capable Worker that changes nothing is a failure, so the recording
        # runner leaves a change behind the way a real one does.
        _write_worker_change(plan)
        db.record_token_turn(
            db_path,
            session_id=plan.metadata["session_id"],
            usage_kind="task_execution",
            model="opencode/gpt-5.1",
            prompt_tokens=total_tokens,
            completion_tokens=0,
            cost=0,
            raw_usage={"total_tokens": total_tokens},
        )
        return {"returncode": 0, "stdout": "done", "stderr": ""}

    return runner


def test_launch_blocks_when_no_project_is_connected(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "opencode",
        config={"launch_template": ["python", "-c", "print('worker')"]},
        supported_models=["opencode/gpt-5.1"],
        is_default=True,
    )
    db.mark_worker_adapter_verification(db_path, "opencode", verified=True, evidence={"ok": True})
    task = db.create_task(
        db_path,
        description="Needs connected project",
        status="Estimated",
        estimate_tokens=50,
        recommended_model="opencode/gpt-5.1",
    )

    try:
        launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=lambda plan: None)
    except TaskLaunchBlocked as exc:
        blocked = exc.task
    else:
        raise AssertionError("launch succeeded without a connected project")

    assert blocked["status"] == "Estimated"
    assert blocked["metadata"]["launch_guardrail_reasons"] == [
        "Task is not bound to a connected project. Recreate it from a project board before launch."
    ]


def test_read_only_launch_blocks_metadata_project_when_no_project_is_connected(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "opencode",
        config={"launch_template": ["python", "-c", "print('worker')"]},
        supported_models=["opencode/gpt-5.1"],
        is_default=True,
    )
    db.mark_worker_adapter_verification(db_path, "opencode", verified=True, evidence={"ok": True})
    task = db.create_task(
        db_path,
        description="Read-only needs connected project",
        status="Estimated",
        estimate_tokens=50,
        recommended_model="opencode/gpt-5.1",
        metadata={"launch_mode": "read_only", "project_root_path": str(tmp_path / "stale-project")},
    )

    try:
        launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=lambda plan: None)
    except TaskLaunchBlocked as exc:
        blocked = exc.task
    else:
        raise AssertionError("launch succeeded without a connected project")

    assert blocked["status"] == "Estimated"
    assert blocked["metadata"]["launch_guardrail_reasons"] == [
        "Task is not bound to a connected project. Recreate it from a project board before launch."
    ]


def test_estimate_within_budget_launches(tmp_path):
    db_path = tmp_path / "harness.db"
    task = _verified_budget_task(db_path, tmp_path, estimate=50, budget={"daily_used_tokens": 25, "daily_cap_tokens": 100})

    result = launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=_runner_recording(db_path))

    assert result.task["status"] == "Running"
    assert result.task["metadata"]["budget_check"]["passed"] is True


def test_successful_worker_run_records_actual_worker_execution_tokens(tmp_path):
    db_path = tmp_path / "harness.db"
    task = _verified_budget_task(db_path, tmp_path, estimate=100, budget={"daily_used_tokens": 0, "daily_cap_tokens": 500})

    launch_task(
        db_path,
        task["id"],
        adapter_id="opencode",
        model=None,
        proxy_url=None,
        runner=_runner_recording(db_path, total_tokens=77),
    )
    _wait_for_worker_run(db_path, task["id"], "completed")
    completed = db.get_task(db_path, task["id"])

    assert completed["status"] == "Review"
    assert completed["actual_tokens"] == 77


def test_native_worker_actuals_and_budget_exclude_cache_read_but_count_cache_write(tmp_path):
    db_path = tmp_path / "harness.db"
    task = _verified_budget_task(db_path, tmp_path, estimate=100, budget={"daily_used_tokens": 0, "daily_cap_tokens": 500})

    def runner(plan):
        _write_worker_change(plan)
        db.record_token_turn(
            db_path,
            session_id=plan.metadata["session_id"],
            usage_kind="task_execution",
            model="opencode/gpt-5.1",
            prompt_tokens=120,
            completion_tokens=40,
            cost=0,
            raw_usage={
                "input_tokens": 50,
                "cache_read_input_tokens": 70,
                "cache_creation_input_tokens": 30,
                "output_tokens": 40,
                "total_tokens": 190,
            },
        )
        return {"returncode": 0, "stdout": "done", "stderr": ""}

    launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)
    _wait_for_worker_run(db_path, task["id"], "completed")
    completed = db.get_task(db_path, task["id"])

    assert completed["status"] == "Review"
    assert completed["actual_tokens"] == 120
    assert db.budgeted_token_usage(db_path) == 120
    breakdown = db.token_usage_breakdown(db_path)
    assert breakdown["total_tokens"] == 120
    assert breakdown["by_category"]["worker_execution"] == 120


def test_launch_rejects_task_from_different_project_board(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    first = _connect_project(db_path, first_root)
    second = _connect_project(db_path, second_root)
    db.update_worker_adapter(
        db_path,
        "opencode",
        workdir=str(first_root),
        config={"launch_template": ["python", "-c", "print('worker')"]},
        supported_models=["opencode/gpt-5.1"],
        is_default=True,
    )
    db.mark_worker_adapter_verification(db_path, "opencode", verified=True, evidence={"ok": True})
    task = db.create_task(
        db_path,
        description="Project-bound launch",
        status="Estimated",
        estimate_tokens=50,
        recommended_model="opencode/gpt-5.1",
        metadata={**project_task_metadata(first), "budget": {"daily_used_tokens": 0, "daily_cap_tokens": 100}},
    )

    try:
        launch_task(
            db_path,
            task["id"],
            adapter_id="opencode",
            model=None,
            proxy_url=None,
            project_id=second["id"],
            runner=lambda plan: None,
        )
    except TaskLaunchBlocked as exc:
        blocked = exc.task
    else:
        raise AssertionError("launch succeeded from the wrong project board")

    assert blocked["metadata"]["launch_guardrail_reasons"] == [
        "Task is not bound to the selected project board."
    ]
    assert db.list_worker_runs(db_path, task_id=task["id"]) == []


def test_launch_injects_repo_context_brief_and_records_timeline_events(tmp_path):
    db_path = tmp_path / "harness.db"
    (tmp_path / "AGENTS.md").write_text(
        "Use pytest and keep changes small. password=plainpass Authorization: Bearer auth-token-123 sk_live_example",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    task = _verified_budget_task(db_path, tmp_path, estimate=50, budget={"daily_used_tokens": 0, "daily_cap_tokens": 100})

    db.update_worker_adapter(
        db_path,
        "opencode",
        config={"launch_template": ["opencode", "run", "--model", "{model}", "--format", "json", "{prompt}"]},
    )
    calls = []

    def runner(plan):
        calls.append(plan)
        _write_worker_change(plan)
        db.record_token_turn(
            db_path,
            session_id=plan.metadata["session_id"],
            usage_kind="task_execution",
            model="opencode/gpt-5.1",
            prompt_tokens=10,
            completion_tokens=0,
            cost=0,
            raw_usage={"total_tokens": 10},
        )
        return {"returncode": 0, "stdout": "done", "stderr": ""}

    result = launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)
    completed_run = _wait_for_worker_run(db_path, task["id"], "completed")
    events = db.list_worker_run_events(db_path, worker_run_id=completed_run["id"])

    assert calls[0].command[-1].startswith("Repo Context Brief")
    assert "Task instructions:\nBudgeted launch" in calls[0].command[-1]
    assert "AGENTS.md" in calls[0].command[-1]
    assert "pytest" in calls[0].command[-1]
    assert "plainpass" not in calls[0].command[-1]
    assert "auth-token-123" not in calls[0].command[-1]
    assert "plainpass" not in completed_run["metadata"]["repo_context_brief"]["text"]
    assert "auth-token-123" not in completed_run["metadata"]["repo_context_brief"]["text"]
    assert [event["kind"] for event in events][:4] == ["launch", "guardrail", "context", "command"]
    assert any(event["kind"] == "token" and event["detail"]["total_tokens"] == 10 for event in events)
    assert any(event["kind"] == "file" and event["title"] == "Workdir evidence captured" for event in events)

    assert events[-1]["title"] == "Worker Run completed"
    assert result.worker_run is not None
    assert result.worker_run["metadata"]["repo_context_brief"]["manifests"] == ["pyproject.toml"]


def test_default_adapter_selection_skips_observed_only_adapter(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    project = _connect_project(db_path, tmp_path)
    db.update_worker_adapter(
        db_path,
        "opencode",
        workdir=str(tmp_path),
        config={"command": "opencode"},
        supported_models=["opencode/gpt-5.1"],
        is_default=True,
    )
    db.mark_worker_adapter_verification(
        db_path,
        "opencode",
        verified=True,
        evidence={"tracking_mode": "observed_only", "tracking_authoritative": False},
    )
    db.update_worker_adapter(
        db_path,
        "codex",
        workdir=str(tmp_path),
        config={"launch_template": ["codex", "--model", "{model}"]},
        supported_models=["gpt-5.6-terra"],
    )
    db.mark_worker_adapter_verification(db_path, "codex", verified=True, evidence={"ok": True})
    task = db.create_task(
        db_path,
        description="Use launchable default fallback",
        status="Estimated",
        estimate_tokens=50,
        recommended_model="gpt-5.6-terra",
        metadata={**project_task_metadata(project), "budget": {"daily_used_tokens": 0, "daily_cap_tokens": 100}},
    )

    result = launch_task(db_path, task["id"], adapter_id=None, model=None, proxy_url=None, runner=_runner_recording(db_path))
    _wait_for_worker_run(db_path, task["id"], "completed")

    assert result.task["metadata"]["launch_adapter_id"] == "codex"


def test_standard_proxy_launch_fails_without_worker_usage_evidence(tmp_path):
    db_path = tmp_path / "harness.db"
    task = _verified_budget_task(db_path, tmp_path, estimate=50, budget={"daily_used_tokens": 0, "daily_cap_tokens": 100})

    result = launch_task(
        db_path,
        task["id"],
        adapter_id="opencode",
        model=None,
        proxy_url=None,
        runner=lambda plan: {"returncode": 0, "stdout": "done without model call", "stderr": ""},
    )
    failed_run = _wait_for_worker_run(db_path, task["id"], "failed")
    failed = db.get_task(db_path, task["id"])
    assert result.session is not None
    session = db.get_session(db_path, result.session["id"])

    assert failed_run["error_type"] == "missing_proxy_worker_usage"
    assert session["status"] == "failed"
    assert failed["status"] == "Estimated"
    assert failed["metadata"]["launch_error"] == "No Worker model call was observed through the Harness Proxy."
    assert failed["metadata"]["launch_failure_type"] == "missing_proxy_worker_usage"
    assert failed["metadata"]["launch_retryable"] is True


def test_direct_launch_recovers_stale_worker_run_before_duplicate_check(tmp_path):
    db_path = tmp_path / "harness.db"
    task = _verified_budget_task(db_path, tmp_path, estimate=50, budget={"daily_used_tokens": 0, "daily_cap_tokens": 100})
    stale_session = db.create_session(
        db_path,
        task_description=task["description"],
        model=task["recommended_model"],
        session_key_hash="d" * 64,
        guardrail_overrides={},
        status="running",
    )
    stale_run = db.create_worker_run(
        db_path,
        task_id=task["id"],
        session_id=stale_session["id"],
        adapter_id="opencode",
        model=task["recommended_model"],
        tracking_mode="proxy_governed",
        command_plan={"command": ["opencode"], "env": {}, "metadata": {}},
    )
    with db.connect(db_path) as conn:
        conn.execute(
            "update worker_runs set metadata_json = ? where id = ?",
            (json.dumps({"executor_pid": -1}), stale_run["id"]),
        )
    db.update_task(
        db_path,
        task["id"],
        {
            "status": "Running",
            "session_id": stale_session["id"],
            "metadata": {**task.get("metadata", {}), "active_worker_run_id": stale_run["id"]},
        },
    )

    result = launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=_runner_recording(db_path))
    completed_run = _wait_for_worker_run(db_path, task["id"], "completed")
    runs = db.list_worker_runs(db_path, task_id=task["id"])

    assert result.task["status"] == "Running"
    assert runs[0]["id"] == stale_run["id"]
    assert runs[0]["status"] == "failed"
    assert runs[0]["error_type"] == "interrupted"
    assert completed_run["id"] != stale_run["id"]
    assert db.get_task(db_path, task["id"])["status"] == "Review"


def test_launch_returns_before_long_running_worker_adapter_completes(tmp_path):
    db_path = tmp_path / "harness.db"
    task = _verified_budget_task(db_path, tmp_path, estimate=50, budget={"daily_used_tokens": 25, "daily_cap_tokens": 100})
    release_runner = threading.Event()

    def long_running_runner(plan):
        _write_worker_change(plan)
        db.record_token_turn(
            db_path,
            session_id=plan.metadata["session_id"],
            usage_kind="task_execution",
            model="opencode/gpt-5.1",
            prompt_tokens=10,
            completion_tokens=0,
            cost=0,
            raw_usage={"total_tokens": 10},
        )
        release_runner.wait(timeout=1)
        return {"returncode": 0, "stdout": "done", "stderr": ""}

    started_at = time.monotonic()
    result = launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=long_running_runner)
    elapsed = time.monotonic() - started_at

    assert elapsed < 0.25
    assert result.task["status"] == "Running"
    assert db.get_task(db_path, task["id"])["status"] == "Running"
    assert db.list_worker_runs(db_path, task_id=task["id"])[-1]["status"] == "running"

    release_runner.set()
    _wait_for_worker_run(db_path, task["id"], "completed")
    assert db.get_task(db_path, task["id"])["status"] == "Review"


def test_worker_adapter_launch_failure_preserves_launchable_status_and_records_retryable_error(tmp_path):
    db_path = tmp_path / "harness.db"
    task = _verified_budget_task(db_path, tmp_path, estimate=50, budget={"daily_used_tokens": 0, "daily_cap_tokens": 100})

    result = launch_task(
        db_path,
        task["id"],
        adapter_id="opencode",
        model=None,
        proxy_url=None,
        runner=lambda plan: {"returncode": 124, "stdout": "", "stderr": "Command timed out after 60 seconds."},
    )
    _wait_for_worker_run(db_path, task["id"], "failed")
    failed = db.get_task(db_path, task["id"])

    session = db.get_session(db_path, failed["session_id"])
    metadata = failed["metadata"]
    assert failed["status"] == "Estimated"
    assert session["status"] == "failed"
    assert metadata["launch_error"] == "Worker adapter launch failed."
    assert metadata["last_launch_failure"] == {
        "type": "worker_adapter_failure",
        "retryable": True,
        "returncode": 124,
        "stderr": "Command timed out after 60 seconds.",
    }
    assert metadata["launch_retryable"] is True
    assert "launch_blocked_reason" not in metadata
    assert result.worker_run is not None
    events = db.list_worker_run_events(db_path, worker_run_id=result.worker_run["id"])
    assert events[-1]["title"] == "Worker Run failed"
    assert events[-1]["detail"]["error_type"] == "worker_adapter_failure"
    assert events[-1]["level"] == "error"

    relaunched = launch_task(
        db_path,
        task["id"],
        adapter_id="opencode",
        model=None,
        proxy_url=None,
        runner=_runner_recording(db_path),
    )
    assert relaunched.task["status"] == "Running"
    assert "launch_error" not in relaunched.task["metadata"]
    assert "last_launch_failure" not in relaunched.task["metadata"]


def test_opencode_bare_launch_template_is_normalized_to_noninteractive_run_command(tmp_path):
    db_path = tmp_path / "harness.db"
    project_root = tmp_path / "connected-project"
    project_root.mkdir()
    task = _verified_budget_task(db_path, project_root, estimate=50, budget={"daily_used_tokens": 0, "daily_cap_tokens": 100})
    db.update_worker_adapter(
        db_path,
        "opencode",
        config={"launch_template": ["opencode"]},
        supported_models=["opencode/gpt-5.1"],
        is_default=True,
    )
    calls = []

    def failing_runner(plan):
        calls.append(plan)
        return {"returncode": 1, "stdout": "", "stderr": "opencode requires a run command"}

    launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=failing_runner)
    _wait_for_worker_run(db_path, task["id"], "failed")
    failed = db.get_task(db_path, task["id"])

    assert calls[0].cwd == project_root.resolve()
    assert calls[0].command[:-1] == [
        "opencode",
        "run",
        "--dir",
        str(project_root.resolve()),
        "--model",
        "opencode/gpt-5.1",
        "--format",
        "json",
    ]
    assert calls[0].command[-1].startswith("Repo Context Brief")
    assert "Task instructions:\nBudgeted launch" in calls[0].command[-1]
    assert failed["status"] == "Estimated"
    assert failed["metadata"]["last_launch_failure"]["returncode"] == 1
    assert failed["metadata"]["launch_command_plan"]["command"] == calls[0].command
    assert failed["metadata"]["launch_command_plan"]["metadata"]["model"] == "opencode/gpt-5.1"


def test_native_usage_budget_override_requires_explicit_acknowledgement(tmp_path):
    db_path = tmp_path / "harness.db"
    task = _verified_budget_task(db_path, tmp_path, estimate=75, budget={"daily_used_tokens": 50, "daily_cap_tokens": 100})
    db.update_worker_adapter(db_path, "opencode", config={"command": "opencode"}, supported_models=["opencode/gpt-5.1"])
    db.mark_worker_adapter_verification(
        db_path,
        "opencode",
        verified=True,
        evidence={"tracking_mode": "native_usage", "tracking_authoritative": True},
    )

    try:
        launch_task(
            db_path,
            task["id"],
            adapter_id="opencode",
            model=None,
            proxy_url=None,
            budget_override=True,
            runner=lambda plan: {"returncode": 0, "stdout": "should not run", "stderr": ""},
        )
    except TaskLaunchBlocked as exc:
        blocked = exc.task
    else:
        raise AssertionError("native usage budget override launched without acknowledgement")

    assert blocked["status"] == "Estimated"
    assert blocked["metadata"]["budget_override_available"] is True
    assert blocked["metadata"]["budget_override_tracking_mode"] == "native_usage"
    assert blocked["metadata"]["native_usage_override_ack_required"] is True
    assert "cannot be request-throttled" in blocked["metadata"]["native_usage_override_ack_text"]


def test_native_usage_launch_passes_selected_model_and_records_usage_metadata(tmp_path):
    db_path = tmp_path / "harness.db"
    task = _verified_budget_task(db_path, tmp_path, estimate=50, budget={"daily_used_tokens": 0, "daily_cap_tokens": 100})
    db.update_worker_adapter(
        db_path,
        "opencode",
        config={"command": "opencode"},
        supported_models=["opencode/gpt-5.1"],
    )
    db.mark_worker_adapter_verification(
        db_path,
        "opencode",
        verified=True,
        evidence={"tracking_mode": "native_usage", "tracking_authoritative": True},
    )
    calls = []

    def runner(plan):
        calls.append(plan)
        _write_worker_change(plan)
        return {
            "returncode": 0,
            "stdout": json.dumps(
                {
                    "type": "complete",
                    "message": "FOREMAN_SENTINEL_OK",
                    "model": "opencode/gpt-5.1",
                    "session_id": "opencode-session-2099",
                    "usage": {"input_tokens": 12, "output_tokens": 3, "total_tokens": 15, "cost": 0.01},
                }
            ),
            "stderr": "",
        }

    result = launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)
    _wait_for_worker_run(db_path, task["id"], "completed")
    session = db.get_session(db_path, result.session["id"])
    with db.connect(db_path) as conn:
        token_turn = conn.execute("select * from token_turns where session_id = ?", (session["id"],)).fetchone()

    assert calls[0].command[:-1] == [
        "opencode",
        "run",
        "--dir",
        str(tmp_path),
        "--model",
        "opencode/gpt-5.1",
        "--format",
        "json",
    ]
    assert calls[0].command[-1].startswith("Repo Context Brief")
    assert "Task instructions:\nBudgeted launch" in calls[0].command[-1]
    assert token_turn is not None
    assert calls[0].env == {}
    assert result.task["metadata"]["tracking_mode"] == "native_usage"
    assert result.task["metadata"]["usage_source"] == "native_usage"
    assert session["guardrail_overrides"]["task_launch"]["tracking_mode"] == "native_usage"
    assert token_turn["usage_kind"] == "task_execution"
    assert token_turn["total_tokens"] == 15
    assert json.loads(token_turn["raw_usage_json"])["usage_source"] == "native_usage"


def test_native_usage_launch_blocks_when_adapter_emits_no_usage_evidence(tmp_path):
    db_path = tmp_path / "harness.db"
    task = _verified_budget_task(db_path, tmp_path, estimate=50, budget={"daily_used_tokens": 0, "daily_cap_tokens": 100})
    db.update_worker_adapter(db_path, "opencode", config={"command": "opencode"}, supported_models=["opencode/gpt-5.1"])
    db.mark_worker_adapter_verification(
        db_path,
        "opencode",
        verified=True,
        evidence={"tracking_mode": "native_usage", "tracking_authoritative": True},
    )

    launch_task(
        db_path,
        task["id"],
        adapter_id="opencode",
        model=None,
        proxy_url=None,
        runner=lambda plan: {"returncode": 0, "stdout": "FOREMAN_SENTINEL_OK", "stderr": ""},
    )
    _wait_for_worker_run(db_path, task["id"], "failed")
    blocked = db.get_task(db_path, task["id"])

    assert blocked["status"] == "Estimated"
    assert blocked["metadata"]["launch_error"] == "No budget-authoritative native Worker usage evidence was emitted by the adapter."
    assert blocked["metadata"]["launch_failure_type"] == "missing_native_usage_evidence"
    assert blocked["metadata"]["launch_retryable"] is True
    assert blocked["metadata"]["launch_guardrail_reasons"] == [
        "No budget-authoritative native Worker usage evidence was emitted by the adapter."
    ]
    assert "launch_blocked_reason" not in blocked["metadata"]

    result = launch_task(
        db_path,
        task["id"],
        adapter_id="opencode",
        model=None,
        proxy_url=None,
        runner=lambda plan: {
            "returncode": 0,
            "stdout": json.dumps(
                {
                    "type": "complete",
                    "message": "FOREMAN_SENTINEL_OK",
                    "model": "opencode/gpt-5.1",
                    "session_id": "opencode-session-2099-retry",
                    "usage": {"input_tokens": 12, "output_tokens": 3, "total_tokens": 15, "cost": 0.01},
                }
            ),
            "stderr": "",
        },
    )

    assert result.task["status"] == "Running"
    assert "launch_error" not in result.task["metadata"]
    assert "launch_guardrail_reasons" not in result.task["metadata"]
    assert "last_launch_failure" not in result.task["metadata"]


def test_token_usage_breakdown_classifies_control_worker_verification_and_reporting(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    session = db.create_session(
        db_path,
        task_description="ledger",
        model="control-plane",
        session_key_hash="b" * 64,
        guardrail_overrides={},
        status="completed",
    )
    rows = [
        ("estimation", "control", 10),
        ("task_breakdown", "control", 7),
        ("task_execution", "worker", 20),
        ("adapter_verification", "worker", 5),
        ("reporting", "control", 3),
    ]
    for usage_kind, model, tokens in rows:
        db.record_token_turn(
            db_path,
            session_id=session["id"],
            usage_kind=usage_kind,
            model=model,
            prompt_tokens=tokens,
            completion_tokens=0,
            cost=0,
            raw_usage={"total_tokens": tokens},
        )

    breakdown = db.token_usage_breakdown(db_path)
    session_breakdown = db.session_token_breakdown(db_path, session["id"])

    assert breakdown["total_tokens"] == 45
    assert breakdown["by_category"] == {
        "control_plane": 10,
        "task_breakdown": 7,
        "worker_execution": 20,
        "adapter_verification": 5,
        "reporting_summary": 3,
        "other": 0,
    }
    assert breakdown == session_breakdown
    assert breakdown["by_source"]["control_plane"] == 17
    assert breakdown["by_source"]["harness_proxy"] == 25


def test_launch_budget_counts_prior_control_plane_reporting_spend(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    review_session = db.create_session(
        db_path,
        task_description="Agent Review spend",
        model="control-plane",
        session_key_hash="c" * 64,
        guardrail_overrides={"spend_category": "agent_review"},
        status="completed",
    )
    db.record_token_turn(
        db_path,
        session_id=review_session["id"],
        usage_kind="reporting",
        model="control-plane",
        prompt_tokens=1000,
        completion_tokens=0,
        cost=0,
        raw_usage={
            "total_tokens": 1000,
            "spend_category": "reporting_summary",
            "usage_source": "control_plane",
            "reporting_kind": "agent_review",
        },
    )
    task = _verified_budget_task(
        db_path,
        tmp_path,
        estimate=10,
        budget={"daily_used_tokens": 0, "daily_cap_tokens": 1005, "session_cap_tokens": 20},
    )
    calls = []

    try:
        launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=lambda plan: calls.append(plan))
    except TaskLaunchBlocked as exc:
        blocked = exc.task
    else:
        raise AssertionError("expected Agent Review spend to consume remaining daily budget")

    assert blocked["status"] == "Estimated"
    budget_check = blocked["metadata"]["budget_check"]
    assert budget_check["passed"] is False
    assert budget_check["current_recorded_tokens"] == 1000
    assert budget_check["current_worker_execution_tokens"] == 0
    assert budget_check["remaining_tokens"] == 5
    assert calls == []


def test_portal_launch_day_start_uses_local_midnight(monkeypatch):
    if not hasattr(time, "tzset"):
        pytest.skip("tzset is required to verify local timezone day starts")
    monkeypatch.setenv("TZ", "America/Los_Angeles")
    time.tzset()
    try:
        day_start = _portal_launch_day_start_iso("local")
    finally:
        monkeypatch.delenv("TZ", raising=False)
        time.tzset()

    parsed = datetime.fromisoformat(day_start)
    local = parsed.astimezone(ZoneInfo("America/Los_Angeles"))
    assert parsed.utcoffset() == UTC.utcoffset(None)
    assert local.hour == 0
    assert local.minute == 0


def test_estimate_over_budget_blocks_without_runner_and_shows_override(tmp_path):
    db_path = tmp_path / "harness.db"
    task = _verified_budget_task(db_path, tmp_path, estimate=80, budget={"daily_used_tokens": 40, "daily_cap_tokens": 100})
    calls = []

    try:
        launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=lambda plan: calls.append(plan))
    except TaskLaunchBlocked as exc:
        blocked = exc.task
    else:
        raise AssertionError("expected budget block")

    assert blocked["status"] == "Estimated"
    assert blocked["metadata"]["budget_check"]["passed"] is False
    assert blocked["metadata"]["budget_override_available"] is True
    assert calls == []


def test_budget_override_is_recorded_and_audited_on_session(tmp_path):
    db_path = tmp_path / "harness.db"
    task = _verified_budget_task(db_path, tmp_path, estimate=80, budget={"daily_used_tokens": 40, "daily_cap_tokens": 100})

    result = launch_task(
        db_path,
        task["id"],
        adapter_id="opencode",
        model=None,
        proxy_url=None,
        budget_override=True,
        runner=_runner_recording(db_path),
    )
    session = db.get_session(db_path, result.session["id"])

    assert result.task["metadata"]["budget_override"]["approved"] is True
    assert session["guardrail_overrides"]["budget"]["budget_override"] is True
    assert session["guardrail_overrides"]["budget"]["budget_override_reason"] == "operator_approved_launch"


def test_budget_overrun_records_alarm_without_auto_killing_session(tmp_path):
    db_path = tmp_path / "harness.db"
    task = _verified_budget_task(db_path, tmp_path, estimate=10, budget={"daily_used_tokens": 0, "daily_cap_tokens": 100, "session_cap_tokens": 20})

    result = launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=_runner_recording(db_path, total_tokens=25))
    assert result.task["status"] == "Running"
    _wait_for_worker_run(db_path, task["id"], "completed")
    session = db.get_session(db_path, result.session["id"])
    alarms = db.list_alarms(db_path, session_id=session["id"])

    assert session["status"] == "completed"
    assert alarms
    assert alarms[0]["type"] == "BUDGET_OVERRUN"


def test_budget_overrun_alarm_uses_reset_window_after_launch(tmp_path):
    db_path = tmp_path / "harness.db"
    task = _verified_budget_task(
        db_path,
        tmp_path,
        estimate=10,
        budget={"daily_used_tokens": 0, "daily_cap_tokens": 1_000, "session_cap_tokens": 500},
    )
    prior_session = db.create_session(
        db_path,
        task_description="Pre-reset DEMO budget spend 2099",
        model="opencode/gpt-5.1",
        session_key_hash="c" * 64,
        guardrail_overrides={},
    )
    db.record_token_turn(
        db_path,
        session_id=prior_session["id"],
        usage_kind="task_execution",
        model="opencode/gpt-5.1",
        prompt_tokens=950,
        completion_tokens=0,
        cost=0,
        raw_usage={"total_tokens": 950},
    )
    started = threading.Event()
    release = threading.Event()

    def runner(plan):
        started.set()
        assert release.wait(timeout=2)
        _write_worker_change(plan)
        db.record_token_turn(
            db_path,
            session_id=plan.metadata["session_id"],
            usage_kind="task_execution",
            model="opencode/gpt-5.1",
            prompt_tokens=100,
            completion_tokens=0,
            cost=0,
            raw_usage={"total_tokens": 100},
        )
        return {"returncode": 0, "stdout": "done", "stderr": ""}

    result = launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)
    assert result.task["status"] == "Running"
    assert started.wait(timeout=2)
    db.reset_daily_budget_counter(db_path)
    release.set()
    _wait_for_worker_run(db_path, task["id"], "completed")

    assert result.session is not None
    session = db.get_session(db_path, result.session["id"])
    assert session["status"] == "completed"
    assert db.list_alarms(db_path, session_id=session["id"], alarm_type="BUDGET_OVERRUN") == []


def test_stale_worker_run_recovery_marks_task_retryable(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    session = db.create_session(
        db_path,
        task_description="Interrupted DEMO worker 2099",
        model="opencode/gpt-5.1",
        session_key_hash="b" * 64,
        guardrail_overrides={},
        status="running",
    )
    task = db.create_task(
        db_path,
        description="Interrupted DEMO worker 2099",
        status="Running",
        estimate_tokens=10,
        recommended_model="opencode/gpt-5.1",
        session_id=session["id"],
    )
    run = db.create_worker_run(
        db_path,
        task_id=task["id"],
        session_id=session["id"],
        adapter_id="opencode",
        model="opencode/gpt-5.1",
        tracking_mode="proxy_governed",
        command_plan={"command": ["opencode"]},
        metadata={},
    )
    with db.connect(db_path) as conn:
        conn.execute(
            "update worker_runs set metadata_json = ? where id = ?",
            (json.dumps({"executor_pid": -1}), run["id"]),
        )

    interrupted = db.mark_stale_worker_runs_interrupted(db_path)

    recovered_task = db.get_task(db_path, task["id"])
    recovered_run = db.get_worker_run(db_path, run["id"])
    recovered_session = db.get_session(db_path, session["id"])
    assert interrupted
    assert recovered_run["status"] == "failed"
    assert recovered_run["error_type"] == "interrupted"
    assert recovered_task["status"] == "Estimated"
    assert recovered_task["metadata"]["launch_retryable"] is True
    assert recovered_session["status"] == "failed"


def test_manual_abort_preserves_task_metadata_and_marks_session_aborted(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    session = db.create_session(
        db_path,
        task_description="Abort me",
        model="opencode/gpt-5.1",
        session_key_hash="a" * 64,
        guardrail_overrides={"task_launch": {"task_branch": "foremanctl/task-demo-2099"}},
        status="running",
    )
    task = db.create_task(
        db_path,
        description="Abort me",
        status="Running",
        estimate_tokens=10,
        recommended_model="opencode/gpt-5.1",
        session_id=session["id"],
        metadata={"task_branch": "foremanctl/task-demo-2099", "diff_summary": {"files_changed": ["demo.py"]}},
    )
    db.record_token_turn(
        db_path,
        session_id=session["id"],
        usage_kind="task_execution",
        model="opencode/gpt-5.1",
        prompt_tokens=1,
        completion_tokens=1,
        cost=0,
        raw_usage={"total_tokens": 2},
    )

    aborted = abort_worker_session(db_path, session["id"], reason="operator stopped runaway task")
    refreshed = db.get_task(db_path, task["id"])
    artifact = db.build_session_artifact(db_path, session["id"])

    assert aborted["session"]["status"] == "aborted"
    assert refreshed["status"] == "Review"
    assert refreshed["metadata"]["abort_reason"] == "operator stopped runaway task"
    assert refreshed["metadata"]["task_branch"] == "foremanctl/task-demo-2099"
    assert artifact["token_log"][0]["total_tokens"] == 2
