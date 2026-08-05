import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from foreman_ai_hq import db
from foreman_ai_hq.app import create_app
from foreman_ai_hq.project_context import project_task_metadata
from foreman_ai_hq.settings import Settings
from foreman_ai_hq.task_launch import refresh_task_from_session
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
        profile={"name": project_root.name, "root_path": str(project_root.resolve()), "test_command": "pytest"},
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
        return {
            "choices": [{"message": {"content": json.dumps(self.contents.pop(0))}}],
            "usage": self.usage,
        }


def _breakdown_content(*titles):
    candidates = [
        {
            "kind": "implementation",
            "title": title,
            "prompt": f"Implement {title}",
            "acceptance_criteria": f"{title} is covered by tests.",
            "constraints": [],
            "human_in_loop": True,
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
                "prompt": "Implement the parser slice for DEMO_CLI_2099.",
                "acceptance_criteria": "Parser tests pass.",
                "constraints": ["Preserve DEMO_ID_999 values."],
                "human_in_loop": True,
            },
            {
                "kind": "implementation",
                "title": "Render DEMO_REPORT_2099 output",
                "prompt": "Implement the report rendering slice for DEMO_REPORT_2099.",
                "acceptance_criteria": "Report shape is covered.",
                "constraints": [],
                "human_in_loop": True,
            },
            {
                "kind": "acceptance_verification",
                "title": "Acceptance Verification for DEMO_CLI_2099",
                "prompt": "Verify the combined CLI/report artifact against the source contract.",
                "acceptance_criteria": "Executable smoke proof and findings are recorded.",
                "constraints": ["Do not rebuild the CLI."],
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
            "token_estimate": 12_345,
            "complexity": "modest",
            "confidence": 0.82,
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
        content = self.content if isinstance(self.content, str) else json.dumps(self.content)
        return {
            "choices": [{"message": {"content": content}}],
            "usage": self.usage,
        }


def _client_with_llm(tmp_path, llm):
    settings = Settings(
        database_path=tmp_path / "harness.db",
        guardrails_path=ROOT / "guardrails.yaml",
    )
    app = create_app(settings)
    db.init_db(settings.database_path)
    app.state.llm_client = llm
    app.state.orchestrator_job_runner = FakeOrchestratorJobRunner(llm)
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


def _board_task(board_response, task_id):
    assert board_response.status_code == 200
    body = board_response.json()
    for column in body["tasks_by_status"].values():
        for task in column:
            if task["id"] == task_id:
                return task
    raise AssertionError(f"task {task_id} not found on board")

def test_review_action_save_prompt_and_mark_done_preserve_completed_session_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        session = db.create_session(
            database_path,
            task_description="Reviewable work",
            model="5.4",
            session_key_hash="r" * 64,
            guardrail_overrides={},
            status="completed",
        )
        task = db.create_task(
            database_path,
            description="Reviewable work",
            status="Review",
            estimate_tokens=8000,
            recommended_model="5.4",
            actual_tokens=321,
            session_id=session["id"],
            metadata={
                "blocked_reason": "Resolved DEMO review blocker 2099",
                "blocked_condition": {
                    "reason": "Resolved DEMO review blocker 2099",
                    "origin": "review_disposition",
                    "timestamp": "2099-01-01T00:00:00Z",
                },
            },
        )

        saved = client.post(
            f"/tasks/{task['id']}/review",
            headers=_auth_headers(),
            json={"action": "save_prompt", "review_prompt": "Focus on DEMO review note 2099."},
        )
        done = client.post(
            f"/tasks/{task['id']}/review",
            headers=_auth_headers(),
            json={"action": "mark_done"},
        )

    assert saved.status_code == 200
    assert saved.json()["status"] == "Review"
    assert saved.json()["metadata"]["review_prompt"] == "Focus on DEMO review note 2099."
    assert done.status_code == 200
    body = done.json()
    assert body["status"] == "Done"
    assert body["session_id"] == session["id"]
    assert body["actual_tokens"] == 321
    assert body["metadata"]["review_decision"] == "accepted"
    assert body["metadata"]["reviewed_by"] == "operator"
    assert "blocked_condition" not in body["metadata"]
    assert "blocked_reason" not in body["metadata"]


@pytest.mark.parametrize(("accept", "react_json"), [(None, False), ("application/json", True)])
def test_review_form_without_json_accept_preserves_redirect(
    tmp_path, monkeypatch, accept, react_json
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        session = db.create_session(
            database_path,
            task_description="Review through browser form",
            model="5.4",
            session_key_hash="f" * 64,
            guardrail_overrides={},
            status="completed",
        )
        task = db.create_task(
            database_path,
            description="Review through browser form",
            status="Review",
            estimate_tokens=8000,
            recommended_model="5.4",
            session_id=session["id"],
        )

        headers = _auth_headers()
        if accept:
            headers["accept"] = accept
        response = client.post(
            f"/tasks/{task['id']}/review",
            headers=headers,
            data={"action": "mark_done"},
            follow_redirects=False,
        )

    if react_json:
        assert response.status_code == 200
        assert response.json() == {
            "ok": True,
            "error": None,
            "setup_href": None,
            "next_href": None,
            "task": {"id": task["id"], "status": "Done"},
        }
    else:
        assert response.status_code == 303
        assert response.headers["location"] == "/board"


def test_react_review_rejects_cross_project_task_binding(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = db.list_connected_projects(database_path)[0]
        session = db.create_session(
            database_path,
            task_description="Project-bound DEMO review",
            model="5.4",
            session_key_hash="p" * 64,
            guardrail_overrides={},
            status="completed",
        )
        task = db.create_task(
            database_path,
            description="Project-bound DEMO review",
            status="Review",
            estimate_tokens=8000,
            recommended_model="5.4",
            session_id=session["id"],
            metadata=project_task_metadata(project),
        )

        response = client.post(
            f"/tasks/{task['id']}/review",
            headers={**_auth_headers(), "accept": "application/json"},
            data={"action": "mark_done", "project_id": "proj_DEMO_999_OTHER"},
        )

    assert response.status_code == 409
    assert response.json() == {
        "ok": False,
        "error": "Task does not belong to the selected project.",
        "setup_href": None,
        "next_href": None,
        "task": None,
    }
    assert db.get_task(database_path, task["id"])["status"] == "Review"


def test_react_review_validation_error_uses_stable_outcome(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.post(
            "/tasks/task_DEMO_999/review",
            headers={**_auth_headers(), "accept": "application/json"},
            data={"action": "not-supported"},
        )

    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"ok", "error", "setup_href", "next_href", "task"}
    assert body["ok"] is False
    assert "action" in body["error"]


def test_react_review_missing_task_uses_stable_outcome(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.post(
            "/tasks/task_DEMO_999_MISSING/review",
            headers={**_auth_headers(), "accept": "application/json"},
            data={"action": "save_prompt", "review_prompt": "Check DEMO contract 2099"},
        )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error"] == "task not found"


def test_review_action_block_requires_reason_and_records_operator_decision(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        session = db.create_session(
            database_path,
            task_description="Blockable review",
            model="5.4",
            session_key_hash="s" * 64,
            guardrail_overrides={},
            status="completed",
        )
        task = db.create_task(
            database_path,
            description="Blockable review",
            status="Review",
            estimate_tokens=8000,
            recommended_model="5.4",
            session_id=session["id"],
        )

        missing_reason = client.post(
            f"/tasks/{task['id']}/review",
            headers=_auth_headers(),
            json={"action": "block"},
        )
        react_missing_reason = client.post(
            f"/tasks/{task['id']}/review",
            headers={**_auth_headers(), "accept": "application/json"},
            json={"action": "block"},
        )
        blocked = client.post(
            f"/tasks/{task['id']}/review",
            headers=_auth_headers(),
            json={"action": "block", "blocked_reason": "DEMO blocker reason 2099."},
        )

    assert missing_reason.status_code == 409
    assert missing_reason.json() == {"detail": "Blocked Review tasks require a reason."}
    assert react_missing_reason.status_code == 409
    assert react_missing_reason.json() == {
        "ok": False,
        "error": "Blocked Review tasks require a reason.",
        "setup_href": None,
        "next_href": None,
        "task": None,
    }
    assert blocked.status_code == 200
    body = blocked.json()
    assert body["status"] == "Review"
    assert body["metadata"]["review_decision"] == "blocked"
    assert body["metadata"]["blocked_reason"] == "DEMO blocker reason 2099."
    assert body["metadata"]["blocked_condition"]["origin"] == "review_disposition"
    assert body["session_id"] == session["id"]

def test_review_action_agent_review_uses_control_plane_and_stays_in_review(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM(
        content={
            "summary": "DEMO review says the task is acceptable.",
            "recommendation": "approve",
            "findings": [{"severity": "low", "message": "DEMO finding only."}],
        },
        usage={"prompt_tokens": 40, "completion_tokens": 9, "total_tokens": 49},
    )
    database_path = tmp_path / "harness.db"
    with _client_with_llm(tmp_path, llm) as client:
        session = db.create_session(
            database_path,
            task_description="Agent reviewed work",
            model="5.4",
            session_key_hash="t" * 64,
            guardrail_overrides={},
            status="completed",
        )
        db.record_token_turn(
            database_path,
            session_id=session["id"],
            usage_kind="worker",
            model="5.4",
            prompt_tokens=111,
            completion_tokens=22,
            cost=0,
            raw_usage={"total_tokens": 133},
        )
        task = db.create_task(
            database_path,
            description="Agent reviewed work",
            status="Review",
            estimate_tokens=8000,
            recommended_model="5.4",
            actual_tokens=133,
            session_id=session["id"],
            metadata={
                **project_task_metadata(db.list_connected_projects(database_path)[0]),
                "launch_stdout": "DEMO worker stdout 2099 with password=bad",
            },
        )

        response = client.post(
            f"/tasks/{task['id']}/review",
            headers=_auth_headers(),
            json={"action": "agent_review", "review_prompt": "Check DEMO edge case 2099."},
        )
        board = client.get(f"/api/projects/{task['metadata']['connected_project_id']}/board", headers=_auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "Review"
    assert body["metadata"]["review_prompt"] == "Check DEMO edge case 2099."
    review = body["metadata"]["agent_review"]
    assert review["status"] == "completed"
    assert review["summary"] == "DEMO review says the task is acceptable."
    assert review["recommendation"] == "approve"
    assert review["token_totals"]["total_tokens"] == 49
    assert review["findings"][0]["message"] == "DEMO finding only."
    assert review["review_session_id"] != session["id"]
    assert body["actual_tokens"] == 133
    assert llm.requests
    review_context = llm.requests[0]["messages"][1]["content"]
    assert "Check DEMO edge case 2099." in review_context
    assert "prompt_tokens" in review_context
    assert "total_tokens" in review_context
    assert "password=bad" not in review_context
    artifact = db.build_session_artifact(database_path, review["review_session_id"])
    assert artifact["token_log"][0]["usage_kind"] == "reporting"
    assert artifact["token_log"][0]["total_tokens"] == 49
    raw_usage = artifact["token_log"][0]["raw_usage"]
    assert raw_usage["spend_category"] == "reporting_summary"
    assert raw_usage["usage_source"] == "control_plane"
    assert raw_usage["reporting_kind"] == "agent_review"
    review_breakdown = db.session_token_breakdown(database_path, review["review_session_id"])
    assert review_breakdown["by_category"]["reporting_summary"] == 49
    assert review_breakdown["by_category"]["worker_execution"] == 0
    assert review_breakdown["by_source"]["control_plane"] == 49
    all_breakdown = db.token_usage_breakdown(database_path)
    assert all_breakdown["total_tokens"] == 182
    assert all_breakdown["by_category"]["worker_execution"] == 133
    assert all_breakdown["by_category"]["reporting_summary"] == 49
    assert db.session_token_breakdown(database_path, session["id"])["by_category"]["worker_execution"] == body["actual_tokens"]
    board_task = _board_task(board, task["id"])
    assert board_task["status"] == "Review"
    # Agent-review detail now surfaces through the Evidence Drawer /report
    # (related_agent_review, covered by tests/portal/test_sessions.py). The board card
    # keeps the task in Review with its original session evidence reachable.
    assert board_task["session_href"] == f"/sessions/{session['id']}"


def test_review_action_agent_review_records_review_payload_without_raw_board_dump(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM(
        content={
            "summary": "DEMO fenced review 2099 is clean.",
            "recommendation": "approve",
            "findings": [{"severity": "low", "message": "DEMO fenced finding 2099.", "path": "README.md", "line": 7}],
        },
        usage={"prompt_tokens": 20, "completion_tokens": 7, "total_tokens": 27},
    )
    database_path = tmp_path / "harness.db"
    with _client_with_llm(tmp_path, llm) as client:
        session = db.create_session(
            database_path,
            task_description="Fenced review work",
            model="5.4",
            session_key_hash="f" * 64,
            guardrail_overrides={},
            status="completed",
        )
        task = db.create_task(
            database_path,
            description="Fenced review work",
            status="Review",
            estimate_tokens=8000,
            recommended_model="5.4",
            session_id=session["id"],
            metadata=project_task_metadata(db.list_connected_projects(database_path)[0]),
        )

        response = client.post(
            f"/tasks/{task['id']}/review",
            headers=_auth_headers(),
            json={"action": "agent_review"},
        )
        board = client.get(f"/api/projects/{task['metadata']['connected_project_id']}/board", headers=_auth_headers())

    assert response.status_code == 200
    review = response.json()["metadata"]["agent_review"]
    assert review["summary"] == "DEMO fenced review 2099 is clean."
    assert review["recommendation"] == "approve"
    assert review["findings"][0]["path"] == "README.md"
    board_task = _board_task(board, task["id"])
    assert board_task["status"] == "Review"
    assert board_task["session_href"] == f"/sessions/{session['id']}"


def test_review_action_agent_review_normalizes_markdown_to_plain_text(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM(
        content={
            "summary": "**DEMO_2099 worker verification is incomplete** because `pip install` was skipped.",
            "recommendation": "needs changes",
            "findings": [
                {"severity": "high", "message": "**High:** `README.md` still references the wrong DEMO_2099 path."},
                {"severity": "low", "message": "Low - **Minor wording** still reads like markdown."},
            ],
        },
        usage={"prompt_tokens": 20, "completion_tokens": 8, "total_tokens": 28},
    )
    database_path = tmp_path / "harness.db"
    with _client_with_llm(tmp_path, llm) as client:
        session = db.create_session(
            database_path,
            task_description="Markdown review work",
            model="5.4",
            session_key_hash="m" * 64,
            guardrail_overrides={},
            status="completed",
        )
        task = db.create_task(
            database_path,
            description="Markdown review work",
            status="Review",
            estimate_tokens=8000,
            recommended_model="5.4",
            session_id=session["id"],
            metadata=project_task_metadata(db.list_connected_projects(database_path)[0]),
        )

        response = client.post(
            f"/tasks/{task['id']}/review",
            headers=_auth_headers(),
            json={"action": "agent_review"},
        )
        board = client.get(f"/api/projects/{task['metadata']['connected_project_id']}/board", headers=_auth_headers())

    assert response.status_code == 200
    review = response.json()["metadata"]["agent_review"]
    assert review["summary"] == "DEMO_2099 worker verification is incomplete because pip install was skipped."
    assert review["recommendation"] == "needs_changes"
    assert review["findings"] == [
        {"severity": "high", "message": "README.md still references the wrong DEMO_2099 path."},
        {"severity": "low", "message": "Minor wording still reads like markdown."},
    ]
    board_task = _board_task(board, task["id"])
    assert board_task["status"] == "Review"
    assert board_task["session_href"] == f"/sessions/{session['id']}"


def test_review_action_agent_review_cleans_markdown_inside_json_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM(
        content={
            "summary": "**DEMO_2099 review:**\n- Worker output is readable.",
            "recommendation": "Approved",
            "findings": [
                {"severity": "**Low**", "message": "- **No blocker** in `README.md`.", "path": "`README.md`"}
            ],
        },
        usage={"prompt_tokens": 18, "completion_tokens": 7, "total_tokens": 25},
    )
    database_path = tmp_path / "harness.db"
    with _client_with_llm(tmp_path, llm) as client:
        session = db.create_session(
            database_path,
            task_description="JSON markdown review work",
            model="5.4",
            session_key_hash="j" * 64,
            guardrail_overrides={},
            status="completed",
        )
        task = db.create_task(
            database_path,
            description="JSON markdown review work",
            status="Review",
            estimate_tokens=8000,
            recommended_model="5.4",
            session_id=session["id"],
            metadata=project_task_metadata(db.list_connected_projects(database_path)[0]),
        )

        response = client.post(
            f"/tasks/{task['id']}/review",
            headers=_auth_headers(),
            json={"action": "agent_review"},
        )
        board = client.get(f"/api/projects/{task['metadata']['connected_project_id']}/board", headers=_auth_headers())

    assert response.status_code == 200
    review = response.json()["metadata"]["agent_review"]
    assert review["summary"] == "DEMO_2099 review: Worker output is readable."
    assert review["recommendation"] == "approve"
    assert review["findings"][0] == {"severity": "low", "message": "No blocker in README.md.", "path": "README.md"}
    board_task = _board_task(board, task["id"])
    assert board_task["status"] == "Review"
    assert board_task["session_href"] == f"/sessions/{session['id']}"

def test_review_action_accepts_completed_worker_run_evidence_when_session_is_not_completed(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        session = db.create_session(
            database_path,
            task_description="Worker run evidence work",
            model="5.4",
            session_key_hash="w" * 64,
            guardrail_overrides={},
            status="failed",
        )
        task = db.create_task(
            database_path,
            description="Worker run evidence work",
            status="Review",
            estimate_tokens=8000,
            recommended_model="5.4",
            session_id=session["id"],
        )
        run = db.create_worker_run(
            database_path,
            task_id=task["id"],
            session_id=session["id"],
            adapter_id="codex",
            model="5.4",
            tracking_mode="native_usage",
            command_plan={"argv": ["codex"]},
        )
        db.mark_worker_run_completed(database_path, run["id"], returncode=0, stdout="DEMO done 2099")

        response = client.post(
            f"/tasks/{task['id']}/review",
            headers=_auth_headers(),
            json={"action": "mark_done"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "Done"
    assert response.json()["session_id"] == session["id"]

def test_review_action_rejects_non_review_task_without_changing_status(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        task = db.create_task(
            database_path,
            description="Estimated task is not reviewable",
            status="Estimated",
            estimate_tokens=8000,
            recommended_model="5.4",
        )
        response = client.post(
            f"/tasks/{task['id']}/review",
            headers=_auth_headers(),
            json={"action": "mark_done"},
        )
        after = db.get_task(database_path, task["id"])

    assert response.status_code == 409
    assert "only available for tasks in Review" in response.text
    assert after["status"] == "Estimated"

def test_review_action_agent_review_failure_is_stored_and_task_remains_review(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeEstimatorLLM(exc=RuntimeError("DEMO control-plane outage 2099"))
    database_path = tmp_path / "harness.db"
    with _client_with_llm(tmp_path, llm) as client:
        session = db.create_session(
            database_path,
            task_description="Review failure work",
            model="5.4",
            session_key_hash="v" * 64,
            guardrail_overrides={},
            status="completed",
        )
        task = db.create_task(
            database_path,
            description="Review failure work",
            status="Review",
            estimate_tokens=8000,
            recommended_model="5.4",
            session_id=session["id"],
            metadata=project_task_metadata(db.list_connected_projects(database_path)[0]),
        )

        response = client.post(
            f"/tasks/{task['id']}/review",
            headers=_auth_headers(),
            json={"action": "agent_review"},
        )
        board = client.get(f"/api/projects/{task['metadata']['connected_project_id']}/board", headers=_auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "Review"
    review = body["metadata"]["agent_review"]
    assert review["status"] == "failed"
    assert review["token_totals"]["total_tokens"] == 0
    assert review["error_type"] == "RuntimeError"
    assert "DEMO control-plane outage 2099" in review["error"]
    assert db.get_session(database_path, review["review_session_id"])["status"] == "failed"
    board_task = _board_task(board, task["id"])
    assert board_task["status"] == "Review"
    assert board_task["session_href"] == f"/sessions/{session['id']}"

