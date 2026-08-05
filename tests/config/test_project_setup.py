from pathlib import Path
import time

from fastapi.testclient import TestClient

from foreman_ai_hq import db
from foreman_ai_hq.app import create_app
from foreman_ai_hq.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
PORTAL_TOKEN = "test-portal-token"


def _client(tmp_path, *, local_runner_enabled=True):
    settings = Settings(
        database_path=tmp_path / "harness.db",
        guardrails_path=ROOT / "guardrails.yaml",
        local_runner_enabled=local_runner_enabled,
    )
    return TestClient(create_app(settings))


def _headers():
    return {"Authorization": f"Bearer {PORTAL_TOKEN}"}


def _wait_for_worker_run(db_path: Path, task_id: str, status: str | None = None):
    deadline = time.time() + 2
    while time.time() < deadline:
        runs = db.list_worker_runs(db_path, task_id=task_id)
        if runs and (status is None or runs[-1]["status"] == status):
            return runs[-1]
        time.sleep(0.01)
    raise AssertionError("worker run did not reach expected status")


def _project_root(tmp_path: Path) -> Path:
    root = tmp_path / "portal-project"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname = "portal-demo"\ndependencies = ["fastapi"]\n')
    (root / "README.md").write_text("# Portal Demo\n")
    (root / "src").mkdir()
    return root


def test_project_setup_rejects_disabled_local_runner(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    root = _project_root(tmp_path)

    with _client(tmp_path, local_runner_enabled=False) as client:
        response = client.post(
            "/settings/project/connect",
            headers=_headers(),
            json={"root_path": str(root)},
        )

    assert response.status_code == 409
    assert "foremanctl init" in response.json()["detail"]
    assert "foremanctl serve" in response.json()["detail"]


def test_project_pages_explain_current_local_runner_enablement_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)

    with _client(tmp_path, local_runner_enabled=False) as client:
        projects = client.get("/api/projects", headers=_headers())
        settings_project = client.get("/api/settings/project", headers=_headers())

    for response in (projects, settings_project):
        assert response.status_code == 200
        assert response.json()["local_runner_enabled"] is False
    # The enablement guidance itself ("enable Local Runner",
    # ".foreman/config.toml", "foremanctl serve --local-runner",
    # "/settings/control-plane") is pure React copy rendered from the
    # local_runner_enabled flag asserted above -- frontend/src/views/Projects.jsx
    # and frontend/src/views/ProjectSettings.jsx, with no JSON equivalent -- and
    # is not yet covered by frontend/tests/shell.test.mjs. Per design Decision 9
    # / tasks.md task 8.11 that assertion belongs in the frontend suite, which
    # is out of scope for this file (task 8.8 owns only the backend JSON
    # migration). The old ".foreman/secrets.env" exclusion is likewise retired:
    # React never renders that string at all.


def test_project_setup_api_connects_valid_path_and_returns_detected_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    root = _project_root(tmp_path)

    with _client(tmp_path) as client:
        response = client.post(
            "/settings/project/connect",
            headers=_headers(),
            json={"root_path": str(root)},
        )

    assert response.status_code == 200
    project = response.json()["project"]
    assert project["root_path"] == str(root.resolve())
    assert project["profile"]["test_command_suggested"] == "pytest"
    assert project["profile"]["test_command"] is None
    assert project["profile"]["language_hints"] == ["python"]
    assert project["capability"]["state"] == "analysis_ready"


def test_project_setup_api_rejects_invalid_path_with_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)

    with _client(tmp_path) as client:
        response = client.post(
            "/settings/project/connect",
            headers=_headers(),
            json={"root_path": str(tmp_path / "missing")},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "Local project path does not exist."


def test_project_settings_page_displays_profile_and_capability_state(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    root = _project_root(tmp_path)

    with _client(tmp_path) as client:
        client.post("/settings/project/connect", headers=_headers(), json={"root_path": str(root)})
        # /api/settings/project's connected_projects only carry id/name/root_path
        # /capability{state,reasons} -- no profile field -- so the detected
        # profile (test_command, framework hints, docs) and the human-readable
        # capability label live on /api/projects instead, which reuses the same
        # project view model the old Jinja project.html page rendered from.
        response = client.get("/api/projects", headers=_headers())

    assert response.status_code == 200
    projects = response.json()["projects"]
    assert len(projects) == 1
    project = projects[0]
    assert project["name"] == "portal-project"
    assert project["root_path"] == str(root.resolve())
    assert project["capability"]["label"] == "Analysis-ready"
    assert project["profile"]["test_command_suggested"] == "pytest"
    assert project["profile"]["test_command"] is None
    assert "fastapi" in project["profile"]["framework_hints"]
    assert "README.md" in project["profile"]["relevant_docs"]
    # The literal "Projects" page title is static React copy
    # (frontend/src/views/ProjectSettings.jsx) with no backend equivalent.


def test_projects_page_lists_connected_projects_and_open_form(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    root = _project_root(tmp_path)

    with _client(tmp_path) as client:
        empty = client.get("/api/projects", headers=_headers())
        client.post("/settings/project/connect", headers=_headers(), json={"root_path": str(root)})
        listed = client.get("/api/projects", headers=_headers())

    assert empty.status_code == 200
    assert empty.json()["projects"] == []
    assert listed.status_code == 200
    projects = listed.json()["projects"]
    assert len(projects) == 1
    assert projects[0]["name"] == "portal-project"
    assert projects[0]["root_path"] == str(root.resolve())


def test_projects_open_form_redirects_to_project_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    root = _project_root(tmp_path)

    with _client(tmp_path) as client:
        response = client.post(
            "/settings/project/connect?redirect=workspace",
            headers={**_headers(), "accept": "text/html"},
            data={"root_path": str(root)},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/projects/")


def test_project_workspace_displays_profile_capability_and_workflow_links(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    root = _project_root(tmp_path)

    with _client(tmp_path) as client:
        project = client.post("/settings/project/connect", headers=_headers(), json={"root_path": str(root)}).json()["project"]
        db.create_task(tmp_path / "harness.db", description="Running workspace task", status="Running", metadata={"connected_project_id": project["id"]})
        db.create_task(tmp_path / "harness.db", description="Review workspace task", status="Review", metadata={"connected_project_id": project["id"]})
        db.create_task(tmp_path / "harness.db", description="Blocked workspace task", status="Blocked", metadata={"connected_project_id": project["id"], "blocked_reason": "guardrail"})
        response = client.get(f"/api/projects/{project['id']}/workspace", headers=_headers())
        missing = client.get("/api/projects/not-a-project/workspace", headers=_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["name"] == "portal-project"
    assert payload["project"]["root_path"] == str(root.resolve())
    assert payload["summary"]["total_tasks"] == 3
    assert payload["summary"]["counts"]["Estimated"] == 1
    assert payload["project"]["capability"]["label"] == "Analysis-ready"
    action_labels = {a["label"] for a in payload["summary"]["attention_actions"]}
    assert "Worker setup" in action_labels
    assert "Running work" in action_labels
    assert "Review needed" in action_labels
    assert payload["project"]["profile"]["test_command_suggested"] == "pytest"
    assert payload["project"]["profile"]["test_command"] is None
    assert "fastapi" in payload["project"]["profile"]["framework_hints"]
    assert "README.md" in payload["project"]["profile"]["relevant_docs"]
    for href in [f"/projects/{project['id']}", f"/projects/{project['id']}/floor", "/sessions", "/settings/workers", "/settings/project"]:
        assert href in payload["links"].values()
    assert missing.status_code == 404


def test_sidebar_lists_projects_and_marks_active_project(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    first_root = _project_root(tmp_path)
    second_root = tmp_path / "second-project"
    second_root.mkdir()
    (second_root / "pyproject.toml").write_text('[project]\nname = "second-demo"\n')

    with _client(tmp_path) as client:
        first = client.post("/settings/project/connect", headers=_headers(), json={"root_path": str(first_root)}).json()["project"]
        second = client.post("/settings/project/connect", headers=_headers(), json={"root_path": str(second_root)}).json()["project"]
        db.create_task(
            tmp_path / "harness.db",
            description="project task",
            status="Estimated",
            metadata={"connected_project_id": first["id"]},
        )
        dashboard = client.get("/api/dashboard", headers=_headers())
        workspace = client.get(f"/api/projects/{first['id']}/workspace", headers=_headers())
        board = client.get(f"/api/projects/{first['id']}/board", headers=_headers())

    assert dashboard.status_code == 200
    dashboard_projects = {p["id"]: p for p in dashboard.json()["projects"]}
    assert first["id"] in dashboard_projects
    assert second["id"] in dashboard_projects
    assert dashboard_projects[first["id"]]["task_count"] == 1
    # Active-project CSS class and static nav copy are React presentation only.
    assert workspace.status_code == 200
    assert workspace.json()["project"]["id"] == first["id"]
    assert board.status_code == 200
    assert board.json()["project"]["id"] == first["id"]


def test_login_sidebar_does_not_expose_projects_before_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    root = _project_root(tmp_path)

    with _client(tmp_path) as client:
        client.post("/settings/project/connect", headers=_headers(), json={"root_path": str(root)})
        response = client.get("/login")

    assert response.status_code == 200
    assert "portal-project" not in response.text


def test_project_page_shows_read_only_proof_only_when_launch_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    root = _project_root(tmp_path)

    with _client(tmp_path) as client:
        connected = client.post("/settings/project/connect", headers=_headers(), json={"root_path": str(root)}).json()["project"]
        analysis_only = client.get(f"/api/projects/{connected['id']}/workspace", headers=_headers())
        db.mark_worker_adapter_verification(tmp_path / "harness.db", "opencode", verified=True, evidence={"ok": True})
        launch_ready = client.get(f"/api/projects/{connected['id']}/workspace", headers=_headers())

    assert connected["capability"]["state"] == "analysis_ready"
    assert analysis_only.json()["project"]["capability"]["state"] == "analysis_ready"
    assert launch_ready.json()["project"]["capability"]["state"] == "launch_ready"


def test_project_read_only_proof_route_is_retired(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.post("/settings/project/project_DEMO_999/read-only-proof", headers=_headers())

    assert response.status_code == 404
