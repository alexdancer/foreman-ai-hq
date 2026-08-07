"""Invariants that keep the retired Jinja Portal retired.

The autouse ``_react_build_absent`` fixture (``tests/conftest.py``) pins these
tests to a missing build, which is exactly the state that used to render the
duplicated Jinja pages. After retirement it must render the recovery response
instead, and the templates it rendered from must be gone.
"""

from pathlib import Path

import pytest

from foreman_ai_hq import db
from tests.portal.helpers import (
    PORTAL_TOKEN,
    _client,
    _connect_project,
    _portal_headers,
)

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "src" / "foreman_ai_hq" / "templates"

# Canonical React-owned routes that need no fixture to resolve.
BARE_REACT_ROUTES = [
    "/dashboard",
    "/projects",
    "/sessions",
    "/alarms",
    "/setup",
    "/settings/budget",
    "/settings/control-plane",
    "/settings/project",
    "/settings/workers",
]


def _browser_headers():
    """Headers a browser sends.

    ``/alarms`` is content-negotiated: it keeps serving JSON to API pollers and
    only the HTML arm becomes the shell. Without an explicit ``Accept`` a test
    client takes the JSON path and never exercises the surface under test.
    """

    return {**_portal_headers(), "Accept": "text/html"}


def test_only_the_login_template_survives_retirement():
    """Set equality, not membership.

    Asserting ``login.html in listdir`` would pass with every retired template
    still present. Asserting the whole set fails the moment one comes back,
    without needing a route to exercise it.
    """

    present = {path.name for path in TEMPLATES_DIR.glob("*.html")}

    assert present == {"login.html"}


@pytest.mark.parametrize("route", BARE_REACT_ROUTES)
def test_missing_build_returns_recovery_response(tmp_path, monkeypatch, route):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get(route, headers=_browser_headers(), follow_redirects=False)

    assert response.status_code == 503, f"{route} did not return the recovery response"
    assert "not built" in response.text


def test_alarms_json_polling_is_unaffected_by_retirement(tmp_path, monkeypatch):
    """Retirement takes the HTML arm only.

    ``/alarms`` serves JSON to API clients that do not ask for HTML, and that
    contract predates the React migration. A missing build must not break it.
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get(
            "/alarms",
            headers={**_portal_headers(), "Accept": "application/json"},
        )

    assert response.status_code == 200
    assert "alarms" in response.json()


def test_missing_build_returns_recovery_response_for_project_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        project = _connect_project(tmp_path / "harness.db", tmp_path / "repo")
        project_id = project["id"]
        routes = [
            f"/projects/{project_id}",
            f"/projects/{project_id}/needs-you",
            f"/projects/{project_id}/floor",
            f"/projects/{project_id}/task-history",
        ]
        responses = {
            route: client.get(route, headers=_portal_headers(), follow_redirects=False)
            for route in routes
        }

    for route, response in responses.items():
        assert response.status_code == 503, f"{route} did not return the recovery response"


def test_legacy_project_board_redirects_before_missing_build_recovery(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        project = _connect_project(tmp_path / "harness.db", tmp_path / "repo")
        response = client.get(
            f"/projects/{project['id']}/board",
            headers=_portal_headers(),
            follow_redirects=False,
        )

    assert response.status_code == 301
    assert response.headers["location"] == f"/projects/{project['id']}"


def test_missing_build_returns_recovery_response_for_session_report(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        started = client.post(
            "/session/start",
            headers=_portal_headers(),
            json={"task_description": "Retirement", "model": "claude-haiku"},
        ).json()
        response = client.get(
            f"/sessions/{started['session_id']}",
            headers=_portal_headers(),
            follow_redirects=False,
        )

    assert response.status_code == 503


def test_unknown_ids_still_404_before_the_build_check(tmp_path, monkeypatch):
    """A missing build must not turn an unknown id into a recovery response.

    The backend stays authoritative for existence: answering ``503`` here would
    tell an operator "build the frontend" about a project that never existed.
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        responses = [
            client.get(route, headers=_portal_headers(), follow_redirects=False)
            for route in (
                "/projects/does-not-exist",
                "/projects/does-not-exist/board",
                "/projects/does-not-exist/needs-you",
            )
        ]

    assert [response.status_code for response in responses] == [404, 404, 404]


def test_login_still_renders_when_the_build_is_missing(tmp_path, monkeypatch):
    """The Portal Recovery Surface, per portal-local-access.

    This is the scenario "Login survives retirement of the duplicated surfaces",
    which the standalone-portal-recovery-login change wrote for this change.
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/login")

    assert response.status_code == 200
    assert 'name="token"' in response.text
    assert 'action="/login"' in response.text


def test_login_inherits_no_retired_template(tmp_path, monkeypatch):
    """Independence is the recovery surface's whole job."""

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    source = (TEMPLATES_DIR / "login.html").read_text(encoding="utf-8")

    assert "{% extends" not in source
    assert source.lstrip().startswith("<!doctype html>")

    with _client(tmp_path) as client:
        response = client.get("/login")

    # No Portal chrome: the sidebar and logout belong to the authenticated shell.
    assert "sidebar" not in response.text.lower()
    assert "/logout" not in response.text


def test_landing_does_not_inspect_build_availability(tmp_path, monkeypatch):
    """The landing is /dashboard unconditionally; the recovery response lives there.

    Before retirement this redirected to a server-rendered first-project or
    /projects route. There is no longer anywhere to divert to.
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path, portal_auth_required=False) as client:
        _connect_project(tmp_path / "harness.db", tmp_path / "repo")
        root = client.get("/", follow_redirects=False)

    assert root.status_code in (302, 303, 307)
    assert root.headers["location"] == "/dashboard"


def test_authenticated_root_lands_on_dashboard_without_a_build(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        _connect_project(tmp_path / "harness.db", tmp_path / "repo")
        root = client.get("/", headers=_portal_headers(), follow_redirects=False)

    assert root.headers["location"] == "/dashboard"


def test_successful_login_lands_on_dashboard_without_a_build(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        _connect_project(tmp_path / "harness.db", tmp_path / "repo")
        response = client.post(
            "/login", data={"token": PORTAL_TOKEN}, follow_redirects=False
        )

    assert response.headers["location"] == "/dashboard"


def test_app_aliases_redirect_permanently_to_canonical_urls(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        responses = {
            "/app": client.get("/app", headers=_portal_headers(), follow_redirects=False),
            "/app/projects/p1": client.get(
                "/app/projects/p1", headers=_portal_headers(), follow_redirects=False
            ),
            "/app/projects/p1/board": client.get(
                "/app/projects/p1/board", headers=_portal_headers(), follow_redirects=False
            ),
            "/app/projects/p1/floor": client.get(
                "/app/projects/p1/floor", headers=_portal_headers(), follow_redirects=False
            ),
            "/app/projects/p1/board?error=DEMO": client.get(
                "/app/projects/p1/board?error=DEMO", headers=_portal_headers(), follow_redirects=False
            ),
        }

    assert responses["/app"].status_code == 301
    assert responses["/app"].headers["location"] == "/dashboard"
    assert responses["/app/projects/p1"].headers["location"] == "/projects/p1"
    assert responses["/app/projects/p1/board"].headers["location"] == "/projects/p1"
    assert responses["/app/projects/p1/floor"].headers["location"] == "/projects/p1/floor"
    assert responses["/app/projects/p1/board?error=DEMO"].headers["location"] == "/projects/p1?error=DEMO"
    assert all(response.status_code == 301 for response in responses.values())


@pytest.mark.parametrize(
    "route", ["/app/sessions", "/app/alarms", "/app/projects/p1/task-history"]
)
def test_undeclared_app_paths_still_return_not_found(tmp_path, monkeypatch, route):
    """The aliases are a fixed set; retirement must not widen them into a catch-all."""

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get(route, headers=_portal_headers(), follow_redirects=False)

    assert response.status_code == 404


def test_recovery_response_names_the_build_command_and_offers_no_dead_link(
    tmp_path, monkeypatch
):
    """The old copy pointed at /projects, which now returns this same document.

    A recovery page whose only link is the error it is apologizing for is worse
    than one with no link at all.
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/dashboard", headers=_portal_headers())

    assert response.status_code == 503
    assert "npm run build" in response.text
    assert "server-rendered" not in response.text
    assert 'href="/projects"' not in response.text


def test_no_route_renders_a_retired_template(tmp_path, monkeypatch):
    """Route-level proof to complement the directory invariant.

    The directory check alone would pass if a retired template were re-added
    under a new name; this checks the chrome those templates rendered cannot
    reach an operator.
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        project = _connect_project(tmp_path / "harness.db", tmp_path / "repo")
        routes = BARE_REACT_ROUTES + [f"/projects/{project['id']}"]
        bodies = [
            client.get(route, headers=_portal_headers(), follow_redirects=False).text
            for route in routes
        ]

    for body in bodies:
        # base.html's sidebar and footer are the tell that Jinja chrome rendered.
        assert "Open local repo" not in body
        assert "operator-controlled budget governance" not in body
