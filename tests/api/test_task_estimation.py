import json
import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from foreman_ai_hq import db
from tests.conftest import seed_orchestrator_inventory
from foreman_ai_hq.app import create_app
from foreman_ai_hq.project_context import project_task_metadata
from foreman_ai_hq.routes import tasks as task_routes
from foreman_ai_hq.settings import Settings
from foreman_ai_hq.task_launch import refresh_task_from_session
from tests.conftest import git_project_profile
from tests.fake_orchestrator import FakeOrchestratorJobRunner


ROOT = Path(__file__).resolve().parents[2]
PORTAL_TOKEN = "test-portal-token"


def _auth_headers():
    return {"Authorization": f"Bearer {PORTAL_TOKEN}"}


def _wait_for_worker_run(db_path: Path, task_id: str, status: str | None = None):
    deadline = time.time() + 2
    while time.time() < deadline:
        runs = db.list_worker_runs(db_path, task_id=task_id)
        if runs and (status is None or runs[-1]["status"] == status):
            return runs[-1]
        time.sleep(0.01)
    raise AssertionError("worker run did not reach expected status")


def _client(tmp_path):
    settings = Settings(database_path=tmp_path / "harness.db", guardrails_path=ROOT / "guardrails.yaml")
    db.init_db(settings.database_path)
    app = create_app(settings)
    project_root = tmp_path / "connected-project"
    project_root.mkdir(exist_ok=True)
    db.upsert_connected_project(
        settings.database_path,
        name=project_root.name,
        root_path=str(project_root.resolve()),
        profile=git_project_profile(project_root, name=project_root.name),
        capability={"state": "launch_ready", "can_launch": True},
    )
    return TestClient(app)


class FakeSequentialLLM:
    def __init__(self, contents):
        self.contents = list(contents)
        self.requests = []
        self.usage = {"prompt_tokens": 111, "completion_tokens": 22, "total_tokens": 133}

    async def acompletion(self, request):
        self.requests.append(request)
        if not self.contents:
            raise AssertionError("unexpected LLM request")
        content = self.contents.pop(0)
        if not isinstance(content, str):
            content = json.dumps(content)
        return {
            "choices": [{"message": {"content": content}}],
            "usage": self.usage,
        }


def _breakdown_content(*titles):
    candidates = [
        {
            "kind": "implementation",
            "title": title,
            "objective": f"Deliver {title} as one independently verifiable slice.",
            "prompt": f"Implement {title}",
            "acceptance_criteria": f"{title} is covered by tests.",
            "constraints": [],
            "proof": f"Run targeted tests proving {title}.",
            "why_this_task_exists": f"{title} maps to a distinct behavior from the source contract.",
            "why_not_smaller": "Smaller subtasks would split implementation from proof.",
            "why_not_larger": "Larger tasks would mix sibling source requirements.",
            "dependencies": [],
            "likely_entry_points": ["tests/api/test_task_estimation.py"],
            "execution_mode": "AFK",
            "hitl_reason": "",
            "human_in_loop": False,
        }
        for title in titles
    ]
    return {
        "decision": "proposed_task_breakdown" if len(candidates) > 1 else "single_task",
        "candidates": candidates,
        "rejected_items": [
            {"text": "Do not add network dependencies.", "reason": "constraint, not a task"}
        ],
        "global_contract_summary": "Accepted slices must preserve the DEMO_TASK_2099 contract end-to-end.",
        "global_constraints": ["Do not add network dependencies."],
        "verification": ["Run pytest."],
        "non_goals": [],
        "recommended_sequence": list(titles),
        "confidence": 0.86,
        "rationale": "Markdown contains multiple vertical slices plus constraints.",
        "source": "llm",
    }


def _integrated_artifact_breakdown():
    return {
        "decision": "proposed_task_breakdown",
        "candidates": [
            {
                "kind": "implementation",
                "title": "Build DEMO_CLI_2099 parser",
                "objective": "Parse DEMO_INPUT_999 for DEMO_CLI_2099 as one vertical slice.",
                "prompt": "Implement the parser slice for DEMO_CLI_2099.",
                "acceptance_criteria": "Parser tests pass.",
                "constraints": ["Preserve DEMO_ID_999 values."],
                "proof": "Run parser tests for DEMO_INPUT_999.",
                "why_this_task_exists": "Parser behavior is a distinct executable seam.",
                "why_not_smaller": "Separating parser branches would lose an independently useful CLI slice.",
                "why_not_larger": "Merging report rendering would over-broaden this Worker task.",
                "dependencies": [],
                "likely_entry_points": ["src/demo_cli_2099.py", "tests/test_demo_cli_2099.py"],
                "execution_mode": "AFK",
                "hitl_reason": "",
                "human_in_loop": False,
            },
            {
                "kind": "implementation",
                "title": "Render DEMO_REPORT_2099 output",
                "objective": "Render DEMO_REPORT_2099 after parsed DEMO_INPUT_999 values are available.",
                "prompt": "Implement the report rendering slice for DEMO_REPORT_2099.",
                "acceptance_criteria": "Report shape is covered.",
                "constraints": [],
                "proof": "Run report rendering tests for DEMO_REPORT_2099 shape.",
                "why_this_task_exists": "Report output is independently reviewable after parser behavior exists.",
                "why_not_smaller": "Splitting fields individually would over-fragment the report slice.",
                "why_not_larger": "Merging acceptance verification would make the task both implement and audit.",
                "dependencies": ["Build DEMO_CLI_2099 parser"],
                "likely_entry_points": ["src/demo_cli_2099.py", "tests/test_demo_report_2099.py"],
                "execution_mode": "AFK",
                "hitl_reason": "",
                "human_in_loop": False,
            },
            {
                "kind": "acceptance_verification",
                "title": "Acceptance Verification for DEMO_CLI_2099",
                "objective": "Prove DEMO_CLI_2099 satisfies the original integrated source contract.",
                "prompt": "Verify the combined CLI/report artifact against the source contract.",
                "acceptance_criteria": "Executable smoke proof and findings are recorded.",
                "constraints": ["Do not rebuild the CLI."],
                "proof": "Run a CLI smoke check against DEMO_INPUT_999 and inspect DEMO_REPORT_2099 output.",
                "why_this_task_exists": "The parser and report slices produce one integrated artifact requiring final proof.",
                "why_not_smaller": "A smaller verification would miss end-to-end CLI/report behavior.",
                "why_not_larger": "This must not become a whole-task reimplementation rerun.",
                "dependencies": ["Build DEMO_CLI_2099 parser", "Render DEMO_REPORT_2099 output"],
                "likely_entry_points": ["tests/test_demo_cli_2099.py"],
                "execution_mode": "HITL",
                "hitl_reason": "Operator reviews final findings before global acceptance.",
                "human_in_loop": True,
            },
        ],
        "rejected_items": [],
        "global_contract_summary": "DEMO_CLI_2099 must parse input and emit DEMO_REPORT_2099 with 999-style IDs.",
        "global_constraints": ["Use only synthetic DEMO_2099 data."],
        "verification": ["Run a CLI smoke check."],
        "non_goals": [],
        "recommended_sequence": [
            "Build DEMO_CLI_2099 parser",
            "Render DEMO_REPORT_2099 output",
            "Acceptance Verification for DEMO_CLI_2099",
        ],
        "confidence": 0.9,
        "rationale": "Two implementation slices create one integrated artifact requiring final proof.",
        "source": "llm",
    }


class FakeEstimatorLLM:
    def __init__(self, content=None, *, exc=None, usage=None):
        self.content = content or {
            "drivers": {
                "files_to_read": 2,
                "files_to_modify": 1,
                "expected_turns": 3,
                "needs_test_run": True,
            },
            "shadow_token_estimate": 11_000,
            "complexity": "modest",
            "confidence": 0.82,
            "investigation_recommended": False,
            "rationale": "Endpoint plus tests is a modest task.",
            "assumptions": ["No schema migration is needed."],
            "risk_flags": ["integration tests may expand scope"],
            "budget_note": "Within normal daily budget.",
            "source": "llm",
        }
        self.exc = exc
        self.usage = usage or {"prompt_tokens": 111, "completion_tokens": 22, "total_tokens": 133}
        self.requests = []

    async def acompletion(self, request):
        self.requests.append(request)
        if self.exc:
            raise self.exc
        return {
            "choices": [{"message": {"content": json.dumps(self.content)}}],
            "usage": self.usage,
        }


def _client_with_llm(
    tmp_path, llm, *, connected_project: bool = True, estimator_model: str = "openai/gpt-4.1-mini"
):
    settings = Settings(
        database_path=tmp_path / "harness.db",
        guardrails_path=ROOT / "guardrails.yaml",
        orchestrator_model=estimator_model,
    )
    app = create_app(settings)
    db.init_db(settings.database_path)
    app.state.llm_client = llm
    app.state.orchestrator_job_runner = FakeOrchestratorJobRunner(llm)
    if connected_project:
        project_root = tmp_path / "connected-project"
        project_root.mkdir(exist_ok=True)
        db.upsert_connected_project(
            settings.database_path,
            name=project_root.name,
            root_path=str(project_root.resolve()),
            profile=git_project_profile(project_root, name=project_root.name),
            capability={"state": "launch_ready", "can_launch": True},
        )
    return TestClient(app)

def test_create_task_with_estimate_defaults_to_estimated(tmp_path):
    with _client(tmp_path) as client:
        created = client.post(
            "/tasks",
            json={
                "description": "Add list command",
                "estimate_tokens": 8_000,
                "recommended_model": "claude-haiku",
            },
        )

    assert created.status_code == 200
    assert created.json()["status"] == "Estimated"

@pytest.mark.parametrize(
    ("accept", "react_json"),
    [("text/html", False), (None, False), ("application/json", True)],
)
def test_project_estimate_form_stamps_connected_project_metadata(
    tmp_path, monkeypatch, accept, react_json
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM()
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    project_root = tmp_path / "project"
    project_root.mkdir()
    project = db.upsert_connected_project(
        database_path,
        name="Project",
        root_path=str(project_root.resolve()),
        profile=git_project_profile(project_root, name="Project"),
        capability={"state": "launch_ready", "can_launch": True},
    )

    with _client_with_llm(tmp_path, llm) as client:
        headers = _auth_headers()
        if accept:
            headers["accept"] = accept
        response = client.post(
            f"/projects/{project['id']}/tasks/estimate-form",
            data={"description": "Add project-scoped task"},
            headers=headers,
            follow_redirects=False,
        )

    tasks = db.list_tasks(database_path)
    if react_json:
        assert response.status_code == 200
        assert response.json() == {
            "ok": True,
            "error": None,
            "setup_href": None,
            "next_href": None,
            "task": {"id": tasks[0]["id"], "status": "Estimated"},
        }
    else:
        assert response.status_code == 303
        assert response.headers["location"] == f"/projects/{project['id']}"
    assert len(tasks) == 1
    assert tasks[0]["metadata"]["connected_project_id"] == project["id"]
    assert tasks[0]["metadata"]["project_root_path"] == project_task_metadata(project)["project_root_path"]


def test_project_estimate_includes_repo_context_and_relevant_calibration_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM()

    with _client_with_llm(tmp_path, llm) as client:
        project = db.list_connected_projects(tmp_path / "harness.db")[0]
        project_root = Path(project["root_path"])
        (project_root / "AGENTS.md").write_text("Use pytest for DEMO_TASK_2099.", encoding="utf-8")
        catalog_dir = project_root / ".foreman"
        catalog_dir.mkdir()
        # The catalog matches on shared profile keys, so it must name this project's
        # confirmed verification command rather than a hardcoded one.
        (catalog_dir / "estimation_calibration.yaml").write_text(
            f"""
cases:
  - id: DEMO-CAL-2099-999-101
    task_description: Add project-scoped DEMO_PORTAL_2099 archive filter tests.
    project_profile:
      name: {project["profile"]["name"]}
      test_command: {project["profile"]["test_command"]}
    task_kind: implementation
    complexity: modest
    recommended_model: claude-sonnet-4-6
    expected_tokens_min: 7000
    expected_tokens_max: 15000
    actual_tokens: 11200
    rationale: Local DEMO_2099 portal task with route and template coverage.
""",
            encoding="utf-8",
        )

        response = client.post(
            f"/projects/{project['id']}/tasks/estimate-form",
            data={"description": "Add project-scoped DEMO_PORTAL_2099 archive filter tests."},
            headers={**_auth_headers(), "accept": "text/html"},
            follow_redirects=False,
        )

    request_payload = json.loads(llm.requests[0]["messages"][1]["content"])
    system_prompt = llm.requests[0]["messages"][0]["content"]

    assert response.status_code == 303
    assert "project_context" in request_payload
    assert "Use pytest for DEMO_TASK_2099" in request_payload["project_context"]
    assert "calibration_context" in request_payload
    assert "DEMO-CAL-2099-999-101" in request_payload["calibration_context"]
    assert "expected=7000-15000" in request_payload["calibration_context"]
    assert "actual=11200" in request_payload["calibration_context"]
    assert "Estimation calibration context" in system_prompt
    assert "do not directly multiply, clamp, or override" in system_prompt


def test_project_estimate_without_relevant_calibration_keeps_repo_context_only(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM()

    with _client_with_llm(tmp_path, llm) as client:
        project = db.list_connected_projects(tmp_path / "harness.db")[0]
        project_root = Path(project["root_path"])
        (project_root / "AGENTS.md").write_text("Use pytest for DEMO_TASK_2099.", encoding="utf-8")

        response = client.post(
            f"/projects/{project['id']}/tasks/estimate-form",
            data={"description": "Reword local onboarding paragraph with no matching calibration terms."},
            headers={**_auth_headers(), "accept": "text/html"},
            follow_redirects=False,
        )

    request_payload = json.loads(llm.requests[0]["messages"][1]["content"])

    assert response.status_code == 303
    assert "project_context" in request_payload
    assert "calibration_context" not in request_payload


def test_global_estimate_can_use_default_calibration_without_project_context(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM()

    with _client_with_llm(tmp_path, llm, connected_project=False) as client:
        response = client.post(
            "/estimate",
            headers=_auth_headers(),
            json={"description": "Implement DEMO_WORKER_2099 token evidence parsing."},
        )

    task = response.json()
    request_payload = json.loads(llm.requests[0]["messages"][1]["content"])

    assert response.status_code == 200
    assert "project_context" not in request_payload
    assert "calibration_context" in request_payload
    assert "DEMO-CAL-2099-999-003" in request_payload["calibration_context"]
    assert task["estimate_tokens"] == 12_345


def test_manual_calibration_cases_do_not_inflate_completed_accuracy_or_control_plane_spend(tmp_path):
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    session = db.create_session(
        database_path,
        task_description="Estimate DEMO_TASK_2099",
        model="openai/gpt-4.1-mini",
        session_key_hash="DEMO_HASH_2099_999",
        guardrail_overrides={},
        status="completed",
    )
    db.record_token_turn(
        database_path,
        session_id=session["id"],
        usage_kind="estimation",
        model="openai/gpt-4.1-mini",
        prompt_tokens=900,
        completion_tokens=100,
        cost=0.0,
        raw_usage={"spend_category": "control_plane"},
    )
    db.create_task(
        database_path,
        description="Estimated but not Done DEMO_TASK_2099",
        status="Estimated",
        estimate_tokens=8_000,
        recommended_model="claude-sonnet-4-6",
        actual_tokens=12_000,
    )

    assert db.estimation_accuracy(database_path) == {
        "completed_count": None,
        "median_error_ratio": None,
        "within_2x_pct": None,
    }

    db.create_task(
        database_path,
        description="Done DEMO_TASK_2099 Worker task",
        status="Done",
        estimate_tokens=10_000,
        recommended_model="claude-sonnet-4-6",
        actual_tokens=15_000,
    )

    assert db.estimation_accuracy(database_path) == {
        "completed_count": 1,
        "median_error_ratio": 1.5,
        "within_2x_pct": 100.0,
    }


def test_project_markdown_breakdown_request_includes_separate_repo_context_and_stores_evidence(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeSequentialLLM([_breakdown_content("Ground DEMO_ROUTE_2099 in repo context")])
    markdown = "# DEMO_TASK_2099 repo-grounded intake\n\n- [ ] Ground DEMO_ROUTE_2099 in repo context"

    with _client_with_llm(tmp_path, llm) as client:
        project = db.list_connected_projects(tmp_path / "harness.db")[0]
        project_root = Path(project["root_path"])
        (project_root / "AGENTS.md").write_text(
            "Use pytest for DEMO_TASK_2099. "
            "api_key=DEMO_SECRET_2099_VALUE "
            "sk-DEMO_PROVIDER_TOKEN_2099 "
            "Bearer DEMO_BEARER_TOKEN_2099",
            encoding="utf-8",
        )
        (project_root / "pyproject.toml").write_text("[project]\nname = 'demo-2099'\n", encoding="utf-8")
        (project_root / "src").mkdir()
        (project_root / ".env").write_text("password=DEMO_PASSWORD_2099", encoding="utf-8")

        response = client.post(
            f"/projects/{project['id']}/tasks/estimate-form",
            headers={**_auth_headers(), "accept": "text/html"},
            data={"description": markdown},
            follow_redirects=False,
        )
        breakdown_id = response.headers["location"].split("/")[2]
        breakdown = db.get_task_breakdown(tmp_path / "harness.db", breakdown_id)

    request_payload = json.loads(llm.requests[0]["messages"][1]["content"])
    repo_context = request_payload["repo_context"]
    stored_evidence = breakdown["repo_context_evidence"]

    assert response.status_code == 303
    assert request_payload["source_text"] == markdown
    assert repo_context["text"] != request_payload["source_text"]
    assert "Use pytest for DEMO_TASK_2099" in repo_context["text"]
    assert "DEMO_SECRET_2099_VALUE" not in json.dumps(repo_context)
    assert "DEMO_PROVIDER_TOKEN_2099" not in json.dumps(repo_context)
    assert "DEMO_BEARER_TOKEN_2099" not in json.dumps(repo_context)
    assert "DEMO_PASSWORD_2099" not in json.dumps(repo_context)
    assert "pyproject.toml" in repo_context["manifests"]
    assert "src" in repo_context["entrypoints"]
    assert "pytest" in repo_context["test_commands"]
    assert stored_evidence["source"] == "repo_context_brief"
    assert stored_evidence["documents"] == ["AGENTS.md"]
    assert "pyproject.toml" in stored_evidence["manifests"]
    assert ".env" not in json.dumps(stored_evidence)
    assert "DEMO_SECRET_2099_VALUE" not in json.dumps(stored_evidence)
    assert "DEMO_PROVIDER_TOKEN_2099" not in json.dumps(stored_evidence)
    assert "DEMO_BEARER_TOKEN_2099" not in json.dumps(stored_evidence)


def test_global_markdown_breakdown_request_sends_no_repo_context(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeSequentialLLM([_breakdown_content("Keep DEMO_TASK_2099 global")])
    markdown = "# DEMO_TASK_2099 global intake\n\n- [ ] Keep DEMO_TASK_2099 global"

    with _client_with_llm(tmp_path, llm, connected_project=False) as client:
        response = client.post(
            "/tasks/estimate-form",
            headers={**_auth_headers(), "accept": "text/html"},
            data={"description": markdown},
            follow_redirects=False,
        )
        breakdown_id = response.headers["location"].split("/")[2]
        breakdown = db.get_task_breakdown(tmp_path / "harness.db", breakdown_id)

    request_payload = json.loads(llm.requests[0]["messages"][1]["content"])
    assert response.status_code == 303
    assert "repo_context" not in request_payload
    assert breakdown["repo_context_evidence"] == {}


def test_project_markdown_breakdown_missing_root_falls_back_without_repo_context(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeSequentialLLM([_breakdown_content("Fallback DEMO_TASK_2099 without context")])
    markdown = "# DEMO_TASK_2099 missing root\n\n- [ ] Fallback DEMO_TASK_2099 without context"

    with _client_with_llm(tmp_path, llm) as client:
        project = db.list_connected_projects(tmp_path / "harness.db")[0]
        shutil.rmtree(Path(project["root_path"]))
        response = client.post(
            f"/projects/{project['id']}/tasks/estimate-form",
            headers={**_auth_headers(), "accept": "text/html"},
            data={"description": markdown},
            follow_redirects=False,
        )
        breakdown_id = response.headers["location"].split("/")[2]
        breakdown = db.get_task_breakdown(tmp_path / "harness.db", breakdown_id)

    request_payload = json.loads(llm.requests[0]["messages"][1]["content"])
    assert response.status_code == 303
    assert request_payload["source_text"] == markdown
    assert "repo_context" not in request_payload
    assert breakdown["repo_context_evidence"] == {}


def test_create_task_blocks_explicit_estimated_without_estimate(tmp_path):
    with _client(tmp_path) as client:
        created = client.post(
            "/tasks",
            json={"description": "Missing estimate", "status": "Estimated"},
        )

    assert created.status_code == 200
    assert created.json()["status"] == "Estimated"
    metadata = created.json()["metadata"]
    assert metadata["blocked_reason"] == "Estimate task before launch."
    assert metadata["requires_manual_estimate"] is True
    assert metadata["requested_status"] == "Estimated"
    assert metadata["blocked_condition"]["reason"] == "Estimate task before launch."
    assert metadata["blocked_condition"]["origin"] == "task_create"
    assert metadata["blocked_condition"]["timestamp"]

def test_estimate_uses_llm_structured_json_creates_estimated_task_and_tracks_usage(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM()
    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/estimate",
            headers=_auth_headers(),
            json={
                "description": "Add an endpoint and tests for sessions",
                "remaining_daily_tokens": 100_000,
                "daily_cap_tokens": 1_000_000,
            },
        )
        task = response.json()
        dashboard = client.get("/api/dashboard", headers=_auth_headers())
        with db.connect(tmp_path / "harness.db") as conn:
            token_turn = conn.execute("select * from token_turns").fetchone()
            estimation_session = conn.execute("select * from sessions").fetchone()

    assert response.status_code == 200
    assert task["status"] == "Estimated"
    assert task["estimate_tokens"] == 12_345
    assert task["recommended_model"] is None
    assert task["actual_tokens"] is None
    assert task["metadata"]["estimation_source"] == "driver_arithmetic"
    assert task["metadata"]["confidence"] == 0.82
    assert task["metadata"]["assumptions"] == ["No schema migration is needed."]
    assert task["metadata"]["risk_flags"] == ["integration tests may expand scope"]
    assert task["metadata"]["budget_note"] == "Within normal daily budget."
    assert task["metadata"]["worker_model_constraint"]["state"] == "no_allowed_models"
    assert task["metadata"]["worker_model_constraint"]["selected_model"] is None
    assert llm.requests[0]["model"] == "openai/gpt-4.1-mini"
    assert "Call submit_estimate exactly once" in llm.requests[0]["messages"][0]["content"]
    assert "Add an endpoint and tests for sessions" in llm.requests[0]["messages"][1]["content"]
    assert token_turn["usage_kind"] == "estimation"
    assert token_turn["prompt_tokens"] == 111
    assert token_turn["completion_tokens"] == 22
    assert token_turn["total_tokens"] == 133
    assert estimation_session["status"] == "completed"
    assert estimation_session["session_key_hash"].startswith("native-planning:")
    session_overrides = json.loads(estimation_session["guardrail_overrides_json"])
    assert session_overrides["session_kind"] == "planning"
    assert session_overrides["tracking_mode"] == "native_usage"
    assert all(
        char in "0123456789abcdef"
        for char in estimation_session["session_key_hash"].removeprefix("native-planning:")
    )
    assert dashboard.json()["budget"]["total_tokens"] == 133


def test_estimate_records_provider_reported_cost(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM(
        usage={"prompt_tokens": 111, "completion_tokens": 22, "total_tokens": 133, "cost": 0.0042}
    )
    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/estimate",
            headers=_auth_headers(),
            json={"description": "Estimate with OpenRouter reported cost"},
        )
        with db.connect(tmp_path / "harness.db") as conn:
            token_turn = conn.execute("select * from token_turns").fetchone()

    assert response.status_code == 200
    assert token_turn["cost"] == pytest.approx(0.0042)


def test_estimate_records_null_when_provider_cost_is_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client_with_llm(tmp_path, FakeEstimatorLLM(), estimator_model="unpriced-model") as client:
        response = client.post(
            "/estimate",
            headers=_auth_headers(),
            json={"description": "Estimate with unavailable provider cost"},
        )
        with db.connect(tmp_path / "harness.db") as conn:
            token_turn = conn.execute("select * from token_turns").fetchone()

    assert response.status_code == 200
    assert token_turn["cost"] is None


def test_estimate_without_allowed_worker_models_blocks_launch_with_setup_reason(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM()
    with _client_with_llm(tmp_path, llm) as client:
        estimated = client.post(
            "/estimate",
            headers=_auth_headers(),
            json={"description": "Add model routing setup reason"},
        ).json()
        launch = client.post(f"/tasks/{estimated['id']}/launch", headers=_auth_headers(), json={})

    body = launch.json()
    assert estimated["recommended_model"] is None
    assert estimated["metadata"]["worker_model_constraint"]["state"] == "no_allowed_models"
    assert launch.status_code == 409
    assert body["launch_guardrails"]["reasons"] == [
        "Approve at least one allowed Worker model before launch."
    ]
    assert body["task"]["metadata"]["launch_blocked_reason"] == "Approve at least one allowed Worker model before launch."


def test_estimate_ignores_legacy_estimator_model_when_distinct_from_orchestrator(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM()
    settings = Settings(
        database_path=tmp_path / "harness.db",
        guardrails_path=ROOT / "guardrails.yaml",
        control_plane_model="openai/gpt-4.1-control",
        operator_config={"estimator_model": "openai/gpt-4.1-estimator"},
    )
    db.init_db(settings.database_path)
    # The legacy setting is migration evidence only; it cannot select this job.
    seed_orchestrator_inventory(settings.database_path, model="openai/gpt-4.1-control")
    app = create_app(settings)
    app.state.llm_client = llm
    app.state.orchestrator_job_runner = FakeOrchestratorJobRunner(llm)

    with TestClient(app) as client:
        response = client.post(
            "/estimate",
            headers=_auth_headers(),
            json={"description": "Use distinct estimator model"},
        )
        with db.connect(tmp_path / "harness.db") as conn:
            token_turn = conn.execute("select * from token_turns").fetchone()
            estimation_session = conn.execute("select * from sessions").fetchone()

    assert response.status_code == 200
    assert llm.requests[0]["model"] == "openai/gpt-4.1-control"
    assert estimation_session["model"] == "openai/gpt-4.1-control"
    assert token_turn["model"] == "openai/gpt-4.1-control"

def test_estimate_routes_model_to_selected_adapter_allowed_models(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM()
    with _client_with_llm(tmp_path, llm) as client:
        db.update_worker_adapter(
            tmp_path / "harness.db",
            "opencode",
            workdir=str(tmp_path),
            config={"command": "opencode"},
            supported_models=["opencode/gpt-5.1", "opencode/other"],
            is_default=True,
        )
        response = client.post(
            "/estimate",
            headers=_auth_headers(),
            json={"description": "Add endpoint", "adapter_id": "opencode"},
        )

    task = response.json()
    assert response.status_code == 200
    assert task["recommended_model"] == "opencode/gpt-5.1"
    constraint = task["metadata"]["worker_model_constraint"]
    assert constraint["state"] == "constrained_by_allowed_models"
    assert constraint["adapter_id"] == "opencode"
    assert constraint["available_models"] == ["opencode/gpt-5.1", "opencode/other"]
    assert constraint["guardrail_policy_model"] == "claude-sonnet-4-6"
    assert constraint["original_model"] == "claude-sonnet-4-6"
    assert constraint["selected_model"] == "opencode/gpt-5.1"
    assert constraint["reason"] == "guardrail_policy_model_not_allowed"
    assert task["metadata"]["model_routing"] == {
        "selected_adapter_id": "opencode",
        "selected_model": "opencode/gpt-5.1",
        "original_complexity": "modest",
        "routing_tier": "modest",
        "guardrail_policy_model": "claude-sonnet-4-6",
        "state": "constrained_by_allowed_models",
        "reason": "guardrail_policy_model_not_allowed",
        "budget_clamped": False,
    }

def test_estimate_routed_model_avoids_heavy_first_discovered_model_for_simple_task(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM(
        content={
            **FakeEstimatorLLM().content,
            "drivers": {
                "files_to_read": 1,
                "files_to_modify": 0,
                "expected_turns": 1,
                "needs_test_run": False,
            },
            "shadow_token_estimate": 2_000,
            "complexity": "simple",
        }
    )
    with _client_with_llm(tmp_path, llm) as client:
        db.update_worker_adapter(
            tmp_path / "harness.db",
            "opencode",
            workdir=str(tmp_path),
            config={"command": "opencode"},
            supported_models=["opencode/big-pickle", "opencode/claude-haiku-4-5", "opencode/gpt-5.4-mini"],
            is_default=True,
        )
        response = client.post(
            "/estimate",
            headers=_auth_headers(),
            json={"description": "Fix a small DEMO_TASK_2099 typo", "adapter_id": "opencode"},
        )

    task = response.json()
    assert response.status_code == 200
    assert task["recommended_model"] == "opencode/claude-haiku-4-5"
    assert task["metadata"]["worker_model_constraint"]["selected_model"] == "opencode/claude-haiku-4-5"
    assert task["metadata"]["worker_model_constraint"]["reason"] == "guardrail_policy_model_not_allowed_ranked"

def test_estimate_requires_portal_auth_before_llm_call(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM()
    with _client_with_llm(tmp_path, llm) as client:
        response = client.post("/estimate", json={"description": "Do not spend tokens"})

    assert response.status_code == 401
    assert llm.requests == []

def test_estimate_invalid_llm_result_creates_blocked_manual_task_without_heuristic_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM(content={"complexity": "simple"})
    with _client_with_llm(tmp_path, llm) as client:
        response = client.post("/estimate", headers=_auth_headers(), json={"description": "Fix typo"})

    task = response.json()
    assert response.status_code == 200
    assert task["status"] == "Estimated"
    assert task["estimate_tokens"] is None
    assert task["recommended_model"] is None
    assert task["metadata"]["requires_manual_estimate"] is True
    assert task["metadata"]["estimator_failure_type"] == "EstimatorValidationError"
    assert task["metadata"]["estimation_source"] == "manual_required"

def test_estimate_form_accepts_pasted_markdown_task(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeSequentialLLM([
        _breakdown_content("Add parser", "Add tests", "Update docs"),
        FakeEstimatorLLM().content,
        FakeEstimatorLLM().content,
        FakeEstimatorLLM().content,
    ])
    markdown = "# DEMO_TASK_2099 Markdown intake\n\n- [ ] Add parser\n- [ ] Add tests\n- [ ] Update docs\n- [ ] Do not add network dependencies."

    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/tasks/estimate-form",
            headers={**_auth_headers(), "accept": "text/html"},
            data={"description": markdown},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"].startswith("/task-breakdowns/")
        assert response.headers["location"].endswith("/review")
        assert db.list_tasks(tmp_path / "harness.db") == []
        breakdown_id = response.headers["location"].split("/")[2]
        review = client.get(f"/api/task-breakdowns/{breakdown_id}/review", headers=_auth_headers())
        accept = client.post(
            f"/task-breakdowns/{breakdown_id}/accept",
            headers={**_auth_headers(), "accept": "text/html"},
            data={
                "accept_0": "1",
                "accept_1": "1",
                "accept_2": "1",
                "kind_0": "implementation",
                "title_0": "Add parser",
                "prompt_0": "Implement Add parser",
                "acceptance_criteria_0": "Parser is tested.",
                "constraints_0": "",
                "kind_1": "implementation",
                "title_1": "Add tests",
                "prompt_1": "Implement Add tests",
                "acceptance_criteria_1": "Tests pass.",
                "constraints_1": "",
                "kind_2": "implementation",
                "title_2": "Update docs",
                "prompt_2": "Implement Update docs",
                "acceptance_criteria_2": "Docs are updated.",
                "constraints_2": "",
                "global_contract_summary": "Edited DEMO_TASK_2099 contract summary.",
                "global_constraints": "Do not add network dependencies.",
                "verification": "Run pytest.",
            },
            follow_redirects=False,
        )
        tasks = db.list_tasks(tmp_path / "harness.db")
        breakdown = db.get_task_breakdown(tmp_path / "harness.db", breakdown_id)
        board = client.get(
            f"/api/projects/{breakdown['intake_metadata']['connected_project_id']}/board",
            headers=_auth_headers(),
        )

    review_json = review.json()
    assert any("Add parser" in c["title"]["preview"] for c in review_json["candidates"]["items"])
    assert "constraint, not a task" in review_json["context"]["rejected_items"]["items"][0]["reason"]["preview"]
    # "Confidence" was a UI label assertion; dropped per final-jinja-retirement.
    assert review_json["links"]["board_href"] == f"/projects/{breakdown['intake_metadata']['connected_project_id']}"
    assert accept.status_code == 303
    assert accept.headers["location"] == f"/projects/{breakdown['intake_metadata']['connected_project_id']}"
    assert len(tasks) == 3
    assert len(llm.requests) == 4
    assert tasks[0]["metadata"]["task_breakdown_id"] == breakdown_id
    assert tasks[0]["metadata"]["task_breakdown_kind"] == "implementation"
    assert tasks[0]["metadata"]["task_breakdown_global_contract_summary"] == "Edited DEMO_TASK_2099 contract summary."
    assert tasks[0]["metadata"]["task_breakdown_global_constraints"] == ["Do not add network dependencies."]
    assert tasks[0]["metadata"]["task_breakdown_verification"] == ["Run pytest."]
    assert breakdown["status"] == "accepted"
    assert breakdown["created_task_ids"] == [task["id"] for task in tasks]
    board_json = board.json()
    assert any(
        "Add parser" in task["summary"]["text"]
        for column in board_json["tasks_by_status"].values()
        for task in column
    )


def test_accepting_legacy_afk_breakdown_preserves_afk_and_clears_hitl_reason(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeSequentialLLM([FakeEstimatorLLM().content])
    db_path = tmp_path / "harness.db"

    with _client_with_llm(tmp_path, llm) as client:
        breakdown = db.create_task_breakdown(
            db_path,
            source_text="# DEMO_TASK_2099 legacy AFK\n\n- [ ] Implement legacy slice",
            source_sha256="demo-legacy-afk-2099",
            intake_metadata={},
            status="pending_review",
            decision="single_task",
            model="legacy-model-2099",
            candidates=[
                {
                    "kind": "implementation",
                    "title": "DEMO_TASK_2099 legacy AFK slice",
                    "prompt": "Implement the legacy AFK slice.",
                    "acceptance_criteria": "Legacy AFK tests pass.",
                    "constraints": [],
                    "human_in_loop": False,
                }
            ],
            rejected_items=[],
            global_contract_summary="Legacy AFK source summary.",
            global_constraints=[],
            verification=["Run legacy AFK tests."],
            non_goals=[],
            recommended_sequence=["DEMO_TASK_2099 legacy AFK slice"],
            confidence=0.8,
            rationale="Legacy candidate before execution_mode existed.",
        )
        review = client.get(f"/api/task-breakdowns/{breakdown['id']}/review", headers=_auth_headers())
        accept = client.post(
            f"/task-breakdowns/{breakdown['id']}/accept",
            headers={**_auth_headers(), "accept": "text/html"},
            data={
                "accept_0": "1",
                "kind_0": "implementation",
                "title_0": "DEMO_TASK_2099 legacy AFK slice",
                "prompt_0": "Implement the legacy AFK slice.",
                "acceptance_criteria_0": "Legacy AFK tests pass.",
                "constraints_0": "",
                "hitl_reason_0": "Stale operator approval reason should not survive AFK.",
                "global_contract_summary": "Legacy AFK source summary.",
                "global_constraints": "",
                "verification": "Run legacy AFK tests.",
            },
            follow_redirects=False,
        )
        tasks = db.list_tasks(db_path)

    assert review.json()["candidates"]["items"][0]["execution_mode"] == "AFK"
    assert accept.status_code == 303
    assert tasks[0]["metadata"]["task_breakdown_execution_mode"] == "AFK"
    assert tasks[0]["metadata"]["task_breakdown_hitl_reason"] == ""
    assert tasks[0]["metadata"]["task_breakdown_policy_evidence"]["hitl_reason"] == ""
    assert "Execution mode:\nAFK" in tasks[0]["description"]
    assert "Stale operator approval reason" not in tasks[0]["description"]


def test_accepting_breakdown_estimates_candidates_from_submit_arguments(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    estimator_response = json.dumps(FakeEstimatorLLM().content)
    llm = FakeSequentialLLM(
        [
            _breakdown_content("Add parser", "Add tests"),
            estimator_response,
            estimator_response,
        ]
    )
    markdown = "# DEMO_TASK_2099 Markdown intake\n\n- [ ] Add parser\n- [ ] Add tests"

    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/tasks/estimate-form",
            headers={**_auth_headers(), "accept": "text/html"},
            data={"description": markdown},
            follow_redirects=False,
        )
        breakdown_id = response.headers["location"].split("/")[2]
        accept = client.post(
            f"/task-breakdowns/{breakdown_id}/accept",
            headers={**_auth_headers(), "accept": "text/html"},
            data={
                "accept_0": "1",
                "accept_1": "1",
                "kind_0": "implementation",
                "title_0": "Add parser",
                "prompt_0": "Implement Add parser",
                "acceptance_criteria_0": "Parser is tested.",
                "constraints_0": "",
                "kind_1": "implementation",
                "title_1": "Add tests",
                "prompt_1": "Implement Add tests",
                "acceptance_criteria_1": "Tests pass.",
                "constraints_1": "",
                "global_contract_summary": "DEMO_TASK_2099 contract.",
                "global_constraints": "",
                "verification": "Run pytest.",
            },
            follow_redirects=False,
        )
        tasks = db.list_tasks(tmp_path / "harness.db")

    assert accept.status_code == 303
    assert [task["status"] for task in tasks] == ["Estimated", "Estimated"]
    assert all(task["metadata"].get("estimation_source") == "driver_arithmetic" for task in tasks)
    assert all(not task["metadata"].get("requires_manual_estimate") for task in tasks)


def test_accepting_breakdown_blocks_incomplete_fenced_estimator_json(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeSequentialLLM(
        [
            _breakdown_content("Add parser"),
            '```json\n{"token_estimate": 123',
        ]
    )
    markdown = "# DEMO_TASK_2099 Markdown intake\n\n- [ ] Add parser"

    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/tasks/estimate-form",
            headers={**_auth_headers(), "accept": "text/html"},
            data={"description": markdown},
            follow_redirects=False,
        )
        breakdown_id = response.headers["location"].split("/")[2]
        accept = client.post(
            f"/task-breakdowns/{breakdown_id}/accept",
            headers={**_auth_headers(), "accept": "text/html"},
            data={
                "accept_0": "1",
                "kind_0": "implementation",
                "title_0": "Add parser",
                "prompt_0": "Implement Add parser",
                "acceptance_criteria_0": "Parser is tested.",
                "constraints_0": "",
                "global_contract_summary": "DEMO_TASK_2099 contract.",
                "global_constraints": "",
                "verification": "Run pytest.",
            },
            follow_redirects=False,
        )
        tasks = db.list_tasks(tmp_path / "harness.db")

    assert accept.status_code == 303
    assert [task["status"] for task in tasks] == ["Estimated"]
    assert tasks[0]["metadata"]["requires_manual_estimate"] is True
    assert tasks[0]["metadata"]["estimator_failure_type"] == "EstimatorValidationError"


def test_manual_recovery_cannot_reopen_accepted_breakdown(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeSequentialLLM([_breakdown_content("Accepted candidate"), FakeEstimatorLLM().content])
    markdown = "# DEMO_TASK_2099 accepted stale recovery\n\n- [ ] Accepted candidate"

    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/tasks/estimate-form",
            headers={**_auth_headers(), "accept": "text/html"},
            data={"description": markdown},
            follow_redirects=False,
        )
        breakdown_id = response.headers["location"].split("/")[2]
        accept = client.post(
            f"/task-breakdowns/{breakdown_id}/accept",
            headers={**_auth_headers(), "accept": "text/html"},
            data={
                "accept_0": "1",
                "title_0": "Accepted candidate",
                "prompt_0": "Implement accepted candidate",
                "acceptance_criteria_0": "Accepted candidate is tested.",
                "constraints_0": "",
                "global_constraints": "",
                "verification": "Run pytest.",
            },
            follow_redirects=False,
        )
        accepted = db.get_task_breakdown(tmp_path / "harness.db", breakdown_id)
        stale_manual = client.post(
            f"/task-breakdowns/{breakdown_id}/manual",
            headers={**_auth_headers(), "accept": "text/html"},
            data={
                "title": "Stale manual mutation",
                "prompt": "This should not replace accepted candidates.",
                "acceptance_criteria": "Should not apply.",
            },
            follow_redirects=False,
        )
        after_stale_manual = db.get_task_breakdown(tmp_path / "harness.db", breakdown_id)
        tasks = db.list_tasks(tmp_path / "harness.db")

    assert accept.status_code == 303
    assert accepted["status"] == "accepted"
    assert stale_manual.status_code == 303
    assert stale_manual.headers["location"].startswith("/projects/")
    assert stale_manual.headers["location"] == f"/projects/{accepted['intake_metadata']['connected_project_id']}"
    assert after_stale_manual["status"] == "accepted"
    assert after_stale_manual["candidates"] == accepted["candidates"]
    assert after_stale_manual["created_task_ids"] == accepted["created_task_ids"]
    assert len(tasks) == 1

def test_acceptance_verification_candidate_carries_full_source_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeSequentialLLM(
        [
            _integrated_artifact_breakdown(),
            FakeEstimatorLLM().content,
            FakeEstimatorLLM().content,
            FakeEstimatorLLM().content,
        ]
    )
    markdown = """# DEMO_TASK_2099 integrated CLI

Build DEMO_CLI_2099 so it parses DEMO_INPUT_999 and emits DEMO_REPORT_2099 with DEMO_ID_999 fields.
The final artifact must be verified with a CLI smoke check and must never use real customer data.
""".strip()

    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/tasks/estimate-form",
            headers={**_auth_headers(), "accept": "text/html"},
            data={"description": markdown},
            follow_redirects=False,
        )
        breakdown_id = response.headers["location"].split("/")[2]
        review = client.get(f"/api/task-breakdowns/{breakdown_id}/review", headers=_auth_headers())
        accept = client.post(
            f"/task-breakdowns/{breakdown_id}/accept",
            headers={**_auth_headers(), "accept": "text/html"},
            data={
                "accept_0": "1",
                "accept_1": "1",
                "accept_2": "1",
                "kind_0": "implementation",
                "title_0": "Build DEMO_CLI_2099 parser",
                "prompt_0": "Implement only parser behavior.",
                "acceptance_criteria_0": "Parser tests pass.",
                "constraints_0": "Preserve DEMO_ID_999 values.",
                "kind_1": "implementation",
                "title_1": "Render DEMO_REPORT_2099 output",
                "prompt_1": "Implement only report rendering.",
                "acceptance_criteria_1": "Report tests pass.",
                "constraints_1": "",
                "kind_2": "acceptance_verification",
                "title_2": "Acceptance Verification for DEMO_CLI_2099",
                "prompt_2": "Verify the combined artifact.",
                "acceptance_criteria_2": "Smoke proof and findings are recorded.",
                "constraints_2": "Do not rebuild the CLI.",
                "hitl_reason_2": "Requires operator review or judgment before completion.",
                "global_contract_summary": "Edited summary: DEMO_CLI_2099 parses DEMO_INPUT_999 and emits DEMO_REPORT_2099.",
                "global_constraints": "Use only synthetic DEMO_2099 data.",
                "verification": "Run a CLI smoke check.",
            },
            follow_redirects=False,
        )
        tasks = db.list_tasks(tmp_path / "harness.db")
        breakdown = db.get_task_breakdown(tmp_path / "harness.db", breakdown_id)

    assert response.status_code == 303
    review_json = review.json()
    assert review_json["candidates"]["items"][2]["kind"] == "acceptance_verification"
    assert review_json["candidates"]["items"][2]["execution_mode"] == "HITL"
    assert review_json["context"]["global_contract_summary"]["preview"] == (
        "DEMO_CLI_2099 must parse input and emit DEMO_REPORT_2099 with 999-style IDs."
    )
    assert review_json["context"]["verification"]["items"][0]["preview"] == "Run a CLI smoke check."
    # UI label assertions ("Global contract summary", "Execution mode", etc.) dropped per final-jinja-retirement.
    assert accept.status_code == 303
    assert [task["metadata"]["task_breakdown_kind"] for task in tasks] == [
        "implementation",
        "implementation",
        "acceptance_verification",
    ]
    assert [task["metadata"]["task_breakdown_execution_mode"] for task in tasks] == [
        "AFK",
        "AFK",
        "HITL",
    ]
    assert tasks[2]["metadata"]["task_breakdown_hitl_reason"] == (
        "Requires operator review or judgment before completion."
    )
    assert tasks[0]["metadata"]["task_breakdown_policy_evidence"]["why_not_smaller"] == (
        "Separating parser branches would lose an independently useful CLI slice."
    )
    assert tasks[1]["metadata"]["task_breakdown_dependencies"] == ["Build DEMO_CLI_2099 parser"]
    implementation_description = tasks[0]["description"]
    verification_description = tasks[2]["description"]
    assert "Objective:" in implementation_description
    assert "Candidate proof:" in implementation_description
    assert "Likely repo entry points:" in implementation_description
    assert "Edited summary: DEMO_CLI_2099 parses DEMO_INPUT_999" in implementation_description
    assert "Implementation slice scope:" in implementation_description
    assert "do not rerun or re-solve the full source task" in implementation_description
    assert "Original source contract:" not in implementation_description
    assert "The final artifact must be verified with a CLI smoke check" not in implementation_description
    assert "Execution mode:\nHITL" in verification_description
    assert "Dependencies:" in verification_description
    assert "Original source contract:" in verification_description
    assert "Build DEMO_CLI_2099 so it parses DEMO_INPUT_999" in verification_description
    assert "Do not reimplement the whole source task" in verification_description
    assert tasks[2]["metadata"]["task_breakdown_recommended_last"] is True
    assert breakdown["global_contract_summary"] == (
        "Edited summary: DEMO_CLI_2099 parses DEMO_INPUT_999 and emits DEMO_REPORT_2099."
    )
    assert breakdown["candidates"][2]["kind"] == "acceptance_verification"

def test_estimate_form_markdown_file_overrides_pasted_text(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeSequentialLLM([_breakdown_content("Use file contents", "Ignore pasted contents")])
    markdown = b"# DEMO_TASK_2099 Uploaded task\n\n- [ ] Use file contents\n- [ ] Ignore pasted contents"

    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/tasks/estimate-form",
            headers={**_auth_headers(), "accept": "text/html"},
            data={"description": "ignored pasted task"},
            files={"markdown_file": ("DEMO_TASK_2099.md", markdown, "text/markdown")},
            follow_redirects=False,
        )
        breakdown_id = response.headers["location"].split("/")[2]
        breakdown = db.get_task_breakdown(tmp_path / "harness.db", breakdown_id)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/task-breakdowns/")
    assert db.list_tasks(tmp_path / "harness.db") == []
    assert breakdown["intake_metadata"]["intake_source"] == "markdown_upload"
    assert breakdown["intake_metadata"]["intake_filename"] == "DEMO_TASK_2099.md"
    assert "ignored pasted task" not in breakdown["source_text"]
    assert [candidate["title"] for candidate in breakdown["candidates"]] == ["Use file contents", "Ignore pasted contents"]

@pytest.mark.parametrize(
    ("accept", "react_json"),
    [("text/html", False), (None, False), ("application/json", True)],
)
def test_estimate_form_single_task_markdown_still_routes_to_breakdown_review(
    tmp_path, monkeypatch, accept, react_json
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeSequentialLLM([_breakdown_content("Fix DEMO_TASK_2099 login copy")])
    markdown = "# DEMO_TASK_2099 small task\n\nFix the login copy and run pytest."

    with _client_with_llm(tmp_path, llm) as client:
        headers = _auth_headers()
        if accept:
            headers["accept"] = accept
        response = client.post(
            "/tasks/estimate-form",
            headers=headers,
            data={"description": markdown},
            follow_redirects=False,
        )
        next_href = response.json()["next_href"] if react_json else response.headers["location"]
        breakdown_id = next_href.split("/")[2]
        breakdown = db.get_task_breakdown(tmp_path / "harness.db", breakdown_id)

    if react_json:
        assert response.status_code == 200
        assert response.json() == {
            "ok": True,
            "error": None,
            "setup_href": None,
            "next_href": next_href,
            "task": None,
        }
    else:
        assert response.status_code == 303
    assert next_href.startswith("/task-breakdowns/")
    assert next_href.endswith("/review")
    assert db.list_tasks(tmp_path / "harness.db") == []
    assert breakdown["decision"] == "single_task"
    assert breakdown["candidates"][0]["title"] == "Fix DEMO_TASK_2099 login copy"


@pytest.mark.parametrize(
    "markdown",
    [
        "**DEMO_TASK_2099 Markdown task**",
        "> DEMO_TASK_2099 quoted requirement",
        "DEMO field | DEMO value\n--- | ---\nID | 999",
        "[DEMO_TASK_2099 requirements](https://example.invalid/spec)",
        "+ DEMO_TASK_2099 plus-list item",
        "1) DEMO_TASK_2099 ordered item",
        "~~~text\nDEMO_TASK_2099\n~~~",
        "*DEMO_TASK_2099 emphasized task*",
        "_DEMO_TASK_2099 emphasized task_",
        "`DEMO_TASK_2099 inline code task`",
        "~~DEMO_TASK_2099 removed task~~",
        "<https://example.invalid/DEMO_TASK_2099>",
    ],
)
def test_markdown_detector_routes_common_markdown_constructs_to_breakdown(markdown):
    assert task_routes._looks_like_markdown(markdown) is True


def test_react_project_intake_missing_project_uses_stable_outcome(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.post(
            "/projects/proj_DEMO_999_MISSING/tasks/estimate-form",
            headers={**_auth_headers(), "accept": "application/json"},
            data={"description": "Estimate DEMO intake task 2099"},
        )

    assert response.status_code == 404
    body = response.json()
    assert set(body) == {"ok", "error", "setup_href", "next_href", "task"}
    assert body["ok"] is False
    assert body["error"] == "connected project not found"


@pytest.mark.parametrize("react_json", [False, True])
def test_project_intake_rejects_archived_project(tmp_path, monkeypatch, react_json):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = db.list_connected_projects(database_path)[0]
        db.archive_connected_project(database_path, project["id"])
        headers = _auth_headers()
        if react_json:
            headers["accept"] = "application/json"
        response = client.post(
            f"/projects/{project['id']}/tasks/estimate-form",
            headers=headers,
            data={"description": "Estimate archived DEMO task 2099"},
            follow_redirects=False,
        )

    assert response.status_code == (409 if react_json else 303)
    if react_json:
        body = response.json()
        assert body["ok"] is False
        assert body["error"] == "restore archived project before adding tasks"
    else:
        assert response.headers["location"].startswith(f"/projects/{project['id']}?error=")
    assert not any(
        task["description"] == "Estimate archived DEMO task 2099"
        for task in db.list_tasks(database_path)
    )

def test_estimate_form_breakdown_missing_source_field_still_proposes(tmp_path, monkeypatch):
    # `source` is a provenance constant the code owns; the model dropping it must
    # not fail the whole breakdown into the manual-review board.
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    content = _breakdown_content("DEMO_TASK_2099 without source field")
    content.pop("source", None)
    llm = FakeSequentialLLM([content])
    markdown = "# DEMO_TASK_2099 missing source\n\n- [ ] Add route"

    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/tasks/estimate-form",
            headers={**_auth_headers(), "accept": "text/html"},
            data={"description": markdown},
            follow_redirects=False,
        )
        breakdown_id = response.headers["location"].split("/")[2]
        breakdown = db.get_task_breakdown(tmp_path / "harness.db", breakdown_id)

    assert response.status_code == 303
    assert breakdown["status"] == "proposed"
    assert breakdown["failure_type"] is None
    assert breakdown["candidates"][0]["title"] == "DEMO_TASK_2099 without source field"


def test_estimate_form_invalid_breakdown_output_creates_manual_recovery_review(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeSequentialLLM([{"not": "a valid breakdown"}, _breakdown_content("Retry succeeded")])
    markdown = "# DEMO_TASK_2099 invalid output recovery\n\n- [ ] Add route\n- [ ] Do not add network dependencies."

    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/tasks/estimate-form",
            headers={**_auth_headers(), "accept": "text/html"},
            data={"description": markdown},
            follow_redirects=False,
        )
        breakdown_id = response.headers["location"].split("/")[2]
        breakdown = db.get_task_breakdown(tmp_path / "harness.db", breakdown_id)
        review = client.get(f"/api/task-breakdowns/{breakdown_id}/review", headers=_auth_headers())
        retry = client.post(
            f"/task-breakdowns/{breakdown_id}/retry",
            headers={**_auth_headers(), "accept": "text/html"},
            follow_redirects=False,
        )
        retried = db.get_task_breakdown(tmp_path / "harness.db", breakdown_id)
        failed_session = db.get_session(tmp_path / "harness.db", breakdown["session_id"])

    assert response.status_code == 303
    assert response.headers["location"].startswith("/task-breakdowns/")
    assert db.list_tasks(tmp_path / "harness.db") == []
    assert breakdown["status"] == "failed"
    assert breakdown["failure_type"] == "TaskBreakdownValidationError"
    assert failed_session["status"] == "failed"
    assert db.session_token_usage(tmp_path / "harness.db", failed_session["id"]) > 0
    review_json = review.json()
    assert review_json["review"]["status"] == "failed"
    assert review_json["controls"]["can_retry"] is True
    assert review_json["controls"]["can_create_manual_candidate"] is True
    # UI label assertions ("Breakdown failed", "Retry breakdown", etc.) dropped per final-jinja-retirement.
    assert retry.status_code == 303
    assert retry.headers["location"] == f"/task-breakdowns/{breakdown_id}/review"
    assert retried["status"] == "proposed"
    assert retried["decision"] == "single_task"
    assert retried["failure_type"] is None
    assert retried["failure_message"] is None
    assert retried["candidates"][0]["title"] == "Retry succeeded"


def test_estimate_form_timeout_breakdown_failure_has_safe_actionable_diagnostics(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    markdown = "# DEMO_TASK_2099 timeout recovery\n\n- [ ] Split safe timeout diagnostics"
    raw_secret = "Bearer DEMO_BEARER_TOKEN_2099"
    llm = FakeEstimatorLLM(exc=TimeoutError(f"provider timed out after prompt {markdown} {raw_secret}"))

    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/tasks/estimate-form",
            headers={**_auth_headers(), "accept": "text/html"},
            data={"description": markdown},
            follow_redirects=False,
        )
        breakdown_id = response.headers["location"].split("/")[2]
        breakdown = db.get_task_breakdown(tmp_path / "harness.db", breakdown_id)
        review = client.get(f"/api/task-breakdowns/{breakdown_id}/review", headers=_auth_headers())
        failed_session = db.get_session(tmp_path / "harness.db", breakdown["session_id"])

    assert response.status_code == 303
    assert breakdown["status"] == "failed"
    assert breakdown["failure_type"] == "TaskBreakdownUnavailableError"
    assert failed_session["status"] == "failed"
    assert "orchestrator runtime timeout" in breakdown["failure_message"]
    assert "model=" in breakdown["failure_message"]
    assert "source_chars=" in breakdown["failure_message"]
    assert "max_output_tokens=16384" in breakdown["failure_message"]
    assert "timeout_seconds=120" in breakdown["failure_message"]
    assert markdown not in breakdown["failure_message"]
    assert raw_secret not in breakdown["failure_message"]
    review_json = review.json()
    assert review_json["review"]["status"] == "failed"
    assert review_json["controls"]["can_retry"] is True
    assert review_json["controls"]["can_create_manual_candidate"] is True
    assert raw_secret not in json.dumps(review_json)
    # UI label assertions ("Breakdown failed", "Retry breakdown", "Create manual candidate") dropped per final-jinja-retirement.


def test_estimate_form_provider_rejection_breakdown_failure_is_sanitized(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM(
        exc=RuntimeError(
            "provider request failed with HTTP 400: temperature is deprecated for this model api_key=DEMO_SECRET_2099_VALUE"
        )
    )
    markdown = "# DEMO_TASK_2099 provider rejection\n\n- [ ] Retry without unsupported parameters"

    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/tasks/estimate-form",
            headers={**_auth_headers(), "accept": "text/html"},
            data={"description": markdown},
            follow_redirects=False,
        )
        breakdown_id = response.headers["location"].split("/")[2]
        breakdown = db.get_task_breakdown(tmp_path / "harness.db", breakdown_id)

    assert response.status_code == 303
    assert breakdown["status"] == "failed"
    assert "orchestrator runtime failure" in breakdown["failure_message"]
    assert "HTTP 400" in breakdown["failure_message"]
    assert "temperature is deprecated" in breakdown["failure_message"]
    assert "DEMO_SECRET_2099_VALUE" not in breakdown["failure_message"]
    assert "[REDACTED]" in breakdown["failure_message"]


def test_estimate_form_provider_echoed_source_payload_is_redacted(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    markdown = "# DEMO_TASK_2099 escaped payload\n\n- [ ] Keep provider echo safe"
    escaped_source = json.dumps(markdown)[1:-1]
    normalized_source = " ".join(markdown.split())
    llm = FakeEstimatorLLM(
        exc=RuntimeError(
            f'provider request failed with HTTP 400: {{"source_text":"{escaped_source}",'
            f'"messages":[{{"content":"{normalized_source}"}}]}}'
        )
    )

    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/tasks/estimate-form",
            headers={**_auth_headers(), "accept": "text/html"},
            data={"description": markdown},
            follow_redirects=False,
        )
        breakdown_id = response.headers["location"].split("/")[2]
        breakdown = db.get_task_breakdown(tmp_path / "harness.db", breakdown_id)
        review = client.get(f"/api/task-breakdowns/{breakdown_id}/review", headers=_auth_headers())

    assert response.status_code == 303
    assert breakdown["status"] == "failed"
    assert "HTTP 400" in breakdown["failure_message"]
    assert "[REDACTED_SOURCE_TEXT]" in breakdown["failure_message"]
    assert markdown not in breakdown["failure_message"]
    assert escaped_source not in breakdown["failure_message"]
    assert normalized_source not in breakdown["failure_message"]
    review_json = review.json()
    failure_preview = review_json["review"]["failure_message"]["preview"]
    assert "[REDACTED_SOURCE_TEXT]" in failure_preview
    assert escaped_source not in failure_preview
    assert normalized_source not in failure_preview


def test_estimate_form_rejects_non_markdown_upload_without_creating_task(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM()

    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/tasks/estimate-form",
            headers={**_auth_headers(), "accept": "text/html"},
            files={"markdown_file": ("tasks.txt", b"not markdown", "text/plain")},
            follow_redirects=False,
        )
        tasks = db.list_tasks(tmp_path / "harness.db")

    assert response.status_code == 303
    assert response.headers["location"].startswith("/board?error=")
    assert tasks == []

def test_estimate_provider_exception_is_sanitized_and_creates_no_usage_session(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    raw_error = "provider secret outage raw detail"
    llm = FakeEstimatorLLM(exc=RuntimeError(raw_error))
    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/estimate",
            headers=_auth_headers(),
            json={"description": "Needs provider call"},
        )
        with db.connect(tmp_path / "harness.db") as conn:
            sessions = conn.execute("select * from sessions").fetchall()
            token_turns = conn.execute("select * from token_turns").fetchall()

    task = response.json()
    assert response.status_code == 200
    assert task["status"] == "Estimated"
    assert task["metadata"]["blocked_reason"] == "Estimator unavailable or invalid; manual estimate required."
    assert raw_error not in json.dumps(task)
    assert task["metadata"]["estimator_failure_type"] == "EstimatorUnavailableError"
    assert len(sessions) == 1
    assert sessions[0]["status"] == "failed"
    assert token_turns == []

def test_estimate_source_becomes_driver_arithmetic(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM(content={**FakeEstimatorLLM().content, "source": "heuristic"})
    with _client_with_llm(tmp_path, llm) as client:
        response = client.post("/estimate", headers=_auth_headers(), json={"description": "Fix source"})

    task = response.json()
    assert response.status_code == 200
    assert task["status"] == "Estimated"
    assert task["metadata"]["estimation_source"] == "driver_arithmetic"

def test_estimate_rejects_worker_model_fields_from_estimator(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM(
        content={**FakeEstimatorLLM().content, "recommended_model": "unapproved-frontier-model"}
    )
    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/estimate",
            headers=_auth_headers(),
            json={"description": "Reject estimator-owned Worker model recommendation"},
        )

    task = response.json()
    assert response.status_code == 200
    assert task["status"] == "Estimated"
    assert task["recommended_model"] is None
    assert task["metadata"]["estimator_failure_type"] == "EstimatorValidationError"

def test_estimate_rejects_bool_numeric_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    for field in ["shadow_token_estimate", "confidence"]:
        content = {**FakeEstimatorLLM().content, field: True}
        llm = FakeEstimatorLLM(content=content)
        with _client_with_llm(tmp_path / field, llm) as client:
            response = client.post(
                "/estimate",
                headers=_auth_headers(),
                json={"description": f"Reject bool {field}"},
            )

        task = response.json()
        assert response.status_code == 200
        assert task["status"] == "Estimated"
        assert task["metadata"]["estimator_failure_type"] == "EstimatorValidationError"

@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"remaining_daily_tokens": True}, "remaining_daily_tokens"),
        ({"remaining_daily_tokens": -1}, "remaining_daily_tokens"),
        ({"daily_cap_tokens": True}, "daily_cap_tokens"),
        ({"daily_cap_tokens": -1}, "daily_cap_tokens"),
    ],
)
def test_estimate_rejects_bool_and_negative_numeric_request_fields(
    tmp_path, monkeypatch, payload, field
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM()
    with _client_with_llm(tmp_path, llm) as client:
        response = client.post(
            "/estimate",
            headers=_auth_headers(),
            json={"description": "Bad estimate request numeric", **payload},
        )

    assert response.status_code == 422
    assert field in response.text
    assert llm.requests == []

def test_manual_update_with_estimate_marks_estimation_source_manual(tmp_path):
    with _client(tmp_path) as client:
        created = client.post("/tasks", json={"description": "Needs manual estimate"}).json()
        updated = client.put(
            f"/tasks/{created['id']}",
            json={"estimate_tokens": 9000, "recommended_model": "claude-haiku"},
        )

    assert updated.status_code == 200
    assert updated.json()["metadata"]["estimation_source"] == "manual"

def test_manual_update_after_estimator_failure_marks_estimation_source_manual(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM(content={"complexity": "simple"})
    with _client_with_llm(tmp_path, llm) as client:
        created = client.post("/estimate", headers=_auth_headers(), json={"description": "Fix typo"})
        task = created.json()
        updated = client.put(
            f"/tasks/{task['id']}",
            json={"estimate_tokens": 9000, "recommended_model": "claude-haiku"},
        )

    assert created.status_code == 200
    assert task["status"] == "Estimated"
    assert task["metadata"]["estimation_source"] == "manual_required"
    assert updated.status_code == 200
    assert updated.json()["estimate_tokens"] == 9000
    assert updated.json()["recommended_model"] == "claude-haiku"
    assert updated.json()["metadata"]["estimation_source"] == "manual"
