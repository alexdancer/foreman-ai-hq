from urllib.parse import unquote

from foreman_ai_hq import db
from foreman_ai_hq.board_automation import list_eligible_estimated_tasks
from foreman_ai_hq.project_context import project_task_metadata
from tests.portal.helpers import PORTAL_TOKEN, _client, _connect_project, _portal_headers


def _task_from_board(board: dict, task_id: str) -> dict:
    for column_tasks in board["tasks_by_status"].values():
        for task in column_tasks:
            if task["id"] == task_id:
                return task
    raise AssertionError(f"task {task_id} not found in board")


def _task_from_history(history: dict, task_id: str) -> dict:
    for task in history["tasks"]:
        if task["id"] == task_id:
            return task
    raise AssertionError(f"task {task_id} not found in history")


def test_board_shows_manual_estimate_blocked_condition(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    db.init_db(tmp_path / "harness.db")
    project = _connect_project(tmp_path / "harness.db", tmp_path / "project")
    with _client(tmp_path) as client:
        task = db.create_task(
            tmp_path / "harness.db",
            description="Needs operator sizing",
            status="Estimated",
            metadata={
                **project_task_metadata(project),
                "launch_blocked_reason": "Daily budget exhausted",
                "launch_retryable": False,
                "blocked_reason": "Estimator unavailable: timeout",
                "requires_manual_estimate": True,
                "blocked_condition": {
                    "reason": "Estimate task before launch.",
                    "origin": "estimation",
                    "timestamp": "2099-01-01T00:00:00+00:00",
                },
            },
        )
        response = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())

    assert response.status_code == 200
    board = response.json()
    task_json = _task_from_board(board, task["id"])
    assert task_json["status"] == "Estimated"
    assert "Needs operator sizing" in task_json["summary"]["text"]
    assert task_json["blocked_condition"]["reason"] == "Estimate task before launch."
    assert task_json["blocked_condition"]["origin"] == "estimation"
    assert task_json["blocked_condition"]["timestamp"]
    assert task_json["controls"]["requires_manual_estimate"] is True
    assert "details" not in task_json


def test_project_board_filters_tasks_and_global_board_redirects_to_recent_project(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    first = _connect_project(database_path, tmp_path / "first")
    second = _connect_project(database_path, tmp_path / "second")
    db.create_task(
        database_path,
        description="First project task",
        status="Blocked",
        metadata={**project_task_metadata(first), "blocked_reason": "manual"},
    )
    db.create_task(
        database_path,
        description="Second project task",
        status="Blocked",
        metadata={**project_task_metadata(second), "blocked_reason": "manual"},
    )
    db.create_task(database_path, description="Legacy global task", status="Blocked")

    with _client(tmp_path) as client:
        first_board = client.get(f"/api/projects/{first['id']}/board", headers=_portal_headers())
        global_board = client.get("/board", headers=_portal_headers(), follow_redirects=False)

    assert first_board.status_code == 200
    first_json = first_board.json()
    descriptions = {
        task["summary"]["text"]
        for column_tasks in first_json["tasks_by_status"].values()
        for task in column_tasks
    }
    assert "First project task" in descriptions
    assert "Second project task" not in descriptions
    assert "Legacy global task" not in descriptions
    assert global_board.status_code == 303
    assert global_board.headers["location"] == f"/projects/{second['id']}"

    with _client(tmp_path) as client:
        preserved = client.get(
            "/board?error=DEMO%202099%20blocked",
            headers=_portal_headers(),
            follow_redirects=False,
        )
    assert preserved.headers["location"] == f"/projects/{second['id']}?error=DEMO%202099%20blocked"


def test_global_board_redirects_to_projects_when_none_connected(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)

    with _client(tmp_path) as client:
        response = client.get("/board", headers=_portal_headers(), follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/projects"


def test_board_renders_columns_and_task_cards(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        project = _connect_project(tmp_path / "harness.db", tmp_path / "connected-project")
        created = db.create_task(
            tmp_path / "harness.db",
            description="Add streaming proxy tests",
            status="Estimated",
            estimate_tokens=25000,
            recommended_model="claude-sonnet",
            actual_tokens=12000,
            metadata=project_task_metadata(project),
        )
        response = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())

    assert response.status_code == 200
    board = response.json()
    for column in ["Estimated", "Running", "Review", "Done"]:
        assert column in board["columns"]
    assert "Backlog" not in board["columns"]
    assert "Other" not in board["columns"]
    # CSS/layout class names and generic button labels are React-shell concerns.
    assert board["board_empty_states"]["Running"].startswith("No Running tasks.")
    assert board["board_empty_states"]["Review"].startswith("No Review tasks.")
    assert board["board_empty_states"]["Done"].startswith("No Done tasks.")

    task = _task_from_board(board, created["id"])
    assert task["summary"]["text"] == "Add streaming proxy tests"
    assert task["estimate_tokens"] == 25000
    assert task["actual_tokens"] == 12000
    assert task["recommended_model"] == "claude-sonnet"
    assert task["controls"]["can_launch"] is True
    assert created["id"] in [
        t["id"] for column_tasks in board["tasks_by_status"].values() for t in column_tasks
    ]


def test_board_shows_launched_model_before_recommendation(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "connected-project")
        task = db.create_task(
            database_path,
            description="Run with operator selected model",
            status="Running",
            estimate_tokens=25000,
            recommended_model="gpt-5.4-mini",
            metadata={
                **project_task_metadata(project),
                "launch_model": "openai/gpt-5.5 --variant high",
            },
        )

        response = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())

    assert response.status_code == 200
    board = response.json()
    task_json = _task_from_board(board, task["id"])
    assert task_json["launch_model"] == "openai/gpt-5.5 --variant high"
    assert task_json["recommended_model"] == "gpt-5.4-mini"
    assert task_json["controls"]["can_refresh"] is True
    # Refresh form/label and on-card ordering are React-shell rendering concerns.


def test_board_defers_verbose_evidence_to_the_session_report(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    long_task_tail = "BOARD_FULL_TASK_TAIL_2099"
    stderr_tail = "BOARD_STDERR_TAIL_2099"
    stdout_tail = "BOARD_STDOUT_TAIL_2099"
    timeline_tail = "BOARD_TIMELINE_TAIL_2099"
    review_prompt_tail = "BOARD_REVIEW_PROMPT_TAIL_2099"
    review_summary_tail = "BOARD_REVIEW_SUMMARY_TAIL_2099"
    review_finding_tail = "BOARD_REVIEW_FINDING_TAIL_2099"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "connected-project")
        task = db.create_task(
            database_path,
            description="Compact board task " + ("long body " * 40) + long_task_tail,
            status="Review",
            estimate_tokens=9000,
            recommended_model="gpt-5.4-mini",
            metadata={
                **project_task_metadata(project),
                "launch_error": "Adapter failed before review",
                "last_launch_failure": {
                    "returncode": 2,
                    "stderr": "stderr line\n" + ("stderr detail\n" * 20) + stderr_tail,
                    "stdout": "stdout line\n" + ("stdout detail\n" * 20) + stdout_tail,
                },
                "launch_stdout": "worker output\n" + ("output detail\n" * 20) + stdout_tail,
                "worker_run_events": [
                    {"kind": "launch", "title": "Worker started", "detail_summary": "timeline detail " + timeline_tail}
                ],
                "review_prompt": "Focus on the bounded review details " + review_prompt_tail,
                "agent_review": {
                    "status": "completed",
                    "summary": "Review summary " + review_summary_tail,
                    "recommendation": "inspect",
                    "findings": [{"severity": "medium", "message": "Finding " + review_finding_tail}],
                },
            },
        )

        response = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())

    assert response.status_code == 200
    board = response.json()
    task_json = _task_from_board(board, task["id"])
    assert task_json["summary"]["truncated"] is True
    assert "Compact board task" in task_json["summary"]["text"]
    assert review_prompt_tail in task_json["review_prompt"]["text"]
    assert len(task_json["timeline"]) == 1
    assert timeline_tail in task_json["timeline"][0]["detail_summary"]["text"]
    serialized = str(task_json)
    assert "details" not in task_json
    assert long_task_tail not in serialized
    assert stderr_tail not in serialized
    assert stdout_tail not in serialized
    assert review_summary_tail not in serialized
    assert review_finding_tail not in serialized


def test_board_card_omits_successful_worker_run_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "connected-project")
        task = db.create_task(
            database_path,
            description="Review launched task evidence",
            status="Review",
            estimate_tokens=8000,
            recommended_model="gpt-5.4-mini",
            actual_tokens=1234,
            metadata={
                **project_task_metadata(project),
                "launch_adapter_id": "opencode",
                "launch_model": "openai/gpt-5.5 --variant high",
                "tracking_mode": "proxy_governed",
                "usage_source": "harness_proxy",
                "launch_returncode": 0,
                "worker_run_status": "completed",
                "active_worker_run_id": "wr_DEMO_999",
                "workdir_evidence": {"configured_workdir": "/tmp/DEMO_2099_project", "has_filesystem_evidence": True},
            },
        )

        response = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())

    assert response.status_code == 200
    board = response.json()
    task_json = _task_from_board(board, task["id"])
    assert task_json["actual_tokens"] == 1234
    assert task_json["launch_model"] == "openai/gpt-5.5 --variant high"
    assert "details" not in task_json
    serialized = str(task_json)
    assert "wr_DEMO_999" not in serialized
    assert "/tmp/DEMO_2099_project" not in serialized
    assert "proxy_governed" not in serialized


def test_board_card_has_stable_empty_live_state_without_launch_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "connected-project")
        task = db.create_task(
            database_path,
            description="Review task without launch evidence",
            status="Review",
            estimate_tokens=8000,
            recommended_model="5.4",
            metadata=project_task_metadata(project),
        )

        response = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())

    assert response.status_code == 200
    board = response.json()
    task_json = _task_from_board(board, task["id"])
    assert task_json["launch_model"] is None
    assert task_json["timeline"] == []
    assert "details" not in task_json


def test_board_renders_unexpected_statuses_as_estimated_with_blocked_condition(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        project = _connect_project(tmp_path / "harness.db", tmp_path / "connected-project")
        created = db.create_task(
            tmp_path / "harness.db",
            description="Odd status task",
            status="Legacy Backlog",
            metadata=project_task_metadata(project),
        )
        response = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())

    assert response.status_code == 200
    board = response.json()
    assert "Blocked" not in board["columns"]
    assert "Other" not in board["columns"]
    task_json = _task_from_board(board, created["id"])
    assert task_json["status"] == "Estimated"
    assert task_json["summary"]["text"] == "Odd status task"
    assert task_json["blocked_condition"]["reason"] == "Unsupported task status: Legacy Backlog"


def test_board_review_card_shows_disposition_actions_prompt_and_agent_review(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "connected-project")
        session = db.create_session(
            database_path,
            task_description="Review UI task",
            model="5.4",
            session_key_hash="u" * 64,
            guardrail_overrides={},
            status="completed",
        )
        task = db.create_task(
            database_path,
            description="Review UI task",
            status="Review",
            estimate_tokens=8000,
            recommended_model="5.4",
            session_id=session["id"],
            metadata={
                **project_task_metadata(project),
                "review_prompt": "DEMO focus note 2099",
                "launch_stdout": "DEMO worker stdout 2099",
                "agent_review": {
                    "status": "completed",
                    "summary": "DEMO agent review summary 2099",
                    "recommendation": "approve",
                    "findings": [{"severity": "low", "message": "DEMO finding 2099"}],
                },
            },
        )
        response = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())
        validation = client.post(
            f"/tasks/{task['id']}/review",
            headers={**_portal_headers(), "Accept": "text/html"},
            data={"action": "block", "blocked_reason": ""},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert validation.status_code == 303
    assert validation.headers["location"].startswith(f"/projects/{project['id']}/floor?error=")
    board = response.json()
    task_json = _task_from_board(board, task["id"])
    # Button labels and form action URLs are React-shell rendering concerns.
    assert task_json["controls"]["can_mark_done"] is True
    assert task_json["controls"]["can_block"] is True
    assert task_json["review_prompt"]["text"] == "DEMO focus note 2099"
    assert "DEMO agent review summary 2099" not in str(task_json)
    assert "DEMO finding 2099" not in str(task_json)
    assert "details" not in task_json
    assert task_json["session_href"] == f"/sessions/{session['id']}"


def test_board_review_card_hides_actions_without_completed_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "connected-project")
        task = db.create_task(
            database_path,
            description="Review task without completed evidence",
            status="Review",
            estimate_tokens=8000,
            recommended_model="5.4",
            metadata=project_task_metadata(project),
        )
        response = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())

    assert response.status_code == 200
    board = response.json()
    task_json = _task_from_board(board, task["id"])
    # The explanatory message is rendered by the React shell when review actions are disabled.
    assert task_json["controls"]["can_mark_done"] is False
    assert task_json["controls"]["can_block"] is False
    assert task_json["controls"]["can_save_review_prompt"] is False
    assert task_json["controls"]["can_agent_review"] is False
    assert task_json["session_href"] is None


def test_project_board_shows_context_indicator(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project_root = tmp_path / "connected-project"
        project = _connect_project(database_path, project_root)
        response = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())

    assert response.status_code == 200
    board = response.json()
    # The exact context-indicator label is a React-shell string; project identity is the backend state.
    assert board["project"]["id"] == project["id"]
    assert board["project"]["name"] == project["name"]


def test_board_redirects_when_no_project(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/board", headers=_portal_headers(), follow_redirects=False)

    assert response.status_code == 303


def test_mark_done_keeps_task_visible_until_archived(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "connected-project")
        session = db.create_session(
            database_path,
            task_description="Accepted review task",
            model="5.4",
            session_key_hash="a" * 64,
            guardrail_overrides={},
            status="completed",
        )
        task = db.create_task(
            database_path,
            description="Accepted review task",
            status="Review",
            estimate_tokens=8000,
            recommended_model="5.4",
            actual_tokens=4200,
            session_id=session["id"],
            metadata=project_task_metadata(project),
        )

        response = client.post(
            f"/tasks/{task['id']}/review",
            headers={**_portal_headers(), "Accept": "text/html"},
            data={"action": "mark_done", "project_id": project["id"]},
            follow_redirects=False,
        )
        board = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())

    updated = db.get_task(database_path, task["id"])
    assert response.status_code == 303
    assert response.headers["location"] == f"/projects/{project['id']}/floor"
    assert updated["status"] == "Done"
    assert "archived_at" not in updated["metadata"]
    assert board.status_code == 200
    board_json = board.json()
    task_json = _task_from_board(board_json, task["id"])
    assert task_json["status"] == "Done"
    assert task_json["summary"]["text"] == "Accepted review task"
    assert task_json["controls"]["can_archive"] is True


def test_archive_done_task_hides_from_board_and_preserves_history_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "connected-project")
        session = db.create_session(
            database_path,
            task_description="Archived done task",
            model="5.4",
            session_key_hash="b" * 64,
            guardrail_overrides={},
            status="completed",
        )
        task = db.create_task(
            database_path,
            description="Archived done task",
            status="Done",
            estimate_tokens=9000,
            recommended_model="5.4",
            actual_tokens=4500,
            session_id=session["id"],
            metadata={**project_task_metadata(project), "active_worker_run_id": "wr_DEMO_999"},
        )

        archive_response = client.post(
            f"/projects/{project['id']}/tasks/{task['id']}/archive",
            headers=_portal_headers(),
            follow_redirects=False,
        )
        board = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())
        history = client.get(f"/api/projects/{project['id']}/task-history", headers=_portal_headers())

    archived = db.get_task(database_path, task["id"])
    assert archive_response.status_code == 303
    assert archive_response.headers["location"] == f"/projects/{project['id']}"
    assert archived["status"] == "Done"
    assert archived["actual_tokens"] == 4500
    assert archived["session_id"] == session["id"]
    assert archived["metadata"]["archived_at"]
    assert board.status_code == 200
    board_json = board.json()
    assert not any(
        t["id"] == task["id"] for column_tasks in board_json["tasks_by_status"].values() for t in column_tasks
    )
    assert board_json["board_summary"]["archived_count"] == 1
    assert board_json["board_summary"]["history_total_tasks"] == 1
    assert history.status_code == 200
    history_json = history.json()
    history_task = _task_from_history(history_json, task["id"])
    assert history_task["description"] == "Archived done task"
    assert history_task["status"] == "Done"
    assert history_task["archived"] is True
    assert history_task["archived_at"]
    assert history_task["actual_tokens"] == 4500
    assert history_task["session_href"] == f"/sessions/{session['id']}"
    assert history_task["worker_run_id"] == "wr_DEMO_999"


def test_react_archive_actions_return_stable_json_and_preserve_project_binding(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "react-archive-project")
        other = _connect_project(database_path, tmp_path / "react-archive-other")
        individual = db.create_task(
            database_path,
            description="Archive one DEMO task",
            status="Done",
            metadata=project_task_metadata(project),
        )
        bulk = db.create_task(
            database_path,
            description="Archive remaining DEMO task",
            status="Done",
            metadata=project_task_metadata(project),
        )

        archived = client.post(
            f"/projects/{project['id']}/tasks/{individual['id']}/archive",
            headers={**_portal_headers(), "accept": "application/json"},
        )
        wrong_project = client.post(
            f"/projects/{other['id']}/tasks/{bulk['id']}/archive",
            headers={**_portal_headers(), "accept": "application/json"},
        )
        archived_all = client.post(
            f"/projects/{project['id']}/tasks/archive-done",
            headers={**_portal_headers(), "accept": "application/json"},
        )

    assert archived.status_code == 200
    assert archived.json() == {
        "ok": True,
        "error": None,
        "setup_href": None,
        "next_href": None,
        "task": {"id": individual["id"], "status": "Done"},
    }
    assert wrong_project.status_code == 404
    assert wrong_project.json() == {
        "ok": False,
        "error": "task not found for selected project",
        "setup_href": None,
        "next_href": None,
        "task": None,
    }
    assert archived_all.status_code == 200
    assert archived_all.json() == {
        "ok": True,
        "error": None,
        "setup_href": None,
        "next_href": None,
        "task": None,
    }
    assert db.get_task(database_path, bulk["id"])["metadata"]["archived_at"]


def test_archive_blocked_task_hides_from_board_and_preserves_history_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "connected-project")
        session = db.create_session(
            database_path,
            task_description="Archived blocked task",
            model="5.4",
            session_key_hash="c" * 64,
            guardrail_overrides={},
            status="completed",
        )
        task = db.create_task(
            database_path,
            description="Archived blocked task",
            status="Blocked",
            estimate_tokens=7000,
            recommended_model="5.4",
            actual_tokens=2100,
            session_id=session["id"],
            metadata={
                **project_task_metadata(project),
                "blocked_reason": "Needs product decision",
                "requires_manual_estimate": True,
                "active_worker_run_id": "wr_DEMO_999_BLOCKED",
            },
        )

        archive_response = client.post(
            f"/projects/{project['id']}/tasks/{task['id']}/archive",
            headers=_portal_headers(),
            follow_redirects=False,
        )
        board = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())
        history = client.get(f"/api/projects/{project['id']}/task-history?filter=archived", headers=_portal_headers())

    archived = db.get_task(database_path, task["id"])
    assert archive_response.status_code == 303
    assert archive_response.headers["location"] == f"/projects/{project['id']}"
    assert archived["status"] == "Estimated"
    assert archived["actual_tokens"] == 2100
    assert archived["session_id"] == session["id"]
    assert archived["metadata"]["blocked_reason"] == "Needs product decision"
    assert archived["metadata"]["requires_manual_estimate"] is True
    assert archived["metadata"]["active_worker_run_id"] == "wr_DEMO_999_BLOCKED"
    assert archived["metadata"]["archived_at"]
    assert board.status_code == 200
    board_json = board.json()
    assert not any(
        t["id"] == task["id"] for column_tasks in board_json["tasks_by_status"].values() for t in column_tasks
    )
    assert board_json["board_summary"]["archived_count"] == 1
    assert history.status_code == 200
    history_json = history.json()
    assert history_json["selected_filter"] == "archived"
    history_task = _task_from_history(history_json, task["id"])
    assert history_task["description"] == "Archived blocked task"
    assert history_task["status"] == "Estimated"
    assert history_task["archived"] is True
    assert history_task["actual_tokens"] == 2100
    assert history_task["session_href"] == f"/sessions/{session['id']}"
    assert history_task["worker_run_id"] == "wr_DEMO_999_BLOCKED"
    assert history_task["blocked_reason"] == "Needs product decision"
    assert history_task["requires_manual_estimate"] is True


def test_dismiss_estimated_task_hides_from_board_and_preserves_history_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "connected-project")
        task = db.create_task(
            database_path,
            description="Dismiss estimated task",
            status="Estimated",
            estimate_tokens=9000,
            recommended_model="5.4",
            metadata={
                **project_task_metadata(project),
                "launch_adapter_id": "opencode",
                "launch_model": "5.4",
            },
        )

        initial_board = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())
        dismiss_response = client.post(
            f"/projects/{project['id']}/tasks/{task['id']}/archive",
            headers=_portal_headers(),
            follow_redirects=False,
        )
        dismissed_board = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())
        history = client.get(f"/api/projects/{project['id']}/task-history?filter=archived", headers=_portal_headers())
        dismissed = db.get_task(database_path, task["id"])
        eligible_after_dismiss = list_eligible_estimated_tasks(database_path, project["id"])
        unarchive_response = client.post(
            f"/projects/{project['id']}/tasks/{task['id']}/unarchive",
            headers=_portal_headers(),
            follow_redirects=False,
        )
        restored_board = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())
        restored = db.get_task(database_path, task["id"])
        eligible_after_restore = list_eligible_estimated_tasks(database_path, project["id"])

    assert initial_board.status_code == 200
    initial_json = initial_board.json()
    initial_task = _task_from_board(initial_json, task["id"])
    assert initial_task["summary"]["text"] == "Dismiss estimated task"
    assert initial_task["controls"]["can_dismiss"] is True
    assert dismiss_response.status_code == 303
    assert dismiss_response.headers["location"] == f"/projects/{project['id']}"
    assert dismissed["status"] == "Estimated"
    assert dismissed["estimate_tokens"] == 9000
    assert dismissed["recommended_model"] == "5.4"
    assert dismissed["metadata"]["launch_adapter_id"] == "opencode"
    assert dismissed["metadata"]["archived_at"]
    assert eligible_after_dismiss == []
    assert dismissed_board.status_code == 200
    dismissed_json = dismissed_board.json()
    assert not any(
        t["id"] == task["id"] for column_tasks in dismissed_json["tasks_by_status"].values() for t in column_tasks
    )
    assert dismissed_json["board_summary"]["archived_count"] == 1
    assert history.status_code == 200
    history_json = history.json()
    history_task = _task_from_history(history_json, task["id"])
    assert history_task["description"] == "Dismiss estimated task"
    assert history_task["status"] == "Estimated"
    assert history_task["archived"] is True
    assert history_task["estimate_tokens"] == 9000
    assert history_task["recommended_model"] == "5.4"
    assert unarchive_response.status_code == 303
    assert unarchive_response.headers["location"] == f"/projects/{project['id']}/task-history"
    assert restored["status"] == "Estimated"
    assert "archived_at" not in restored["metadata"]
    assert restored_board.status_code == 200
    restored_json = restored_board.json()
    restored_task = _task_from_board(restored_json, task["id"])
    assert restored_task["summary"]["text"] == "Dismiss estimated task"
    assert restored_task["controls"]["can_dismiss"] is True
    assert [t["id"] for t in eligible_after_restore] == [task["id"]]


def test_archive_all_done_is_project_scoped_and_keeps_estimation_accuracy(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        first_project = _connect_project(database_path, tmp_path / "first-project")
        second_project = _connect_project(database_path, tmp_path / "second-project")
        first_done = db.create_task(
            database_path,
            description="First done task",
            status="Done",
            estimate_tokens=1000,
            actual_tokens=500,
            metadata=project_task_metadata(first_project),
        )
        second_done = db.create_task(
            database_path,
            description="Second done task",
            status="Done",
            estimate_tokens=2000,
            actual_tokens=4000,
            metadata=project_task_metadata(first_project),
        )
        first_estimated = db.create_task(
            database_path,
            description="First estimated task",
            status="Estimated",
            estimate_tokens=3000,
            recommended_model="5.4",
            metadata=project_task_metadata(first_project),
        )
        other_done = db.create_task(
            database_path,
            description="Other project done task",
            status="Done",
            estimate_tokens=1000,
            actual_tokens=1000,
            metadata=project_task_metadata(second_project),
        )

        response = client.post(
            f"/projects/{first_project['id']}/tasks/archive-done",
            headers=_portal_headers(),
            follow_redirects=False,
        )
        first_board = client.get(f"/api/projects/{first_project['id']}/board", headers=_portal_headers())
        other_board = client.get(f"/api/projects/{second_project['id']}/board", headers=_portal_headers())

    assert response.status_code == 303
    assert db.get_task(database_path, first_done["id"])["metadata"].get("archived_at")
    assert db.get_task(database_path, second_done["id"])["metadata"].get("archived_at")
    assert not db.get_task(database_path, first_estimated["id"])["metadata"].get("archived_at")
    assert not db.get_task(database_path, other_done["id"])["metadata"].get("archived_at")
    first_json = first_board.json()
    first_descriptions = {
        t["summary"]["text"] for column_tasks in first_json["tasks_by_status"].values() for t in column_tasks
    }
    assert "First done task" not in first_descriptions
    assert "Second done task" not in first_descriptions
    assert "First estimated task" in first_descriptions
    other_json = other_board.json()
    other_descriptions = {
        t["summary"]["text"] for column_tasks in other_json["tasks_by_status"].values() for t in column_tasks
    }
    assert "Other project done task" in other_descriptions
    assert db.estimation_accuracy(database_path)["completed_count"] == 3


def test_unarchive_restores_done_task_to_project_board(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "connected-project")
        task = db.create_task(
            database_path,
            description="Return archived task",
            status="Done",
            estimate_tokens=9000,
            actual_tokens=4500,
            metadata={**project_task_metadata(project), "archived_at": "2099-01-01T00:00:00+00:00"},
        )

        response = client.post(
            f"/projects/{project['id']}/tasks/{task['id']}/unarchive",
            headers=_portal_headers(),
            follow_redirects=False,
        )
        board = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())

    updated = db.get_task(database_path, task["id"])
    assert response.status_code == 303
    assert response.headers["location"] == f"/projects/{project['id']}/task-history"
    assert updated["status"] == "Done"
    assert "archived_at" not in updated["metadata"]
    assert board.status_code == 200
    board_json = board.json()
    task_json = _task_from_board(board_json, task["id"])
    assert task_json["status"] == "Done"
    assert task_json["summary"]["text"] == "Return archived task"
    assert task_json["controls"]["can_archive"] is True


def test_unarchive_restores_blocked_task_to_project_board(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "connected-project")
        task = db.create_task(
            database_path,
            description="Return blocked task",
            status="Blocked",
            estimate_tokens=9000,
            metadata={
                **project_task_metadata(project),
                "blocked_reason": "Needs operator",
                "archived_at": "2099-01-01T00:00:00+00:00",
            },
        )

        response = client.post(
            f"/projects/{project['id']}/tasks/{task['id']}/unarchive",
            headers=_portal_headers(),
            follow_redirects=False,
        )
        board = client.get(f"/api/projects/{project['id']}/board", headers=_portal_headers())

    updated = db.get_task(database_path, task["id"])
    assert response.status_code == 303
    assert response.headers["location"] == f"/projects/{project['id']}/task-history"
    assert updated["status"] == "Estimated"
    assert updated["metadata"]["blocked_reason"] == "Needs operator"
    assert "archived_at" not in updated["metadata"]
    assert board.status_code == 200
    board_json = board.json()
    task_json = _task_from_board(board_json, task["id"])
    assert task_json["status"] == "Estimated"
    assert task_json["blocked_condition"]["reason"] == "Needs operator"
    assert task_json["controls"]["can_archive"] is False
    assert task_json["controls"]["can_dismiss"] is True


def test_archive_rejects_active_non_archivable_tasks(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    project = _connect_project(database_path, tmp_path / "connected-project")
    task_ids = []
    for blocked_status in ["Running", "Review"]:
        task = db.create_task(
            database_path,
            description=f"{blocked_status} task cannot archive",
            status=blocked_status,
            estimate_tokens=9000,
            recommended_model="5.4",
            metadata=project_task_metadata(project),
        )
        task_ids.append(task["id"])

    with _client(tmp_path) as client:
        responses = [
            client.post(
                f"/projects/{project['id']}/tasks/{task_id}/archive",
                headers=_portal_headers(),
                follow_redirects=False,
            )
            for task_id in task_ids
        ]

    for response, task_id in zip(responses, task_ids):
        assert response.status_code == 303
        assert response.headers["location"].startswith(f"/projects/{project['id']}?error=")
        assert "Only Done, Estimated, or blocked Review tasks can be archived or dismissed." in unquote(response.headers["location"])
        assert not db.get_task(database_path, task_id)["metadata"].get("archived_at")
