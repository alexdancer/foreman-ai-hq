"""The not-configured gate blocks orchestration without hiding the audit trail.

ADR-0010: an Orchestrator that is not configured does not operate. But an expired
provider token must not lock an operator out of their own evidence, or out of the
page they need in order to fix the configuration.
"""

import pytest

from tests.portal.helpers import PORTAL_TOKEN, _client, _portal_headers

pytestmark = pytest.mark.unconfigured_orchestrator


BLOCKED = [
    ("post", "/estimate", {"json": {"description": "anything"}}),
    ("post", "/tasks/task_x/launch", {"json": {}}),
    ("post", "/api/projects/proj_x/planning/start", {"json": {}}),
    ("post", "/api/projects/proj_x/planning/message", {"json": {"message": "hi"}}),
    ("post", "/task-breakdowns/bd_x/accept", {"json": {}}),
    ("get", "/projects/proj_x/board/status", {}),
]

REACHABLE = [
    ("get", "/settings/control-plane"),
    ("get", "/api/settings/control-plane"),
    ("get", "/api/setup"),
    ("get", "/api/sessions"),
    ("get", "/api/alarms"),
]


@pytest.mark.parametrize("method,path,kwargs", BLOCKED)
def test_orchestration_is_refused_when_not_configured(tmp_path, monkeypatch, method, path, kwargs):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = getattr(client, method)(path, headers=_portal_headers(), **kwargs)

    assert response.status_code == 503, f"{path} -> {response.status_code}"
    assert "not configured" in response.text


@pytest.mark.parametrize("method,path", REACHABLE)
def test_settings_and_evidence_stay_reachable_when_not_configured(tmp_path, monkeypatch, method, path):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = getattr(client, method)(path, headers=_portal_headers())

    # These surfaces can legitimately 503 for an unrelated reason (the React build
    # is pinned absent in tests), so the claim is specifically that the *gate* did
    # not refuse them — never that they returned 200.
    assert "not configured" not in response.text, f"{path} was gated but must stay reachable"


def test_login_is_reachable_when_not_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/login")
    assert response.status_code == 200


def test_board_directs_the_operator_to_orchestrator_setup(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    from foreman_ai_hq import db

    with _client(tmp_path) as client:
        project = db.upsert_connected_project(
            client.app.state.settings.database_path,
            name="p",
            root_path=str(tmp_path / "p"),
            profile={},
            capability={},
        )
        response = client.get(
            f"/projects/{project['id']}", headers=_portal_headers(), follow_redirects=False
        )

    # An HTML surface gets a page it can act on, not a bare error code.
    assert response.status_code == 303
    assert response.headers["location"] == "/settings/control-plane"
