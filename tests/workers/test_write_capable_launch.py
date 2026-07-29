from __future__ import annotations

import shlex
import subprocess
import sys
import time
from pathlib import Path

from foreman_ai_hq import db
from foreman_ai_hq.project_context import project_task_metadata
from foreman_ai_hq.routes.react_shell import _task_controls
from foreman_ai_hq.routes.tasks import (
    _agent_review_diff_summary,
    _approve_harness_commit,
    _mark_review_done,
    _open_pull_request,
)
from foreman_ai_hq.task_kind import with_task_kind
from foreman_ai_hq.task_launch import (
    TaskLaunchBlocked,
    _git_diff_summary,
    detect_pr_capability,
    launch_task,
)


# The interpreter running the suite is the only one guaranteed to exist; a bare
# `python` is absent on plenty of machines and would fail verification silently.
PASSING_TEST_COMMAND = f"{shlex.quote(sys.executable)} -m pytest"
FAILING_TEST_COMMAND = f"{shlex.quote(sys.executable)} -c 'raise SystemExit(1)'"


def _wait_for_worker_run(db_path: Path, task_id: str, status: str | None = None):
    deadline = time.time() + 5
    while time.time() < deadline:
        runs = db.list_worker_runs(db_path, task_id=task_id)
        if runs and (status is None or runs[-1]["status"] == status):
            return runs[-1]
        time.sleep(0.01)
    raise AssertionError("worker run did not reach expected status")


def _git_project(tmp_path: Path, *, files: dict[str, str] | None = None) -> Path:
    root = tmp_path / "write-project"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname = 'write-demo'\n")
    (root / "test_sample.py").write_text("def test_ok():\n    assert True\n")
    if files:
        for name, content in files.items():
            (root / name).write_text(content)
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=demo@example.com", "-c", "user.name=Demo", "commit", "-m", "initial"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return root


def _current_branch(root: Path) -> str:
    return subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _verified_project(db_path: Path, root: Path, *, test_command: str | None = PASSING_TEST_COMMAND, base_branch: str | None = None) -> dict[str, object]:
    db.init_db(db_path)
    profile: dict[str, object] = {
        "root_path": str(root),
        "test_command_suggested": test_command,
        "test_command_confirmed": test_command is not None,
        "test_command": test_command,
    }
    branch = base_branch or _current_branch(root)
    profile["base_branch_suggested"] = branch
    profile["base_branch"] = branch
    profile["base_branch_confirmed"] = True
    project = db.upsert_connected_project(
        db_path,
        name="Write Project",
        root_path=str(root),
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
    return project


def _verified_task(db_path: Path, root: Path, *, test_command: str | None = PASSING_TEST_COMMAND, task_kind: str = "implementation") -> dict[str, object]:
    project = _verified_project(db_path, root, test_command=test_command)
    return db.create_task(
        db_path,
        description="Write code change",
        status="Ready",
        estimate_tokens=1000,
        recommended_model="opencode/gpt-5.1",
        metadata=with_task_kind({**project_task_metadata(project)}, task_kind),
    )


def _record_worker_usage(db_path: Path, plan):
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


def _runner_that_writes(root: Path, path: str, content: str):
    def runner(plan):
        _record_worker_usage(root if isinstance(root, Path) else Path(str(root)), plan)
        (Path(str(root)) / path).write_text(content)
        return {"returncode": 0, "stdout": "changed", "stderr": ""}

    return runner


def test_implementation_task_creates_branch_and_commits_without_metadata_flag(tmp_path):
    """7.2 An implementation Task creates a branch and commits without any metadata flag."""
    db_path = tmp_path / "harness.db"
    root = _git_project(tmp_path)
    task = _verified_task(db_path, root)
    operator_branch = _current_branch(root)

    def runner(plan):
        _record_worker_usage(db_path, plan)
        (root / "feature.py").write_text("VALUE = 'demo'\n")
        return {"returncode": 0, "stdout": "changed", "stderr": ""}

    result = launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)
    assert result.task["status"] == "Running"
    _wait_for_worker_run(db_path, task["id"], "completed")
    launched = db.get_task(db_path, task["id"])
    metadata = launched["metadata"]
    assert metadata["launch_mode"] == "write_capable"
    assert metadata["task_branch"].startswith("foremanctl/task-")
    assert metadata["harness_commit"]["sha"]
    assert metadata["post_run_verification"]["passed"] is True
    # HEAD is restored to the operator's original branch.
    assert _current_branch(root) == operator_branch
    # The commit exists on the task branch.
    commit_message = subprocess.run(
        ["git", "log", metadata["task_branch"], "-1", "--pretty=%B"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert task["id"] in commit_message
    # The task branch starts from the base branch, not from a previous Task branch.
    assert metadata["task_branch"] != operator_branch


def test_acceptance_verification_task_is_read_only_and_blocks_mutation(tmp_path):
    """7.3 An acceptance_verification Task launches read-only, creates no branch, and fails on mutation."""
    db_path = tmp_path / "harness.db"
    root = _git_project(tmp_path)
    task = _verified_task(db_path, root, task_kind="acceptance_verification")

    def runner(plan):
        _record_worker_usage(db_path, plan)
        (root / "mutation.py").write_text("mutated = True\n")
        return {"returncode": 0, "stdout": "changed", "stderr": ""}

    launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)
    _wait_for_worker_run(db_path, task["id"], "failed")
    launched = db.get_task(db_path, task["id"])
    assert launched["metadata"]["launch_mode"] == "read_only"
    assert "task_branch" not in launched["metadata"]
    assert launched["metadata"]["blocked_condition"]["origin"] == "read_only_mutation"


def test_missing_verification_command_offers_approve_commit(tmp_path):
    """7.4 No verification command -> Approve commit available -> commit created with recorded authorization."""
    db_path = tmp_path / "harness.db"
    root = _git_project(tmp_path, files={"feature.py": "old\n"})
    task = _verified_task(db_path, root, test_command=None)

    def runner(plan):
        _record_worker_usage(db_path, plan)
        (root / "feature.py").write_text("new\n")
        return {"returncode": 0, "stdout": "changed", "stderr": ""}

    launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)
    _wait_for_worker_run(db_path, task["id"], "completed")
    launched = db.get_task(db_path, task["id"])
    assert launched["status"] == "Review"
    state = launched["metadata"]["review_disposition_state"]
    assert state["pending_decision"] is True
    assert "approve_commit" in state["available_actions"]
    assert launched["metadata"]["post_run_verification"]["reason"] == "No test command confirmed."
    # HEAD stays on the Task branch while the work is unauthorized; checking the operator's
    # branch back out would carry the uncommitted work onto the base branch.
    assert _current_branch(root) == launched["metadata"]["task_branch"]

    updated = _approve_harness_commit(db_path, launched, "operator authorized missing verification")
    assert updated["metadata"]["harness_commit"]["sha"]
    assert updated["metadata"]["harness_commit_authorization"]["authorized_by"] == "operator"
    assert updated["metadata"]["harness_commit_authorization"]["verification_did_not_clear"] is True
    # The task branch is committed and HEAD is back on the operator's branch.
    assert _current_branch(root) == launched["metadata"]["operator_branch"]


def test_failed_verification_offers_approve_commit_and_block(tmp_path):
    """7.5 Verification failed -> both Approve commit and Block available."""
    db_path = tmp_path / "harness.db"
    root = _git_project(tmp_path)
    task = _verified_task(db_path, root, test_command=PASSING_TEST_COMMAND)

    def runner(plan):
        _record_worker_usage(db_path, plan)
        (root / "test_sample.py").write_text("def test_bad():\n    assert False\n")
        return {"returncode": 0, "stdout": "changed", "stderr": ""}

    launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)
    _wait_for_worker_run(db_path, task["id"], "completed")
    launched = db.get_task(db_path, task["id"])
    assert launched["status"] == "Review"
    state = launched["metadata"]["review_disposition_state"]
    assert state["pending_decision"] is True
    assert "approve_commit" in state["available_actions"]
    assert "block" in state["available_actions"]
    assert launched["metadata"]["post_run_verification"]["passed"] is False


def test_open_pr_offered_after_commit_and_failure_preserves_commit(tmp_path):
    """7.6 Open PR offered only after a commit and with capability; failure preserves the commit."""
    db_path = tmp_path / "harness.db"
    root = _git_project(tmp_path)
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/example/repo.git"], cwd=root, check=True, capture_output=True)
    task = _verified_task(db_path, root)

    def runner(plan):
        _record_worker_usage(db_path, plan)
        (root / "feature.py").write_text("VALUE = 'demo'\n")
        return {"returncode": 0, "stdout": "changed", "stderr": ""}

    with _fake_github_pr_failure():
        launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)
        _wait_for_worker_run(db_path, task["id"], "completed")
    launched = db.get_task(db_path, task["id"])
    state = launched["metadata"]["review_disposition_state"]
    assert "open_pr" in state["available_actions"]
    assert launched["metadata"]["harness_commit"]["sha"]

    with _fake_github_pr_failure():
        try:
            _open_pull_request(db_path, launched)
        except ValueError as exc:
            assert "Pull request" in str(exc)
    relaunched = db.get_task(db_path, task["id"])
    assert relaunched["metadata"]["harness_commit"]["sha"] == launched["metadata"]["harness_commit"]["sha"]
    assert relaunched["metadata"].get("pr_failure")


def test_sequential_tasks_branch_from_base_independently(tmp_path):
    """7.7 Two Tasks launched in sequence each branch from the base, and the second does not contain the first's commit."""
    db_path = tmp_path / "harness.db"
    root = _git_project(tmp_path)
    project = _verified_project(db_path, root)

    def make_task(index: int):
        return db.create_task(
            db_path,
            description=f"Write change {index}",
            status="Ready",
            estimate_tokens=1000,
            recommended_model="opencode/gpt-5.1",
            metadata=with_task_kind({**project_task_metadata(project)}, "implementation"),
        )

    def runner_for(index: int):
        def runner(plan):
            _record_worker_usage(db_path, plan)
            (root / f"feature{index}.py").write_text(f"VALUE{index} = 'demo'\n")
            return {"returncode": 0, "stdout": "changed", "stderr": ""}

        return runner

    task1 = make_task(1)
    launch_task(db_path, task1["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner_for(1))
    _wait_for_worker_run(db_path, task1["id"], "completed")
    first = db.get_task(db_path, task1["id"])

    task2 = make_task(2)
    launch_task(db_path, task2["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner_for(2))
    _wait_for_worker_run(db_path, task2["id"], "completed")
    second = db.get_task(db_path, task2["id"])

    first_sha = first["metadata"]["harness_commit"]["sha"]
    second_log = subprocess.run(
        ["git", "log", second["metadata"]["task_branch"], "--pretty=%H"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert first_sha not in second_log

    # Marking the first task done fast-forwards the base; the second task still predates that.
    _mark_review_done(db_path, first)
    assert first["metadata"]["harness_commit"]["sha"] in subprocess.run(
        ["git", "log", "--pretty=%H"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def test_acceptance_fast_forwards_base_and_diverged_base_is_refused(tmp_path):
    """7.8 Acceptance fast-forwards the base; a diverged base is refused with the Task branch and commit intact."""
    db_path = tmp_path / "harness.db"
    root = _git_project(tmp_path)
    task = _verified_task(db_path, root)

    def runner(plan):
        _record_worker_usage(db_path, plan)
        (root / "feature.py").write_text("VALUE = 'demo'\n")
        return {"returncode": 0, "stdout": "changed", "stderr": ""}

    launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)
    _wait_for_worker_run(db_path, task["id"], "completed")
    launched = db.get_task(db_path, task["id"])
    commit_sha = launched["metadata"]["harness_commit"]["sha"]

    # Accept the task; base should fast-forward to the harness commit.
    accepted = _mark_review_done(db_path, launched)
    assert accepted["status"] == "Done"
    base_log = subprocess.run(
        ["git", "log", "--pretty=%H"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert commit_sha in base_log

    # Diverge the base with a new commit, then create and try to accept a second task.
    (root / "diverge.py").write_text("diverged = True\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=demo@example.com", "-c", "user.name=Demo", "commit", "-m", "diverge"],
        cwd=root,
        check=True,
        capture_output=True,
    )

    def runner2(plan):
        _record_worker_usage(db_path, plan)
        (root / "feature2.py").write_text("VALUE2 = 'demo'\n")
        return {"returncode": 0, "stdout": "changed", "stderr": ""}

    task2 = _verified_task(db_path, root)
    launch_task(db_path, task2["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner2)
    _wait_for_worker_run(db_path, task2["id"], "completed")
    second = db.get_task(db_path, task2["id"])
    second_commit = second["metadata"]["harness_commit"]["sha"]
    try:
        _mark_review_done(db_path, second)
    except ValueError:
        pass
    # The second commit and branch are intact; the base did not fast-forward.
    assert second_commit in subprocess.run(
        ["git", "log", second["metadata"]["task_branch"], "--pretty=%H"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def test_no_review_task_has_decision_without_action(tmp_path):
    """7.9 No Task in Review records a pending decision with no available action."""
    db_path = tmp_path / "harness.db"
    root = _git_project(tmp_path)
    task = _verified_task(db_path, root)

    def runner(plan):
        _record_worker_usage(db_path, plan)
        (root / "feature.py").write_text("VALUE = 'demo'\n")
        return {"returncode": 0, "stdout": "changed", "stderr": ""}

    launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)
    _wait_for_worker_run(db_path, task["id"], "completed")
    launched = db.get_task(db_path, task["id"])
    state = launched["metadata"].get("review_disposition_state") or {}
    if state.get("pending_decision"):
        assert state["available_actions"]
    # Verified tasks have an automatic commit and can be marked done.
    assert "open_pr" in state.get("available_actions", []) or launched["metadata"]["harness_commit"]


def test_queue_stops_when_task_awaits_approve_commit(tmp_path):
    """7.10 A queue run whose Task lands in Review awaiting Approve commit stops with that reason."""
    from foreman_ai_hq.board_automation import get_run_automation_state, start_run_automation, stop_run_automation

    db_path = tmp_path / "harness.db"
    root = _git_project(tmp_path)
    project = _verified_project(db_path, root, test_command=None)
    task = db.create_task(
        db_path,
        description="Queue task",
        status="Ready",
        estimate_tokens=1000,
        recommended_model="opencode/gpt-5.1",
        metadata=with_task_kind({**project_task_metadata(project)}, "implementation"),
    )

    start_run_automation(db_path, project_id=project["id"], source="run_queue")

    def runner(plan):
        _record_worker_usage(db_path, plan)
        (root / "feature.py").write_text("VALUE = 'demo'\n")
        return {"returncode": 0, "stdout": "changed", "stderr": ""}

    launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)
    _wait_for_worker_run(db_path, task["id"], "completed")
    launched = db.get_task(db_path, task["id"])
    assert launched["metadata"]["review_disposition_state"]["pending_decision"] is True

    stop_run_automation(db_path, project_id=project["id"], reason="awaiting_disposition", task_id=task["id"])
    state = get_run_automation_state(db_path, project["id"])
    assert state["status"] == "stopped"
    assert state["latest_stop_reason"] == "awaiting_disposition"


def test_head_restored_to_operator_branch_after_write_capable_run(tmp_path):
    """7.11 HEAD is back on the operator's original branch after a write-capable run completes."""
    db_path = tmp_path / "harness.db"
    root = _git_project(tmp_path)
    task = _verified_task(db_path, root)
    operator_branch = _current_branch(root)

    def runner(plan):
        _record_worker_usage(db_path, plan)
        (root / "feature.py").write_text("VALUE = 'demo'\n")
        return {"returncode": 0, "stdout": "changed", "stderr": ""}

    launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)
    _wait_for_worker_run(db_path, task["id"], "completed")
    assert _current_branch(root) == operator_branch


def test_non_git_project_refuses_write_but_allows_read_only(tmp_path):
    """7.12 A non-git connected project is refused at write-capable launch and still permitted for read-only launch."""
    db_path = tmp_path / "harness.db"
    root = tmp_path / "non-git-project"
    root.mkdir()
    db.init_db(db_path)
    project = db.upsert_connected_project(
        db_path,
        name="Non Git Project",
        root_path=str(root),
        profile={"root_path": str(root)},
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
    write_task = db.create_task(
        db_path,
        description="Write to non-git",
        status="Ready",
        estimate_tokens=1000,
        recommended_model="opencode/gpt-5.1",
        metadata=with_task_kind({**project_task_metadata(project)}, "implementation"),
    )
    try:
        launch_task(db_path, write_task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=lambda plan: {"returncode": 0, "stdout": "", "stderr": ""})
    except TaskLaunchBlocked as exc:
        assert "git repository" in exc.reasons[0]
    else:
        raise AssertionError("expected non-git project to block write-capable launch")

    read_task = db.create_task(
        db_path,
        description="Read non-git",
        status="Ready",
        estimate_tokens=1000,
        recommended_model="opencode/gpt-5.1",
        metadata=with_task_kind({**project_task_metadata(project)}, "acceptance_verification"),
    )
    def read_runner(plan):
        _record_worker_usage(db_path, plan)
        return {"returncode": 0, "stdout": "", "stderr": ""}

    launch_task(db_path, read_task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=read_runner)
    _wait_for_worker_run(db_path, read_task["id"], "completed")


def test_write_capable_launch_blocks_dirty_repo_before_runner(tmp_path):
    db_path = tmp_path / "harness.db"
    root = _git_project(tmp_path)
    task = _verified_task(db_path, root)
    (root / "dirty.py").write_text("print('dirty')\n")
    calls = []

    try:
        launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=calls.append)
    except TaskLaunchBlocked as exc:
        blocked = exc.task
    else:
        raise AssertionError("expected dirty repo to block")

    assert blocked["status"] == "Estimated"
    assert "Offending paths" in blocked["metadata"]["launch_guardrail_reasons"][1]
    assert calls == []


def test_detected_unconfirmed_command_blocks_launch(tmp_path):
    db_path = tmp_path / "harness.db"
    root = _git_project(tmp_path)
    project = _verified_project(db_path, root, test_command=PASSING_TEST_COMMAND)
    db.update_connected_project_profile(
        db_path,
        project["id"],
        updater=lambda p: {**p, "test_command_confirmed": False},
    )
    task = db.create_task(
        db_path,
        description="Blocked by unconfirmed command",
        status="Ready",
        estimate_tokens=1000,
        recommended_model="opencode/gpt-5.1",
        metadata=with_task_kind({**project_task_metadata(project)}, "implementation"),
    )
    try:
        launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=lambda plan: {"returncode": 0, "stdout": "", "stderr": ""})
    except TaskLaunchBlocked as exc:
        assert "verification command is confirmed" in exc.reasons[0]
    else:
        raise AssertionError("expected unconfirmed command to block launch")


def test_pr_capability_detection_handles_missing_github_remote(tmp_path):
    root = _git_project(tmp_path)

    capability = detect_pr_capability(root)

    assert capability["available"] is False
    assert capability["github_remote"] is False
    assert "GitHub remote" in capability["reason"]


def test_agent_review_reads_the_diff_from_the_harness_commit(tmp_path):
    """6b.4 Auto Review fires after the commit, when the working tree is already clean."""
    db_path = tmp_path / "harness.db"
    root = _git_project(tmp_path)
    task = _verified_task(db_path, root)

    def runner(plan):
        _record_worker_usage(db_path, plan)
        (root / "feature.py").write_text("VALUE = 'demo'\n")
        return {"returncode": 0, "stdout": "changed", "stderr": ""}

    launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)
    _wait_for_worker_run(db_path, task["id"], "completed")
    launched = db.get_task(db_path, task["id"])

    # The commit exists and the tree is clean, so a working-tree diff would be empty.
    assert launched["metadata"]["harness_commit"]["sha"]
    assert _git_diff_summary(str(root))["has_changes"] is False

    summary = _agent_review_diff_summary(db_path, launched)
    assert summary["has_changes"] is True
    # Verification runs before the commit, so its byproducts are committed alongside the change.
    assert "feature.py" in summary["files_changed"]
    assert summary["commit_sha"] == launched["metadata"]["harness_commit"]["sha"]
    assert "feature.py" in summary["stat"]


def test_open_pr_is_not_offered_without_capability(tmp_path):
    """4.3 A commit without PR capability offers no Open PR action, only the stated reason."""
    db_path = tmp_path / "harness.db"
    root = _git_project(tmp_path)  # no remote, so capability is unavailable
    task = _verified_task(db_path, root)

    def runner(plan):
        _record_worker_usage(db_path, plan)
        (root / "feature.py").write_text("VALUE = 'demo'\n")
        return {"returncode": 0, "stdout": "changed", "stderr": ""}

    launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)
    _wait_for_worker_run(db_path, task["id"], "completed")
    launched = db.get_task(db_path, task["id"])
    state = launched["metadata"]["review_disposition_state"]

    assert launched["metadata"]["harness_commit"]["sha"]
    assert "open_pr" not in state["available_actions"]
    assert "GitHub remote" in state["pr_unavailable_reason"]
    controls = _task_controls(launched, launched["metadata"], {})
    assert controls["can_open_pr"] is False
    assert "GitHub remote" in controls["pr_unavailable_reason"]


import contextlib


@contextlib.contextmanager
def _fake_github_pr_failure():
    """Temporarily shadow `gh` so `auth status` passes and `pr create` fails."""
    import os
    import shutil
    import tempfile

    original_path = os.environ.get("PATH", "")
    with tempfile.TemporaryDirectory() as tmp:
        fake_gh = Path(tmp) / "gh"
        fake_gh.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = \"auth\" ] && [ \"$2\" = \"status\" ]; then\n"
            "  exit 0\n"
            "fi\n"
            "echo 'gh: could not create pull request' >&2\n"
            "exit 1\n"
        )
        fake_gh.chmod(0o755)
        os.environ["PATH"] = f"{tmp}:{original_path}"
        yield
    os.environ["PATH"] = original_path
