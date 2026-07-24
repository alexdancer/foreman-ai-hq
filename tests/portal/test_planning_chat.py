import pytest

from foreman_ai_hq import db
from foreman_ai_hq.routes import react_shell
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
