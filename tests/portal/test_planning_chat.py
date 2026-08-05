import time
from types import SimpleNamespace

import pytest

from foreman_ai_hq import db, intake
from foreman_ai_hq.pi_adapter import PiAuthRequired
from foreman_ai_hq.routes import planning_conversation, react_shell
from tests.portal.helpers import PORTAL_TOKEN, _client, _connect_project, _portal_headers


def _build(tmp_path, *, complete):
    root = tmp_path / ("complete-build" if complete else "partial-build")
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text(
        '<!doctype html><div id="root"></div><script src="/static/react/assets/main.js"></script>',
        encoding="utf-8",
    )
    if complete:
        (root / "assets" / "main.js").write_text("console.log('planning shell')", encoding="utf-8")
    return root


@pytest.mark.parametrize(("complete", "expects_shell"), [(True, True), (False, False)])
def test_planning_chat_serves_shell_or_the_missing_build_recovery_response(
    tmp_path, monkeypatch, complete, expects_shell
):
    """GET /projects/{project_id}/plan behaves like the other project page routes."""

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    db.init_db(tmp_path / "harness.db")
    project = _connect_project(tmp_path / "harness.db", tmp_path / "repo")
    build_dir = _build(tmp_path, complete=complete)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    with _client(tmp_path) as client:
        unauthorized = client.get(f"/projects/{project['id']}/plan")
        response = client.get(f"/projects/{project['id']}/plan", headers=_portal_headers())
        missing = client.get("/projects/missing-DEMO-999/plan", headers=_portal_headers())
    assert unauthorized.status_code == 401
    if expects_shell:
        assert response.status_code == 200
        assert 'id="root"' in response.text
    else:
        assert response.status_code == 503
        assert "not built" in response.text
    assert missing.status_code == 404


def test_only_planning_chat_can_create_tasks_with_intake_provenance(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    db.init_db(tmp_path / "harness.db")
    project = _connect_project(tmp_path / "harness.db", tmp_path / "repo")

    async def _single_task(_request, _source, _metadata):
        return {"decision": "single_task", "reason": "One bounded vertical slice."}

    async def _create_estimated(request, description, *, extra_metadata=None, **_kwargs):
        return db.create_task(
            request.app.state.settings.database_path,
            description=description,
            status="Estimated",
            estimate_tokens=100,
            metadata=extra_metadata,
        )

    monkeypatch.setattr(intake, "run_intake_decision", _single_task)
    monkeypatch.setattr(intake, "_estimate_and_create_task", _create_estimated)

    with _client(tmp_path) as client:
        planning_session, _ = db.create_planning_session(
            client.app.state.settings.database_path,
            task_description="Planning Chat intake test",
            model=client.app.state.settings.orchestrator_model,
            tracking_mode="native_usage",
        )
        registry = client.app.state.planning_registry
        registry._live[project["id"]] = planning_conversation.LiveConversation(
            conv=SimpleNamespace(proc=SimpleNamespace(poll=lambda: None), close=lambda: None),
            planning_session_id=planning_session["id"],
            model=client.app.state.settings.orchestrator_model,
            last_used_at=time.monotonic(),
        )
        created = client.post(
            f"/api/projects/{project['id']}/planning/intake",
            headers=_portal_headers(),
            data={"message": "Add a bounded task"},
        )
        retired = [
            client.post("/tasks", json={"description": "bypass"}),
            client.post("/estimate", json={"description": "bypass"}),
            client.post("/tasks/estimate-form", data={"description": "bypass"}),
            client.post(
                f"/projects/{project['id']}/tasks/estimate-form",
                data={"description": "bypass"},
            ),
        ]

    assert created.status_code == 200
    task = db.list_tasks(tmp_path / "harness.db")[0]
    assert task["metadata"]["intake_decision"] == "single_task"
    assert task["metadata"]["intake_decision_reason"] == "One bounded vertical slice."
    # `/tasks/estimate-form` also matches the surviving dynamic `/tasks/{task_id}`
    # path, so FastAPI reports method-not-allowed rather than not-found for POST.
    assert all(response.status_code in {404, 405} for response in retired)
    assert len(db.list_tasks(tmp_path / "harness.db")) == 1


def test_planning_start_surfaces_provider_auth_required_instead_of_a_dead_turn(tmp_path, monkeypatch):
    """Absent/expired provider auth must reach the operator as an actionable sign-in state."""

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    db.init_db(tmp_path / "harness.db")
    project = _connect_project(tmp_path / "harness.db", tmp_path / "repo")

    def _no_provider_auth(*args, **kwargs):
        raise PiAuthRequired("Provider authentication required; run `pi /login` or add an API key in pi.")

    monkeypatch.setattr(planning_conversation, "open_pi_conversation", _no_provider_auth)

    with _client(tmp_path) as client:
        response = client.post(
            f"/api/projects/{project['id']}/planning/start", headers=_portal_headers()
        )

    assert response.status_code == 401
    detail = response.json()["detail"]
    assert "provider" in detail.lower()
    assert "pi /login" in detail
    assert "planning_session_id" not in response.text


def test_planning_message_surfaces_provider_auth_expiring_mid_conversation(tmp_path, monkeypatch):
    """Provider auth can expire between turns; that turn must still reach the sign-in state."""

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    db.init_db(tmp_path / "harness.db")
    project = _connect_project(tmp_path / "harness.db", tmp_path / "repo")

    class _ExpiredAuthConversation:
        proc = SimpleNamespace(poll=lambda: None)

        def prompt(self, text, **kwargs):
            raise PiAuthRequired("Provider authentication required; run `pi /login` or add an API key in pi.")

        def close(self):
            """No subprocess to tear down; app shutdown closes every held conversation."""

    with _client(tmp_path) as client:
        registry = client.app.state.planning_registry
        registry._live[project["id"]] = planning_conversation.LiveConversation(
            conv=_ExpiredAuthConversation(),
            planning_session_id="sess_planning_test",
            model=client.app.state.settings.orchestrator_model,
            last_used_at=time.monotonic(),
        )
        response = client.post(
            f"/api/projects/{project['id']}/planning/message",
            headers=_portal_headers(),
            json={"message": "plan this"},
        )

    assert response.status_code == 401
    assert "pi /login" in response.json()["detail"]
