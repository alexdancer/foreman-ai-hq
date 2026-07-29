import json
import subprocess
from pathlib import Path
import time

from foreman_ai_hq import db
from foreman_ai_hq.execution_backend import LocalExecutionBackend, detect_project_profile, validate_local_project_path
from foreman_ai_hq.project_context import project_task_metadata
from foreman_ai_hq.task_kind import with_task_kind
from foreman_ai_hq.task_launch import TaskLaunchBlocked, launch_task
from tests.conftest import git_project_profile


def _wait_for_worker_run(db_path: Path, task_id: str, status: str | None = None):
    deadline = time.time() + 2
    while time.time() < deadline:
        runs = db.list_worker_runs(db_path, task_id=task_id)
        if runs and (status is None or runs[-1]["status"] == status):
            return runs[-1]
        time.sleep(0.01)
    raise AssertionError("worker run did not reach expected status")


def _project_root(tmp_path: Path) -> Path:
    root = tmp_path / "demo-project"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname = "demo"\ndependencies = ["fastapi"]\n')
    (root / "README.md").write_text("# Demo\n")
    (root / "src").mkdir()
    return root


def _connect_project(db_path: Path, root: Path, *, git: bool = True) -> dict:
    # `git=False` keeps a bare directory for the native workdir-evidence tests, whose
    # subject is an *empty* configured workdir; a git fixture would populate it.
    profile = (
        git_project_profile(root)
        if git
        else {"name": root.name, "root_path": str(root.resolve()), "test_command": "pytest"}
    )
    return db.upsert_connected_project(
        db_path,
        name=root.name,
        root_path=str(root.resolve()),
        profile=profile,
        capability={"state": "launch_ready", "can_launch": True},
    )


def test_local_project_validation_rejects_missing_paths_but_allows_unmarked_directories(tmp_path):
    assert validate_local_project_path(tmp_path / "missing") == "Local project path does not exist."

    empty = tmp_path / "empty"
    empty.mkdir()
    assert validate_local_project_path(empty) is None


def test_profile_detection_records_lightweight_project_context(tmp_path):
    root = _project_root(tmp_path)

    profile = detect_project_profile(root)

    assert profile["name"] == "demo-project"
    assert profile["root_path"] == str(root.resolve())
    assert profile["language_hints"] == ["python"]
    assert "fastapi" in profile["framework_hints"]
    assert "pip" in profile["package_manager_hints"]
    assert profile["test_command_suggested"] == "pytest"
    assert profile["test_command"] is None
    assert profile["test_command_confirmed"] is False
    assert "src" in profile["top_level_folders"]
    assert "README.md" in profile["relevant_docs"]


def test_local_execution_backend_persists_project_profile_and_analysis_capability(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    root = _project_root(tmp_path)

    result = LocalExecutionBackend(db_path).connect_project(root)

    assert result.error is None
    assert result.project is not None
    project = db.list_connected_projects(db_path)[0]
    assert project["root_path"] == str(root.resolve())
    assert project["profile"]["test_command_suggested"] == "pytest"
    assert project["profile"]["test_command"] is None
    assert project["capability"]["state"] == "analysis_ready"
    assert "No verified launchable Worker Adapter is available." in project["capability"]["reasons"]
    backend_status = db.get_execution_backend_status(db_path, "local_runner")
    assert backend_status["online"] is True


def test_local_execution_backend_connects_unmarked_directory(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    root = tmp_path / "experiment-demo"
    root.mkdir()
    (root / "notes.txt").write_text("demo inputs\n")

    result = LocalExecutionBackend(db_path).connect_project(root)

    assert result.error is None
    assert result.project is not None
    assert result.project["root_path"] == str(root.resolve())
    assert result.project["profile"]["name"] == "experiment-demo"
    assert result.project["profile"]["top_level_entries"] == ["notes.txt"]
    assert result.project["capability"]["state"] == "analysis_ready"


def test_project_capability_stays_analysis_ready_with_observed_only_adapter(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    root = _project_root(tmp_path)
    db.mark_worker_adapter_verification(
        db_path,
        "opencode",
        verified=True,
        evidence={"tracking_mode": "observed_only", "tracking_authoritative": False},
    )

    result = LocalExecutionBackend(db_path).connect_project(root)

    assert result.project is not None
    assert result.project["capability"]["state"] == "analysis_ready"
    assert "No verified launchable Worker Adapter is available." in result.project["capability"]["reasons"]


def test_project_capability_is_launch_ready_with_online_backend_and_verified_adapter(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    root = _project_root(tmp_path)
    db.update_worker_adapter(
        db_path,
        "opencode",
        supported_models=["opencode/gpt-5.1"],
    )
    db.mark_worker_adapter_verification(db_path, "opencode", verified=True, evidence={"ok": True})

    result = LocalExecutionBackend(db_path).connect_project(root)

    assert result.project is not None
    assert result.project["capability"]["state"] == "launch_ready"
    assert result.project["capability"]["label"] == "Launch-ready via Local Runner"
    assert result.project["capability"]["reasons"] == []



def test_read_only_proof_task_launches_in_connected_repo_and_persists_report(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    root = _project_root(tmp_path)
    db.update_worker_adapter(
        db_path,
        "opencode",
        supported_models=["opencode/gpt-5.1"],
    )
    db.mark_worker_adapter_verification(db_path, "opencode", verified=True, evidence={"ok": True})
    backend = LocalExecutionBackend(db_path)
    project = backend.connect_project(root).project
    assert project is not None
    task = backend.create_read_only_proof_task(project)
    runner_calls = []

    def fake_runner(plan):
        runner_calls.append(plan)
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
        return {"returncode": 0, "stdout": "report complete", "stderr": ""}

    result = launch_task(
        db_path,
        task["id"],
        adapter_id="opencode",
        model="opencode/gpt-5.1",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=fake_runner,
    )

    assert result.task["status"] == "Running"
    _wait_for_worker_run(db_path, task["id"], "completed")
    assert runner_calls[0].cwd == root.resolve()
    assert runner_calls[0].env["OPENAI_BASE_URL"] == "http://127.0.0.1:8000/v1"
    refreshed = db.get_task(db_path, task["id"])
    refreshed = db.get_task(db_path, task["id"])
    assert refreshed["status"] == "Review"
    assert refreshed["metadata"]["session_report"]["test_command"] == "pytest"
    assert "src" in refreshed["metadata"]["session_report"]["top_level_structure"]


def test_read_only_proof_blocks_when_no_worker_model_call_observed(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    root = _project_root(tmp_path)
    db.update_worker_adapter(
        db_path,
        "opencode",
        supported_models=["opencode/gpt-5.1"],
    )
    db.mark_worker_adapter_verification(db_path, "opencode", verified=True, evidence={"ok": True})
    backend = LocalExecutionBackend(db_path)
    project = backend.connect_project(root).project
    assert project is not None
    task = backend.create_read_only_proof_task(project)

    launch_task(
        db_path,
        task["id"],
        adapter_id="opencode",
        model="opencode/gpt-5.1",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=lambda plan: {"returncode": 0, "stdout": "no model call", "stderr": ""},
    )
    _wait_for_worker_run(db_path, task["id"], "failed")
    blocked = db.get_task(db_path, task["id"])

    assert blocked["status"] == "Estimated"
    assert blocked["metadata"]["launch_error"] == "No Worker model call was observed through the Harness Proxy."
    assert blocked["metadata"]["launch_failure_type"] == "missing_proxy_worker_usage"
    assert blocked["metadata"]["launch_retryable"] is True
    assert blocked["metadata"]["launch_guardrail_reasons"] == ["No Worker model call was observed through the Harness Proxy."]
    assert "launch_blocked_reason" not in blocked["metadata"]


def test_read_only_proof_blocks_when_worker_modifies_files(tmp_path):
    import subprocess

    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    root = _project_root(tmp_path)
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=demo@example.com", "-c", "user.name=Demo", "commit", "-m", "initial"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    db.update_worker_adapter(
        db_path,
        "opencode",
        supported_models=["opencode/gpt-5.1"],
    )
    db.mark_worker_adapter_verification(db_path, "opencode", verified=True, evidence={"ok": True})
    backend = LocalExecutionBackend(db_path)
    project = backend.connect_project(root).project
    assert project is not None
    task = backend.create_read_only_proof_task(project)

    def modifying_runner(plan):
        (root / "src" / "changed.py").write_text("print('changed')\n")
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
        return {"returncode": 0, "stdout": "modified", "stderr": ""}

    launch_task(
        db_path,
        task["id"],
        adapter_id="opencode",
        model="opencode/gpt-5.1",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=modifying_runner,
    )
    _wait_for_worker_run(db_path, task["id"], "failed")
    blocked = db.get_task(db_path, task["id"])

    assert blocked["status"] == "Review"
    assert blocked["metadata"]["launch_blocked_reason"] == "Read-only Worker session modified the connected project."
    assert "src/" in blocked["metadata"]["readonly_diff_evidence"]["after"]


def _native_usage_stdout(model: str, *, extra_path: str | None = None) -> str:
    payload = {
        "session_id": "DEMO_2099_NATIVE_RUN_999",
        "model": model,
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost_usd": 0},
    }
    lines = [json.dumps(payload)]
    if extra_path:
        lines.append(f"wrote {extra_path}")
    return "\n".join(lines)


def _claude_native_usage_stdout() -> str:
    return json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "session_id": "session_2099_demo_claude",
            "total_cost_usd": 0.0065403,
            "usage": {
                "input_tokens": 3,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 21571,
                "output_tokens": 4,
            },
            "modelUsage": {
                "claude-sonnet-4-6": {
                    "inputTokens": 3,
                    "outputTokens": 4,
                    "cacheReadInputTokens": 21571,
                    "cacheCreationInputTokens": 0,
                    "costUSD": 0.0065403,
                }
            },
        }
    )


def _claude_permission_denied_stdout() -> str:
    payload = json.loads(_claude_native_usage_stdout())
    payload["permission_denials"] = [
        {"tool_name": "Bash", "tool_input": {"command": "rtk pwd"}},
        {"tool_name": "Write", "tool_input": {"file_path": "/tmp/DEMO_2099_file.md"}},
    ]
    payload["result"] = "I need file write permissions."
    return json.dumps(payload) + "\nwrote /Users/alex/.claude/projects/DEMO_2099/memory"


def _claude_permission_denied_without_usage_stdout() -> str:
    return json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "permission_denials": [{"tool_name": "Write", "tool_input": {"file_path": "/tmp/DEMO_2099_file.md"}}],
            "result": "I need file write permissions.",
        }
    )


def _worker_change_then(root: Path, stdout: str) -> dict:
    """A write-capable Worker that changes nothing fails, so leave a change behind."""
    (root / "worker_change.txt").write_text("changed\n")
    return {"returncode": 0, "stdout": stdout, "stderr": ""}


def _estimated_task(db_path: Path, *, task_kind: str = "implementation") -> dict:
    project = db.list_connected_projects(db_path)[0]
    return db.create_task(
        db_path,
        description="Implement DEMO_2099 incident ledger task.",
        status="Estimated",
        estimate_tokens=1_000,
        recommended_model="openai/gpt-5.5",
        metadata=with_task_kind(project_task_metadata(project), task_kind),
    )


def test_native_worker_run_fails_when_output_points_outside_empty_configured_workdir(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    harness_target = tmp_path / "harness-target"
    harness_target.mkdir()
    outside_file = tmp_path / "incident-ledger" / "src" / "incident_ledger" / "cli.py"
    outside_file.parent.mkdir(parents=True)
    outside_file.write_text("print('DEMO_2099')\n")
    _connect_project(db_path, harness_target, git=False)
    db.update_worker_adapter(db_path, "opencode", workdir=str(harness_target), supported_models=["openai/gpt-5.5"])
    db.mark_worker_adapter_verification(db_path, "opencode", verified=True, evidence={"tracking_mode": "native_usage"})
    task = _estimated_task(db_path, task_kind="acceptance_verification")

    launch_task(
        db_path,
        task["id"],
        adapter_id="opencode",
        model="openai/gpt-5.5",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=lambda plan: {"returncode": 0, "stdout": _native_usage_stdout("openai/gpt-5.5", extra_path=str(outside_file)), "stderr": ""},
    )
    run = _wait_for_worker_run(db_path, task["id"], "failed")
    blocked = db.get_task(db_path, task["id"])

    assert blocked["status"] == "Estimated"
    assert blocked["metadata"]["launch_failure_type"] == "workdir_mismatch"
    assert blocked["metadata"]["launch_error"] == "Worker completed but produced evidence outside the configured workdir."
    evidence = blocked["metadata"]["workdir_evidence"]
    assert evidence["configured_workdir"] == str(harness_target.resolve())
    assert evidence["top_level_entries"] == []
    assert str(outside_file.resolve()) in evidence["outside_paths"]
    assert run["metadata"]["workdir_evidence"] == evidence


def test_native_worker_workdir_evidence_ignores_json_escaped_newline_after_configured_root(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    harness_target = tmp_path / "harness-target"
    harness_target.mkdir()
    _connect_project(db_path, harness_target, git=False)
    db.update_worker_adapter(db_path, "opencode", workdir=str(harness_target), supported_models=["openai/gpt-5.5"])
    db.mark_worker_adapter_verification(db_path, "opencode", verified=True, evidence={"tracking_mode": "native_usage"})
    task = _estimated_task(db_path, task_kind="acceptance_verification")

    launch_task(
        db_path,
        task["id"],
        adapter_id="opencode",
        model="openai/gpt-5.5",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=lambda plan: {
            "returncode": 0,
            "stdout": _native_usage_stdout("openai/gpt-5.5", extra_path=f"{harness_target.resolve()}\\n"),
            "stderr": "",
        },
    )
    run = _wait_for_worker_run(db_path, task["id"], "completed")
    reviewed = db.get_task(db_path, task["id"])

    assert reviewed["status"] == "Review"
    assert reviewed["metadata"]["workdir_evidence"]["outside_paths"] == []
    assert run["metadata"]["workdir_evidence"] == reviewed["metadata"]["workdir_evidence"]


def test_native_worker_workdir_evidence_keeps_outside_path_after_json_escaped_newline(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    harness_target = tmp_path / "harness-target"
    harness_target.mkdir()
    outside_file = tmp_path / "outside-root" / "demo.py"
    outside_file.parent.mkdir()
    outside_file.write_text("print('DEMO_2099')\n")
    _connect_project(db_path, harness_target, git=False)
    db.update_worker_adapter(db_path, "opencode", workdir=str(harness_target), supported_models=["openai/gpt-5.5"])
    db.mark_worker_adapter_verification(db_path, "opencode", verified=True, evidence={"tracking_mode": "native_usage"})
    task = _estimated_task(db_path, task_kind="acceptance_verification")

    launch_task(
        db_path,
        task["id"],
        adapter_id="opencode",
        model="openai/gpt-5.5",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=lambda plan: {
            "returncode": 0,
            "stdout": _native_usage_stdout(
                "openai/gpt-5.5", extra_path=f"{harness_target.resolve()}\\n{outside_file.resolve()}"
            ),
            "stderr": "",
        },
    )
    run = _wait_for_worker_run(db_path, task["id"], "failed")
    blocked = db.get_task(db_path, task["id"])

    assert blocked["status"] == "Estimated"
    evidence = blocked["metadata"]["workdir_evidence"]
    assert str(outside_file.resolve()) in evidence["outside_paths"]
    assert run["metadata"]["workdir_evidence"] == evidence


def test_write_capable_run_without_code_changes_is_blocked_by_the_diff_check(tmp_path):
    """The adapter-agnostic diff check replaced the codex-only `no_workdir_changes` rule."""
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    harness_target = tmp_path / "harness-target"
    harness_target.mkdir()
    (harness_target / "README.md").write_text("# DEMO_2099\n")
    _connect_project(db_path, harness_target)
    db.update_worker_adapter(db_path, "codex", workdir=str(harness_target), supported_models=["gpt-5.6-terra"])
    db.mark_worker_adapter_verification(db_path, "codex", verified=True, evidence={"tracking_mode": "native_usage"})
    task = _estimated_task(db_path)

    launch_task(
        db_path,
        task["id"],
        adapter_id="codex",
        model="gpt-5.6-terra",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=lambda plan: {"returncode": 0, "stdout": _native_usage_stdout("gpt-5.6-terra"), "stderr": ""},
    )
    _wait_for_worker_run(db_path, task["id"], "failed")
    blocked = db.get_task(db_path, task["id"])

    assert blocked["status"] == "Review"
    assert blocked["metadata"]["blocked_reason"] == "Worker completed but produced no code changes."
    assert blocked["metadata"]["blocked_condition"]["origin"] == "write_completion"
    assert blocked["metadata"]["diff_summary"]["has_changes"] is False


# A pre-existing dirty edit is now refused by the Repository Cleanliness Guardrail before
# launch, which `tests/workers/test_write_capable_launch.py` covers, so the old
# misclassification guard has no surviving code path to protect.


def test_claude_code_native_worker_run_records_cache_inclusive_usage(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    harness_target = tmp_path / "harness-target"
    harness_target.mkdir()
    (harness_target / "README.md").write_text("# DEMO_2099\n")
    _connect_project(db_path, harness_target)
    db.update_worker_adapter(db_path, "claude_code", workdir=str(harness_target), supported_models=["sonnet"])
    db.mark_worker_adapter_verification(db_path, "claude_code", verified=True, evidence={"tracking_mode": "native_usage"})
    task = _estimated_task(db_path)

    launch_task(
        db_path,
        task["id"],
        adapter_id="claude_code",
        model="sonnet",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=lambda plan: _worker_change_then(harness_target, _claude_native_usage_stdout()),
    )
    _wait_for_worker_run(db_path, task["id"], "completed")
    reviewed = db.get_task(db_path, task["id"])
    artifact = db.build_session_artifact(db_path, reviewed["session_id"])

    assert reviewed["status"] == "Review"
    turn = artifact["token_log"][0]
    assert turn["model"] == "sonnet"
    assert turn["prompt_tokens"] == 21574
    assert turn["completion_tokens"] == 4
    assert turn["total_tokens"] == 21578
    assert turn["cost"] == 0.0065403
    assert turn["raw_usage"]["source"]["modelUsage"]["claude-sonnet-4-6"]["costUSD"] == 0.0065403


def test_failed_native_worker_run_records_emitted_usage_as_failed_retry_spend(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    harness_target = tmp_path / "harness-target"
    harness_target.mkdir()
    _connect_project(db_path, harness_target)
    db.update_worker_adapter(db_path, "claude_code", workdir=str(harness_target), supported_models=["sonnet"])
    db.mark_worker_adapter_verification(db_path, "claude_code", verified=True, evidence={"tracking_mode": "native_usage"})
    task = _estimated_task(db_path)

    launch_task(
        db_path,
        task["id"],
        adapter_id="claude_code",
        model="sonnet",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=lambda plan: {"returncode": 1, "stdout": _claude_native_usage_stdout(), "stderr": "worker crashed after usage"},
    )
    run = _wait_for_worker_run(db_path, task["id"], "failed")
    refreshed = db.get_task(db_path, task["id"])
    artifact = db.build_session_artifact(db_path, refreshed["session_id"])

    assert refreshed["status"] == "Estimated"
    assert refreshed["metadata"]["launch_failure_type"] == "worker_adapter_failure"
    assert run["error_type"] == "worker_adapter_failure"
    assert artifact["token_log"][0]["total_tokens"] == 21578
    assert db.budgeted_token_usage(db_path) == 7
    assert db.worker_execution_token_summary(db_path)["status_split"]["failed_retry"] == 7


def test_claude_code_permission_denials_are_reported_before_workdir_mismatch(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    harness_target = tmp_path / "harness-target"
    harness_target.mkdir()
    _connect_project(db_path, harness_target)
    db.update_worker_adapter(db_path, "claude_code", workdir=str(harness_target), supported_models=["sonnet"])
    db.mark_worker_adapter_verification(db_path, "claude_code", verified=True, evidence={"tracking_mode": "native_usage"})
    task = _estimated_task(db_path)

    launch_task(
        db_path,
        task["id"],
        adapter_id="claude_code",
        model="sonnet",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=lambda plan: {"returncode": 0, "stdout": _claude_permission_denied_stdout(), "stderr": ""},
    )
    run = _wait_for_worker_run(db_path, task["id"], "failed")
    refreshed = db.get_task(db_path, task["id"])

    assert refreshed["status"] == "Estimated"
    assert refreshed["metadata"]["launch_failure_type"] == "worker_permission_denied"
    assert refreshed["metadata"]["permission_denials"] == ["Bash", "Write"]
    assert refreshed["metadata"]["launch_error"] == "Worker was denied required tool permissions: Bash, Write."
    assert "workdir_evidence" not in refreshed["metadata"]
    assert run["error_type"] == "worker_permission_denied"
    artifact = db.build_session_artifact(db_path, refreshed["session_id"])
    assert artifact["token_log"][0]["total_tokens"] == 21578


def test_claude_code_permission_denials_are_reported_without_usage_evidence(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    harness_target = tmp_path / "harness-target"
    harness_target.mkdir()
    _connect_project(db_path, harness_target)
    db.update_worker_adapter(db_path, "claude_code", workdir=str(harness_target), supported_models=["sonnet"])
    db.mark_worker_adapter_verification(db_path, "claude_code", verified=True, evidence={"tracking_mode": "native_usage"})
    task = _estimated_task(db_path)

    launch_task(
        db_path,
        task["id"],
        adapter_id="claude_code",
        model="sonnet",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=lambda plan: {"returncode": 0, "stdout": _claude_permission_denied_without_usage_stdout(), "stderr": ""},
    )
    run = _wait_for_worker_run(db_path, task["id"], "failed")
    refreshed = db.get_task(db_path, task["id"])

    assert refreshed["metadata"]["launch_failure_type"] == "worker_permission_denied"
    assert refreshed["metadata"]["permission_denials"] == ["Write"]
    assert run["error_type"] == "worker_permission_denied"


def test_claude_code_native_worker_run_without_usage_returns_to_estimated(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    harness_target = tmp_path / "harness-target"
    harness_target.mkdir()
    (harness_target / "README.md").write_text("# DEMO_2099\n")
    _connect_project(db_path, harness_target)
    db.update_worker_adapter(db_path, "claude_code", workdir=str(harness_target), supported_models=["sonnet"])
    db.mark_worker_adapter_verification(db_path, "claude_code", verified=True, evidence={"tracking_mode": "native_usage"})
    task = _estimated_task(db_path)

    launch_task(
        db_path,
        task["id"],
        adapter_id="claude_code",
        model="sonnet",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=lambda plan: {"returncode": 0, "stdout": json.dumps({"result": "ok"}), "stderr": ""},
    )
    run = _wait_for_worker_run(db_path, task["id"], "failed")
    refreshed = db.get_task(db_path, task["id"])

    assert refreshed["status"] == "Estimated"
    assert refreshed["metadata"]["launch_failure_type"] == "missing_native_usage_evidence"
    assert refreshed["metadata"]["launch_retryable"] is True
    assert refreshed["metadata"]["launch_error"] == "No budget-authoritative native Worker usage evidence was emitted by the adapter."
    assert run["error_type"] == "missing_native_usage_evidence"
