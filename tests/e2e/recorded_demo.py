from __future__ import annotations

import json
import os
import secrets
import subprocess
import tempfile
import threading
import time
import types
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD_DIR = REPO_ROOT / "src" / "foreman_ai_hq" / "static" / "react"
REACT_BUILD_LOCK = threading.Lock()
REACT_BUILD_AVAILABLE = threading.Event()

DEMO_PROJECT_NAME = "DEMO_999_mdlink_project"
DEMO_TASK_ID = "DEMO_999_TASK_001"
DEMO_SESSION_ID = "session_2099_demo_claude"
DEMO_ADAPTER_ID = "claude_code"
DEMO_MODEL = "claude-sonnet-4-6"
# Seeded explicitly because there is no code default for the Orchestrator Model:
# a Recorded Demo Run configures it as ordinary scenario state, provider-qualified
# like any value pi's inventory would offer.
DEMO_ORCHESTRATOR_MODEL = "anthropic/claude-sonnet-4-6"
DEMO_SENTINEL = "DEMO streamed progress 2099"


def _seed_orchestrator_inventory(database_path) -> None:
    """Seed pi's discovery evidence the way a real refresh would write it.

    The readiness gate reads this row, so a demo passes it through the production
    code path rather than through an environment bypass that would weaken it.
    """
    from foreman_ai_hq import db
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
                "models": [DEMO_ORCHESTRATOR_MODEL],
                "discovered_at": "2099-01-01T00:00:00+00:00",
                "returncode": 0,
                "reasons": [],
            },
            "verification": {
                "model": DEMO_ORCHESTRATOR_MODEL,
                "passed": True,
                "verified_at": "2099-01-01T00:00:00+00:00",
                "sentinel_matched": True,
                "token_recorded": True,
                "reasons": [],
            },
        },
    )
DEMO_PORTAL_TOKEN_ENV = "DEMO_999_PORTAL_TOKEN"


def _react_sources_newest_mtime() -> float:
    """Return the newest mtime across inputs that affect the built React shell."""
    frontend = REPO_ROOT / "frontend"
    newest = 0.0
    for path in frontend.rglob("*"):
        if not path.is_file():
            continue
        if "node_modules" in path.parts or path.parts[-1].startswith("."):
            continue
        newest = max(newest, path.stat().st_mtime)
    return newest


def _react_build_is_stale() -> bool:
    """Report whether the built shell predates any frontend source change.

    A build that merely exists is not enough: serving a bundle older than the
    sources under test would silently verify stale UI.
    """
    index = BUILD_DIR / "index.html"
    if not index.is_file():
        return True
    return index.stat().st_mtime < _react_sources_newest_mtime()


def _ensure_react_build() -> None:
    """Build the React shell once per process, and whenever the build is stale."""
    with REACT_BUILD_LOCK:
        if REACT_BUILD_AVAILABLE.is_set() and not _react_build_is_stale():
            return
        if not _react_build_is_stale():
            REACT_BUILD_AVAILABLE.set()
            return
        subprocess.run(
            ["npm", "--prefix", "frontend", "run", "build"],
            cwd=str(REPO_ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        REACT_BUILD_AVAILABLE.set()


def _synthetic_repo(root: Path) -> None:
    """Create a minimal, synthetic git project for the demo run."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# DEMO 999 mdlink project\n\nA synthetic fixture.\n")
    (root / "demo.py").write_text("print('DEMO 999 mdlink fixture')\n")
    subprocess.run(["git", "init"], cwd=str(root), check=True, capture_output=True, text=True)


def _synthetic_stream_runner(
    entered: threading.Event,
    stream_more: threading.Event,
    provisional_emitted: threading.Event,
    release: threading.Event,
    finished: threading.Event,
) -> Callable[[Any, Callable[[str], None]], Any]:
    """Return a stand-in for `foreman_ai_hq.task_launch.streaming_runner`.

    The provisional usage line is held behind `stream_more` on purpose. Anything
    emitted before the launch action's board reload would also arrive in the
    board payload, so a browser assertion on it could pass without the live
    event feed working at all. Releasing it only after the board has settled
    leaves the incremental `since_id` projection as the sole delivery path.
    """

    def runner(plan: Any, on_event: Callable[[str], None]) -> Any:
        # Claude Code `--output-format stream-json` shapes. Unlike OpenCode,
        # Claude's own result event carries top-level `usage`, so the provisional
        # line below is a real wire shape rather than a harness-facing invention.
        text_line = json.dumps(
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": DEMO_SENTINEL}]},
            }
        )
        # Deliberately carries no session_id, no modelUsage, and no cost, so
        # `parse_native_usage_evidence` cannot bind it and the final result event
        # below stays authoritative (design D6).
        provisional_usage_line = json.dumps(
            {
                "type": "result",
                "usage": {"input_tokens": 12, "output_tokens": 3},
            }
        )

        stdout_parts: list[str] = [text_line]
        on_event(text_line + "\n")

        entered.set()

        if not stream_more.wait(timeout=60):
            finished.set()
            raise TimeoutError("Synthetic runner stream_more timed out")

        stdout_parts.append(provisional_usage_line)
        on_event(provisional_usage_line + "\n")
        provisional_emitted.set()

        if not release.wait(timeout=60):
            finished.set()
            raise TimeoutError("Synthetic runner release timed out")

        # Authoritative completion evidence: session-bound, model-bound, costed.
        # Cache counters are zero so the operator-facing actual stays 12 + 3.
        finish_line = json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "session_id": DEMO_SESSION_ID,
                "total_cost_usd": 0.01,
                "usage": {
                    "input_tokens": 12,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "output_tokens": 3,
                },
                "modelUsage": {
                    DEMO_MODEL: {
                        "inputTokens": 12,
                        "outputTokens": 3,
                        "cacheReadInputTokens": 0,
                        "cacheCreationInputTokens": 0,
                        "costUSD": 0.01,
                    }
                },
            }
        )
        stdout_parts.append(finish_line)
        on_event(finish_line + "\n")

        full_stdout = "\n".join(stdout_parts) + "\n"
        finished.set()
        return subprocess.CompletedProcess(
            args=getattr(plan, "command", []),
            returncode=0,
            stdout=full_stdout,
            stderr="",
        )

    return runner


@dataclass
class RecordedDemo:
    """Spin up an ephemeral Foreman AI HQ instance for the recorded demo.

    The fixture builds the React shell, starts uvicorn on a loopback port,
    and seeds a synthetic project, verified Claude Code adapter, accepted task,
    and deterministic budget. The worker runner is monkey-patched so the
    server-side launch produces synthetic Claude `stream-json` events instead of
    invoking the real `claude` CLI. No provider, API key, or CLI is required.
    """

    database_path: Path = field(init=False)
    project_id: str = field(init=False)
    task_id: str = DEMO_TASK_ID
    base_url: str = field(init=False)
    portal_token: str = field(default_factory=lambda: f"demo_{secrets.token_urlsafe(16)}")
    entered: threading.Event = field(default_factory=threading.Event)
    stream_more: threading.Event = field(default_factory=threading.Event)
    provisional_emitted: threading.Event = field(default_factory=threading.Event)
    release: threading.Event = field(default_factory=threading.Event)
    finished: threading.Event = field(default_factory=threading.Event)
    outcome_done: threading.Event = field(default_factory=threading.Event)

    _temp_dir: tempfile.TemporaryDirectory | None = field(default=None, repr=False)
    _server: Any = field(default=None, repr=False)
    _server_thread: threading.Thread | None = field(default=None, repr=False)
    _original_streaming_runner: Any = field(default=None, repr=False)
    _original_apply_outcome: Any = field(default=None, repr=False)
    _original_react_build_dir: Callable[[], Path] | None = field(default=None, repr=False)
    _original_planning_start: Any = field(default=None, repr=False)
    _project_root: Path = field(init=False)

    def __enter__(self) -> "RecordedDemo":
        _ensure_react_build()

        self._temp_dir = tempfile.TemporaryDirectory(prefix="foreman_demo_")
        temp_path = Path(self._temp_dir.name)
        self.database_path = temp_path / "harness.db"
        self._project_root = temp_path / DEMO_PROJECT_NAME

        _synthetic_repo(self._project_root)

        # Import and patch the streaming runner before the app imports routes.
        import foreman_ai_hq.task_launch as task_launch

        self._original_streaming_runner = task_launch.streaming_runner
        task_launch.streaming_runner = _synthetic_stream_runner(
            self.entered,
            self.stream_more,
            self.provisional_emitted,
            self.release,
            self.finished,
        )

        # Observation-only hook (design D1): this wrapper calls straight through
        # and returns the original result, so no governed behavior is
        # substituted. It only signals when the worker-run outcome has been
        # applied, so browser tests can reload the board without racing the
        # backend. The Worker subprocess seam above remains the sole
        # substitution.
        self._original_apply_outcome = task_launch._apply_worker_run_outcome

        def _apply_outcome_and_signal(*args: Any, **kwargs: Any) -> None:
            try:
                return self._original_apply_outcome(*args, **kwargs)
            finally:
                self.outcome_done.set()

        task_launch._apply_worker_run_outcome = _apply_outcome_and_signal

        # Tests may monkeypatch react_build_dir to a missing build; restore it
        # so the server can serve the built React shell.
        from foreman_ai_hq.routes import react_shell as _react_shell

        self._original_react_build_dir = _react_shell.react_build_dir
        _react_shell.react_build_dir = lambda: BUILD_DIR

        # Provide the demo token through the environment so the login form works.
        os.environ[DEMO_PORTAL_TOKEN_ENV] = self.portal_token

        self._seed_data()

        from foreman_ai_hq.app import create_app
        from foreman_ai_hq.settings import Settings

        guardrails_path = REPO_ROOT / "guardrails.yaml"
        if not guardrails_path.is_file():
            guardrails_path = REPO_ROOT / "src" / "foreman_ai_hq" / "defaults" / "guardrails.yaml"

        settings = Settings(
            database_path=self.database_path,
            guardrails_path=guardrails_path,
            portal_token_env=DEMO_PORTAL_TOKEN_ENV,
            portal_auth_required=True,
            local_runner_enabled=True,
            timezone="UTC",
            operator_config={},
            orchestrator_model=DEMO_ORCHESTRATOR_MODEL,
        )
        _seed_orchestrator_inventory(self.database_path)
        app = create_app(settings)
        self._seed_llm_client(app)

        import uvicorn

        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=0,
            loop="asyncio",
            log_level="warning",
            access_log=False,
        )
        self._server = uvicorn.Server(config)
        self._server.capture_signals = lambda: nullcontext()  # type: ignore[attr-defined]

        self._server_thread = threading.Thread(target=self._server.run, daemon=True)
        self._server_thread.start()

        # Wait for uvicorn to bind and start accepting connections.
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if getattr(self._server, "started", False):
                servers = getattr(self._server, "servers", [])
                if servers and servers[0].sockets:
                    break
            time.sleep(0.05)
        else:
            raise RuntimeError("uvicorn server failed to start")

        port = self._server.servers[0].sockets[0].getsockname()[1]
        self.base_url = f"http://127.0.0.1:{port}"

        return self

    def __exit__(self, *exc: Any) -> None:
        # Release every gate unconditionally so a failed assertion cannot leave
        # the runner thread blocked until its own timeout expires.
        self.stream_more.set()
        self.release.set()
        if self._server is not None:
            self._server.should_exit = True
            self._server_thread.join(timeout=5)
            if self._server_thread.is_alive():
                self._server.force_exit = True
                self._server_thread.join(timeout=2)

        if self._original_streaming_runner is not None:
            import foreman_ai_hq.task_launch as task_launch

            task_launch.streaming_runner = self._original_streaming_runner

        if self._original_apply_outcome is not None:
            import foreman_ai_hq.task_launch as task_launch

            task_launch._apply_worker_run_outcome = self._original_apply_outcome

        if self._original_react_build_dir is not None:
            from foreman_ai_hq.routes import react_shell as _react_shell

            _react_shell.react_build_dir = self._original_react_build_dir

        if self._original_planning_start is not None:
            import foreman_ai_hq.routes.planning_conversation as planning_conversation

            planning_conversation.PlanningConversationRegistry.start = self._original_planning_start

        os.environ.pop(DEMO_PORTAL_TOKEN_ENV, None)

        if self._temp_dir is not None:
            self._temp_dir.cleanup()

    def _seed_llm_client(self, app) -> None:
        """Subclasses may inject a fake LLM client before the server starts."""
        import foreman_ai_hq.db as db
        import foreman_ai_hq.pi_adapter as pi_adapter
        import foreman_ai_hq.routes.planning_conversation as planning_conversation
        import time

        app.state.orchestrator_job_runner = self._fake_orchestrator

        # Replace the planning-conversation start so the demo never needs a real
        # pi CLI; only the session id and a no-op conversation handle are used.
        # The lifespan will create a new PlanningConversationRegistry instance, so
        # we patch the class method rather than a single instance.
        self._original_planning_start = planning_conversation.PlanningConversationRegistry.start

        def _fake_start(self, project_id, database_path, model, cwd=None, timeout=60):
            with self._lock:
                live = self._live.get(project_id)
                if live is not None and live.conv.proc.poll() is None and live.model == model:
                    return live.planning_session_id

            session, _ = db.create_planning_session(
                database_path,
                task_description="Demo planning conversation",
                model=model,
                tracking_mode="native_usage",
            )
            fake_proc = types.SimpleNamespace(poll=lambda: None)
            fake_conv = types.SimpleNamespace(
                session=session,
                proc=fake_proc,
                prompt=lambda text: ("ok", "end_turn"),
                cancel=lambda: None,
                close=lambda: None,
            )
            with self._lock:
                self._live[project_id] = planning_conversation.LiveConversation(
                    conv=fake_conv,
                    planning_session_id=session["id"],
                    model=model,
                    last_used_at=time.monotonic(),
                )
            return session["id"]

        planning_conversation.PlanningConversationRegistry.start = _fake_start

    async def _fake_orchestrator(self, database_path, *, instructions, input_payload, model, persona_filename, extension_filename, submit_tool, usage_kind, task_description, result_validator=None, session_id=None, timeout=None, **kwargs):
        """Deterministic orchestrator/estimator that lets the chat pane create a Task."""
        import foreman_ai_hq.db as db
        import foreman_ai_hq.pi_adapter as pi_adapter

        session = db.create_session(
            database_path,
            task_description=task_description,
            model=model,
            session_key_hash="x" * 64,
            guardrail_overrides={},
            status="running",
        )
        session = db.update_session_status(database_path, session["id"], "completed")

        if persona_filename == "intake.md":
            raw = {"decision": "single_task", "reason": "Demo fixture judged as a single small task."}
        elif persona_filename == "estimator.md":
            raw = {
                "drivers": {"files_to_read": 1, "files_to_modify": 0, "expected_turns": 1, "needs_test_run": False},
                "shadow_token_estimate": 1500,
                "complexity": "simple",
                "confidence": 0.9,
                "investigation_recommended": False,
                "rationale": "Demo fixture estimate.",
                "assumptions": [],
                "risk_flags": [],
                "budget_note": "demo",
                "source": "llm",
            }
        else:
            raw = {}

        validated = result_validator(raw) if result_validator else raw
        return pi_adapter.PiStructuredJobResult(
            arguments=raw,
            validated=validated,
            session=session,
            args=[],
        )

    def _seed_data(self) -> None:
        import foreman_ai_hq.db as db
        import foreman_ai_hq.execution_backend as execution_backend
        from foreman_ai_hq.project_context import project_task_metadata
        from foreman_ai_hq.task_kind import with_task_kind

        db.init_db(self.database_path)
        # After init_db, so the demo's own Orchestrator Model is the one that survives.
        _seed_orchestrator_inventory(self.database_path)

        adapter = db.get_worker_adapter(self.database_path, DEMO_ADAPTER_ID)
        config = dict(adapter.get("config") or {})
        config["allowed_models_configured"] = True
        db.update_worker_adapter(
            self.database_path,
            DEMO_ADAPTER_ID,
            config=config,
            supported_models=[DEMO_MODEL],
            is_default=True,
        )
        db.mark_worker_adapter_verification(
            self.database_path,
            DEMO_ADAPTER_ID,
            verified=True,
            evidence={
                "tracking_mode": "native_usage",
                "tracking_authoritative": True,
                "synthetic_fixture": True,
            },
        )

        profile = execution_backend.detect_project_profile(self._project_root)
        project = db.upsert_connected_project(
            self.database_path,
            name=DEMO_PROJECT_NAME,
            root_path=str(self._project_root),
            profile=profile,
            capability={
                "state": "launch_ready",
                "label": "Launch-ready via Local Runner",
                "backend": "local_runner",
                "reasons": [],
                "can_launch": True,
                "can_analyze": True,
            },
            backend_id="local_runner",
        )
        self.project_id = project["id"]

        db.set_token_budget_settings(
            self.database_path,
            daily_cap_tokens=100_000,
            session_cap_tokens=50_000,
        )

        task_description = "DEMO 999 read-only md link check fixture"
        assert DEMO_SENTINEL not in task_description
        task = db.create_task(
            self.database_path,
            task_id=DEMO_TASK_ID,
            description=task_description,
            status="Estimated",
            estimate_tokens=1_500,
            recommended_model=DEMO_MODEL,
            # Launch mode follows the canonical Task kind; the old `read_only` metadata
            # flag is ignored, so the demo declares an acceptance-verification Task.
            metadata=with_task_kind(
                {
                    "synthetic_fixture": True,
                    **project_task_metadata(project),
                },
                "acceptance_verification",
            ),
        )
        self.task_id = task["id"]

    def set_task_kind_acceptance_verification(self, task_id: str) -> None:
        """Test helper to flip a chat-created task to the read-only kind expected by the demo run."""
        import foreman_ai_hq.db as db
        from foreman_ai_hq.task_kind import with_task_kind

        current = db.get_task(self.database_path, task_id)
        db.update_task(
            self.database_path,
            task_id,
            {"metadata": with_task_kind(current.get("metadata", {}), "acceptance_verification")},
        )
