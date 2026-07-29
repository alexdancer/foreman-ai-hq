import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from foreman_ai_hq import db

# The readiness gate refuses orchestration unless a provider-qualified model is
# configured *and* present in pi's persisted discovery evidence. Almost every test
# that drives a route needs that true, and almost none of them are about the gate,
# so it is seeded as scenario state the way a Recorded Demo Run seeds it.
TEST_ORCHESTRATOR_MODEL = "anthropic/claude-sonnet-5"


def seed_orchestrator_inventory(database_path, model: str = TEST_ORCHESTRATOR_MODEL) -> None:
    """Write the evidence a successful `pi --list-models` refresh would write."""
    from foreman_ai_hq.pi_adapter import (
        ORCHESTRATOR_STATUS_RECORD_ID,
        ORCHESTRATOR_STATUS_RECORD_NAME,
    )

    db.upsert_execution_backend_status(
        database_path,
        ORCHESTRATOR_STATUS_RECORD_ID,
        name=ORCHESTRATOR_STATUS_RECORD_NAME,
        online=True,
        details={
            "model_discovery": {
                "state": "ready",
                "models": [model],
                "discovered_at": "2099-01-01T00:00:00+00:00",
                "returncode": 0,
                "reasons": [],
            }
        },
    )


# `implementation` is the default Task kind and launches write-capable, which requires a
# git repository with a clean tree, a confirmed verification command, and a confirmed base
# branch. Any fixture that launches a Task needs that state, so it is built in one place.
PASSING_TEST_COMMAND = f"{shlex.quote(sys.executable)} -c pass"


def init_git_project(root: Path, *, base_branch: str = "main") -> Path:
    """Make `root` a committed git repository whose test artifacts stay ignored."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if (root / ".git").exists():
        return root
    # Databases, caches and worker output live inside tmp roots; ignoring them keeps the
    # working tree clean so the launch guardrail sees the state a real project has.
    (root / ".gitignore").write_text("*.db\n*.db-*\n*.sqlite*\n__pycache__/\n.pytest_cache/\n")
    git = ["git", "-c", "user.email=test@example.invalid", "-c", "user.name=Foreman Test"]
    subprocess.run(["git", "init", "-b", base_branch], cwd=root, check=True, capture_output=True)
    subprocess.run([*git, "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run([*git, "commit", "-m", "test fixture"], cwd=root, check=True, capture_output=True)
    return root


def git_project_profile(root: Path, *, base_branch: str = "main", **overrides) -> dict:
    """Profile for a launch-ready connected project, with git state to match."""
    init_git_project(root, base_branch=base_branch)
    profile = {
        "name": Path(root).name,
        "root_path": str(Path(root).resolve()),
        "test_command": PASSING_TEST_COMMAND,
        "test_command_confirmed": True,
        "base_branch": base_branch,
        "base_branch_confirmed": True,
    }
    profile.update(overrides)
    return profile


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "unconfigured_orchestrator: leave the Orchestrator Model unconfigured"
    )
    config.addinivalue_line(
        "markers", "raw_orchestrator_env: do not inject FOREMAN_AI_HQ_ORCHESTRATOR_MODEL"
    )


@pytest.fixture(autouse=True)
def _configured_orchestrator(request, monkeypatch):
    if "unconfigured_orchestrator" in request.keywords:
        monkeypatch.delenv("FOREMAN_AI_HQ_ORCHESTRATOR_MODEL", raising=False)
        return
    if "raw_orchestrator_env" not in request.keywords:
        # The single surviving override, so tests configure the model the same way
        # a headless operator does.
        monkeypatch.setenv("FOREMAN_AI_HQ_ORCHESTRATOR_MODEL", TEST_ORCHESTRATOR_MODEL)

    # Every test database is created through `db.init_db`, so seeding there covers
    # the 40-odd files that each build their own without restating it in all of them.
    real_init_db = db.init_db

    def init_db_with_inventory(path, *args, **kwargs):
        result = real_init_db(path, *args, **kwargs)
        # Never overwrite evidence a test seeded itself. `init_db` runs again on
        # TestClient startup, so seeding unconditionally would clobber a test's own
        # model depending on call order.
        from foreman_ai_hq.pi_adapter import persisted_orchestrator_discovery

        if not persisted_orchestrator_discovery(path):
            seed_orchestrator_inventory(path)
        return result

    monkeypatch.setattr(db, "init_db", init_db_with_inventory)


@pytest.fixture(autouse=True)
def _test_portal_token(monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", "test-portal-token")


@pytest.fixture(autouse=True)
def _react_build_absent(tmp_path, monkeypatch):
    # The built React shell lives in a git-ignored directory, so its presence
    # depends on the developer's machine. Pin every test to "build absent";
    # tests that need the built shell monkeypatch react_build_dir themselves.
    from foreman_ai_hq.routes import react_shell

    monkeypatch.setattr(react_shell, "react_build_dir", lambda: tmp_path / "no-react-build")


def pytest_runtest_teardown(item, nextitem):
    # `foremanctl` mutates `os.environ` directly; pytest's monkeypatch cannot revert
    # values set by code under test. Purge the CLI env variables after every test
    # so leaked `serve`/`check` state does not break later route tests.
    for name in [
        "TOKEN_TRACKER_PORTAL_AUTH_REQUIRED",
        "TOKEN_TRACKER_LOCAL_RUNNER",
        "TOKEN_TRACKER_DATABASE_PATH",
        "TOKEN_TRACKER_GUARDRAILS_PATH",
        "TOKEN_TRACKER_PORTAL_TOKEN_ENV",
        "FOREMAN_AI_HQ_ORCHESTRATOR_MODEL",
        "FOREMAN_AI_HQ_CONTROL_PROVIDER",
        "FOREMAN_AI_HQ_CONTROL_MODEL",
        "FOREMAN_AI_HQ_CONTROL_BASE_URL",
        "FOREMAN_AI_HQ_CONTROL_API_KEY_ENV",
        "FOREMAN_AI_HQ_CONTROL_API_KEY",
    ]:
        os.environ.pop(name, None)
