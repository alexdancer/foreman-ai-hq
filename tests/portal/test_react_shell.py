import json
import os
from dataclasses import replace
from pathlib import Path

import pytest

from foreman_ai_hq import db
from foreman_ai_hq.pi_adapter import (
    OrchestratorModelDiscoveryResult,
    OrchestratorVerificationResult,
)
from foreman_ai_hq.project_context import project_task_metadata
from foreman_ai_hq.routes import portal, react_shell
from tests.conftest import TEST_ORCHESTRATOR_MODEL
from tests.portal.helpers import (
    PORTAL_TOKEN,
    _client,
    _client_with_control_plane_llm,
    _connect_project,
    _portal_headers,
    FakeControlPlaneLLM,
)


def _build_react_assets(tmp_path):
    build_dir = tmp_path / "react_build"
    (build_dir / "assets").mkdir(parents=True)
    (build_dir / "index.html").write_text(
        '<!doctype html><div id="root"></div>'
        '<script type="module" src="/static/react/assets/main.js"></script>',
        encoding="utf-8",
    )
    (build_dir / "assets" / "main.js").write_text(
        "console.log('react shell');", encoding="utf-8"
    )
    return build_dir


def _build_partial_react_assets(tmp_path):
    build_dir = tmp_path / "partial_react_build"
    build_dir.mkdir(parents=True)
    (build_dir / "index.html").write_text(
        '<!doctype html><div id="root"></div>'
        '<script type="module" src="/static/react/assets/missing.js"></script>',
        encoding="utf-8",
    )
    return build_dir


def _build_mixed_quote_partial_react_assets(tmp_path):
    build_dir = tmp_path / "mixed_quote_partial_react_build"
    (build_dir / "assets").mkdir(parents=True)
    (build_dir / "index.html").write_text(
        '<!doctype html><div id="root"></div>'
        '<script type="module" src="/static/react/assets/main.js"></script>'
        "<link rel='stylesheet' href='/static/react/assets/missing.css'>",
        encoding="utf-8",
    )
    (build_dir / "assets" / "main.js").write_text(
        "console.log('react shell');", encoding="utf-8"
    )
    return build_dir


def test_react_shell_served_when_built(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "shell-repo")
        shells = [
            client.get(path, headers=_portal_headers())
            for path in (
                "/dashboard",
                "/projects",
                f"/projects/{project['id']}",
                f"/projects/{project['id']}/board",
                f"/projects/{project['id']}/floor",
            )
        ]
        asset = client.get("/static/react/assets/main.js")

    assert all(shell.status_code == 200 for shell in shells)
    assert all('id="root"' in shell.text for shell in shells)
    assert asset.status_code == 200
    assert "react shell" in asset.text


def test_project_board_redirects_to_pipeline_and_floor_checks_project(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "two-surface-repo")
        legacy = client.get(
            f"/projects/{project['id']}/board",
            headers=_portal_headers(),
            follow_redirects=False,
        )
        floor = client.get(f"/projects/{project['id']}/floor", headers=_portal_headers())
        missing = client.get(
            "/projects/does-not-exist/floor",
            headers=_portal_headers(),
            follow_redirects=False,
        )

    assert legacy.status_code == 301
    assert legacy.headers["location"] == f"/projects/{project['id']}"
    assert floor.status_code == 200
    assert missing.status_code == 404


@pytest.mark.parametrize(("complete", "expected_status"), [(True, 200), (False, 503)])
def test_canonical_needs_you_route_uses_the_authenticated_shell_or_recovery_boundary(
    tmp_path, monkeypatch, complete, expected_status
):
    """Needs You owns one project route and validates project existence before build state."""

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path) if complete else _build_partial_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "needs-you-route-repo")
        unauthorized = client.get(f"/projects/{project['id']}/needs-you")
        response = client.get(
            f"/projects/{project['id']}/needs-you", headers=_portal_headers()
        )
        missing = client.get(
            "/projects/missing-DEMO-999/needs-you", headers=_portal_headers()
        )
        app_alias = client.get(
            f"/app/projects/{project['id']}/needs-you",
            headers=_portal_headers(),
            follow_redirects=False,
        )

    assert unauthorized.status_code == 401
    assert response.status_code == expected_status
    if complete:
        assert 'id="root"' in response.text
    else:
        assert "not built" in response.text
    assert missing.status_code == 404
    assert app_alias.status_code == 404


def test_needs_you_aggregates_project_decisions_and_drives_nav_badge(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "needs-you-repo")
        metadata = project_task_metadata(project)
        db.create_task_breakdown(
            database_path,
            source_text="DEMO proposed breakdown 2099",
            source_sha256="9" * 64,
            intake_metadata={
                "connected_project_id": project["id"],
                "source_name": "DEMO_INTAKE_2099_999.md",
            },
            status="pending_review",
            decision="multi_task",
            model="demo-model",
            candidates=[{"summary": "DEMO candidate 2099"}],
        )
        task_specs = [
            ("manual estimate", "Estimated", {"requires_manual_estimate": True, "blocked_condition": {"reason": "Estimate required", "origin": "estimation", "timestamp": "2099-01-01T00:00:00Z"}}),
            ("launch guardrail", "Estimated", {"blocked_condition": {"reason": "Worker setup required", "origin": "launch_guardrail", "timestamp": "2099-01-01T00:00:00Z"}}),
            ("review disposition", "Review", {}),
            ("budget approval", "Estimated", {"budget_override_available": True, "blocked_condition": {"reason": "Budget approval required", "origin": "budget_guardrail", "timestamp": "2099-01-01T00:00:00Z"}}),
        ]
        for description, status_value, extra in task_specs:
            db.create_task(
                database_path,
                description=f"DEMO {description} 2099",
                status=status_value,
                estimate_tokens=999,
                recommended_model="demo-model",
                metadata={**metadata, **extra},
            )
        other = _connect_project(database_path, tmp_path / "other-needs-you-repo")
        db.create_task(
            database_path,
            description="DEMO other project review 2099",
            status="Review",
            estimate_tokens=999,
            recommended_model="demo-model",
            metadata=project_task_metadata(other),
        )

        response = client.get(
            f"/api/projects/{project['id']}/needs-you", headers=_portal_headers()
        )
        nav = client.get("/api/portal/nav", headers=_portal_headers()).json()

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 5
    assert [item["kind"] for item in payload["items"]] == [
        "breakdown_review",
        "manual_estimate",
        "launch_guardrail",
        "review_disposition",
        "budget_override",
    ]
    assert {
        key: payload["items"][0][key]
        for key in ("source", "candidate_count", "status")
    } == {
        "source": "DEMO_INTAKE_2099_999.md",
        "candidate_count": 1,
        "status": "pending_review",
    }
    assert payload["items"][0]["created_at"]
    nav_project = next(item for item in nav["sidebar_projects"] if item["id"] == project["id"])
    assert nav_project["needs_you_count"] == payload["count"]


@pytest.mark.parametrize(
    "path",
    [
        "/app/settings",
        "/app/not-a-migrated-route",
        "/app/projects/demo-999/extra",
        "/app/projects/demo-999/board/extra",
    ],
)
def test_react_shell_rejects_unknown_routes(path, tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)

    with _client(tmp_path) as client:
        response = client.get(path, headers=_portal_headers())

    assert response.status_code == 404


def test_react_shell_reports_missing_build(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    empty_dir = tmp_path / "no_build"
    empty_dir.mkdir()
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: empty_dir)
    with _client(tmp_path) as client:
        response = client.get("/dashboard", headers=_portal_headers())

    assert response.status_code == 503
    assert "not built" in response.text
    # Never a silent blank shell.
    assert "<h1>" in response.text


def test_partial_react_build_returns_recovery_without_blank_shell(tmp_path, monkeypatch):
    """A partial build is still a missing build.

    Every entry point lands on /dashboard and gets the recovery response there.
    Before retirement these redirected to a server-rendered /projects landing.
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_partial_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)

    with _client(tmp_path, portal_auth_required=False) as client:
        root = client.get("/", follow_redirects=False)
        login_form = client.get("/login", follow_redirects=False)
        login_submit = client.post(
            "/login",
            data={"token": "unused-DEMO-999"},
            follow_redirects=False,
        )
        logout = client.post("/logout", follow_redirects=False)
        landing = client.get(root.headers["location"])

    with _client(tmp_path) as client:
        login = client.post(
            "/login", data={"token": PORTAL_TOKEN}, follow_redirects=False
        )
        authenticated_root = client.get("/", follow_redirects=False)

    assert root.headers["location"] == "/dashboard"
    assert login_form.headers["location"] == "/dashboard"
    assert login_submit.headers["location"] == "/dashboard"
    assert logout.headers["location"] == "/dashboard"
    assert login.status_code == 303
    assert login.headers["location"] == "/dashboard"
    assert authenticated_root.headers["location"] == "/dashboard"
    # The landing itself reports the partial build rather than promoting it.
    assert landing.status_code == 503
    assert "not built" in landing.text


def test_partial_build_landing_ignores_connected_projects(tmp_path, monkeypatch):
    """A connected project no longer changes the landing.

    This replaces the connected-project fallback: the landing used to pick the
    first project's route when the build was incomplete. There is no longer a
    server-rendered destination to pick.
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_partial_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    database_path = tmp_path / "harness.db"

    with _client(tmp_path, portal_auth_required=False) as client:
        _connect_project(database_path, tmp_path / "partial-fallback-repo")
        no_auth_responses = [
            client.get("/", follow_redirects=False),
            client.get("/login", follow_redirects=False),
            client.post(
                "/login",
                data={"token": "unused-DEMO-999"},
                follow_redirects=False,
            ),
            client.post("/logout", follow_redirects=False),
        ]

    with _client(tmp_path) as client:
        login = client.post(
            "/login", data={"token": PORTAL_TOKEN}, follow_redirects=False
        )
        authenticated_root = client.get("/", follow_redirects=False)

    assert all(response.headers["location"] == "/dashboard" for response in no_auth_responses)
    assert login.headers["location"] == "/dashboard"
    assert authenticated_root.headers["location"] == "/dashboard"


def test_mixed_quote_missing_asset_rejects_partial_build(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_mixed_quote_partial_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)

    with _client(tmp_path, portal_auth_required=False) as client:
        root = client.get("/", follow_redirects=False)
        dashboard = client.get("/dashboard")

    assert root.headers["location"] == "/dashboard"
    assert dashboard.status_code == 503


def test_auth_disabled_root_uses_react_when_built(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    with _client(tmp_path, portal_auth_required=False) as client:
        root = client.get("/", follow_redirects=False)

    assert root.status_code in (302, 307)
    assert root.headers["location"] == "/dashboard"


def test_auth_disabled_login_and_logout_use_react_when_built(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)

    with _client(tmp_path, portal_auth_required=False) as client:
        login_form = client.get("/login", follow_redirects=False)
        login_submit = client.post(
            "/login",
            data={"token": "unused-DEMO-999"},
            follow_redirects=False,
        )
        logout = client.post("/logout", follow_redirects=False)

    assert login_form.headers["location"] == "/dashboard"
    assert login_submit.headers["location"] == "/dashboard"
    assert logout.headers["location"] == "/dashboard"


def test_authenticated_root_uses_react_when_built(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    with _client(tmp_path) as client:
        login = client.post(
            "/login", data={"token": PORTAL_TOKEN}, follow_redirects=False
        )
        root = client.get("/", follow_redirects=False)

    assert login.status_code == 303
    assert root.status_code in (302, 307)
    assert root.headers["location"] == "/dashboard"


@pytest.mark.parametrize(
    "build_helper",
    [_build_react_assets, _build_partial_react_assets],
)
def test_react_build_availability_never_bypasses_root_auth(
    build_helper,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = build_helper(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)

    with _client(tmp_path) as client:
        root = client.get("/", follow_redirects=False)

    assert root.status_code in (302, 307)
    assert root.headers["location"] == "/login"


# The three build-aware landing fallback tests that lived here asserted the
# retired contract: that a missing build diverted the landing to a
# server-rendered /projects or first-project route. The landing no longer
# inspects build availability, and test_jinja_retirement.py covers the
# replacement for every entry point (root, authenticated root, successful
# login, logout) plus the connected-project case.


def test_login_redirects_to_react_when_built(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    with _client(tmp_path) as client:
        login = client.post(
            "/login", data={"token": PORTAL_TOKEN}, follow_redirects=False
        )

    assert login.status_code == 303
    assert login.headers["location"] == "/dashboard"
    assert "foreman_ai_hq_portal" in login.headers.get("set-cookie", "")


def test_built_react_and_valid_cookie_lands_on_app(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "repo")
        # Perform a real login so the signed cookie is set on the client.
        login = client.post(
            "/login", data={"token": PORTAL_TOKEN}, follow_redirects=False
        )
        assert login.status_code == 303
        assert "foreman_ai_hq_portal" in login.headers.get("set-cookie", "")
        root = client.get("/", follow_redirects=False)
        landing = client.get(root.headers["location"], follow_redirects=False)

    assert project["id"]
    assert login.headers["location"] == "/dashboard"
    assert root.status_code in (302, 307)
    assert root.headers["location"] == "/dashboard"
    assert landing.status_code == 200
    assert 'id="root"' in landing.text


def _build_missing_react_assets(tmp_path):
    empty_dir = tmp_path / "no_build"
    empty_dir.mkdir()
    return empty_dir


def test_partial_build_is_never_promoted_on_any_canonical_route(tmp_path, monkeypatch):
    """A build with a missing referenced asset is treated as no build at all.

    This consolidates six per-route tests that each asserted their canonical URL
    kept rendering Jinja under a partial build. The Jinja pages are retired, but
    the property they were protecting is not: a half-built shell must never be
    served, because it fails silently in the browser rather than loudly here.
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_partial_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    session = db.create_session(
        database_path,
        task_description="DEMO partial build 2099",
        model="demo-model-999",
        session_key_hash="s" * 64,
        guardrail_overrides={},
    )

    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "partial-repo")
        routes = [
            "/sessions",
            f"/sessions/{session['id']}",
            f"/projects/{project['id']}/task-history",
            "/settings/budget",
            "/settings/control-plane",
            "/settings/workers",
            "/setup",
        ]
        responses = {
            route: client.get(route, headers=_portal_headers()) for route in routes
        }

    for route, response in responses.items():
        assert response.status_code == 503, f"{route} promoted a partial build"
        assert "not built" in response.text
        assert 'id="root"' not in response.text


@pytest.mark.parametrize(
    "build_helper,auth_required,expect_react",
    [
        (_build_react_assets, False, True),
        (_build_partial_react_assets, False, False),
        (_build_missing_react_assets, False, False),
        (_build_react_assets, True, True),
        (_build_partial_react_assets, True, False),
        (_build_missing_react_assets, True, False),
    ],
)
def test_canonical_routing_matrix(
    build_helper,
    auth_required,
    expect_react,
    tmp_path,
    monkeypatch,
):
    """Auth-required x build-state, across every entry point.

    The landing is /dashboard in all six cells: it no longer inspects build
    availability, because there is no server-rendered destination to divert to.
    The build state decides only what /dashboard itself then returns — the shell
    or the recovery response.
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = build_helper(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    database_path = tmp_path / "harness.db"

    client = _client(tmp_path, portal_auth_required=auth_required)
    with client:
        # A connected project exists precisely to prove it no longer steers the
        # landing the way the retired first-project fallback did.
        _connect_project(database_path, tmp_path / "routing-repo")
        if auth_required:
            login = client.post(
                "/login", data={"token": PORTAL_TOKEN}, follow_redirects=False
            )
            assert login.status_code == 303
            assert login.headers["location"] == "/dashboard"
        else:
            login_form = client.get("/login", follow_redirects=False)
            login_submit = client.post(
                "/login",
                data={"token": "unused-DEMO-999"},
                follow_redirects=False,
            )
            logout = client.post("/logout", follow_redirects=False)
            assert login_form.headers["location"] == "/dashboard"
            assert login_submit.headers["location"] == "/dashboard"
            assert logout.headers["location"] == "/dashboard"

        root = client.get("/", follow_redirects=False)
        dashboard = client.get("/dashboard")
        projects = client.get("/projects")

    assert root.status_code in (302, 307)
    assert root.headers["location"] == "/dashboard"

    if expect_react:
        assert dashboard.status_code == 200
        assert 'id="root"' in dashboard.text
        assert projects.status_code == 200
        assert 'id="root"' in projects.text
    else:
        assert dashboard.status_code == 503
        assert "not built" in dashboard.text
        assert projects.status_code == 503
        assert "not built" in projects.text


def test_global_board_redirects_to_pipeline(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"

    with _client(tmp_path, portal_auth_required=False) as client:
        no_project = client.get("/board", follow_redirects=False)
        project = _connect_project(database_path, tmp_path / "repo")
        with_project = client.get("/board", follow_redirects=False)

    assert no_project.status_code in (302, 303, 307)
    assert no_project.headers["location"] == "/projects"
    assert with_project.status_code in (302, 303, 307)
    assert with_project.headers["location"] == f"/projects/{project['id']}"


@pytest.mark.parametrize(
    "build_helper,expect_react",
    [
        (_build_react_assets, True),
        (_build_partial_react_assets, False),
        (_build_missing_react_assets, False),
    ],
)
def test_canonical_project_workspace_and_board_routing(
    build_helper, expect_react, tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = build_helper(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    database_path = tmp_path / "harness.db"

    with _client(tmp_path, portal_auth_required=False) as client:
        project = _connect_project(database_path, tmp_path / "routing-repo")
        workspace = client.get(f"/projects/{project['id']}")
        board = client.get(f"/projects/{project['id']}/board")

    if expect_react:
        assert workspace.status_code == 200
        assert 'id="root"' in workspace.text
        assert board.status_code == 200
        assert 'id="root"' in board.text
    else:
        assert workspace.status_code == 503
        assert "not built" in workspace.text
        assert board.status_code == 503
        assert "not built" in board.text


def test_unknown_project_returns_404_at_canonical_routes_in_both_build_states(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)

    with _client(tmp_path) as client:
        workspace = client.get("/projects/missing-DEMO-999", headers=_portal_headers())
        board = client.get(
            "/projects/missing-DEMO-999/board", headers=_portal_headers()
        )

    assert workspace.status_code == 404
    assert 'id="root"' not in workspace.text
    assert board.status_code == 404
    assert 'id="root"' not in board.text


def test_archived_legacy_board_redirects_to_pipeline_in_every_build_state(
    tmp_path, monkeypatch
):
    """Legacy board redirects; canonical Pipeline owns build recovery and Restore."""

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"

    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "archived-board-repo")
        db.archive_connected_project(database_path, project["id"])

        build_dir = _build_react_assets(tmp_path)
        monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
        built = client.get(f"/projects/{project['id']}/board", headers=_portal_headers())

        build_dir = _build_missing_react_assets(tmp_path)
        monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
        missing = client.get(
            f"/projects/{project['id']}/board", headers=_portal_headers(), follow_redirects=False
        )

    assert built.status_code == 200
    assert 'id="root"' in built.text
    assert missing.status_code == 301
    assert missing.headers["location"] == f"/projects/{project['id']}"


def test_every_canonical_route_serves_the_shell_when_built(tmp_path, monkeypatch):
    """The full canonical route inventory, proven against a built shell.

    This began as proof that non-migrated Jinja routes stayed reachable. There
    are no non-migrated routes left, so the inventory now proves the opposite
    and more useful thing: React serves every one of them. The missing-build
    half of this matrix lives in test_jinja_retirement.py.
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)

    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "jinja-fallback-repo")
        session = db.create_session(
            database_path,
            task_description="DEMO session report 999",
            model="DEMO-model-999",
            session_key_hash="DEMO-hash-999",
            guardrail_overrides={},
            status="completed",
        )
        breakdown = db.create_task_breakdown(
            database_path,
            source_text="# DEMO breakdown 999",
            source_sha256="DEMO-sha-999",
            intake_metadata={},
            status="pending_review",
            decision="single_task",
            model="DEMO-model-999",
            candidates=[],
        )
        headers = {**_portal_headers(), "Accept": "text/html"}
        paths = [
            "/dashboard",
            "/projects",
            f"/projects/{project['id']}",
            f"/projects/{project['id']}/board",
            "/sessions",
            f"/sessions/{session['id']}",
            "/alarms",
            "/setup",
            "/settings/control-plane",
            "/settings/budget",
            "/settings/project",
            "/settings/workers",
            f"/projects/{project['id']}/task-history",
            f"/task-breakdowns/{breakdown['id']}/review",
        ]
        responses = {path: client.get(path, headers=headers) for path in paths}

    assert {path: response.status_code for path, response in responses.items()} == {
        path: 200 for path in paths
    }
    # Every one is the shell, not a server-rendered page.
    for path, response in responses.items():
        assert 'id="root"' in response.text, f"{path} did not serve the React shell"


def test_react_projects_endpoint_requires_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/api/projects")

    assert response.status_code == 401


def test_react_projects_endpoint_lists_connected_projects(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "repo")
        response = client.get("/api/projects", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["projects"]) == 1
    listed = payload["projects"][0]
    assert listed["id"] == project["id"]
    assert listed["name"] == project["name"]
    assert set(listed["counts"]) == {
        "Estimated",
        "Running",
        "Review",
        "Done",
    }
    assert listed["total_tasks"] == sum(listed["counts"].values())


def test_react_projects_endpoint_empty_list(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/api/projects", headers=_portal_headers())

    assert response.status_code == 200
    assert response.json() == {
        "projects": [],
        "archived_projects": [],
        "local_runner_enabled": True,
    }


def test_react_projects_endpoint_includes_archived_and_local_runner_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path, local_runner_enabled=False) as client:
        active = _connect_project(database_path, tmp_path / "active-repo")
        archived = _connect_project(database_path, tmp_path / "archived-repo")
        db.archive_connected_project(database_path, archived["id"])
        response = client.get("/api/projects", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"projects", "archived_projects", "local_runner_enabled"}
    assert payload["local_runner_enabled"] is False
    assert len(payload["projects"]) == 1
    assert len(payload["archived_projects"]) == 1
    assert payload["projects"][0]["id"] == active["id"]
    assert payload["projects"][0]["name"] == active["name"]
    assert payload["archived_projects"][0]["id"] == archived["id"]
    assert payload["archived_projects"][0]["name"] == archived["name"]
    assert payload["archived_projects"][0]["archived_at"] is not None
    assert set(payload["archived_projects"][0]) == {"id", "name", "root_path", "archived_at", "capability"}
    assert set(payload["archived_projects"][0]["capability"]) == {"state", "label", "reasons"}


def test_react_projects_endpoint_active_array_fields_unchanged(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "repo")
        db.create_task(
            database_path,
            description="board task",
            status="Estimated",
            metadata={"connected_project_id": project["id"]},
        )
        response = client.get("/api/projects", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["projects"][0]["id"] == project["id"]
    assert set(payload["projects"][0]) == {
        "id", "name", "root_path", "profile", "capability", "backend_id",
        "archived_at", "archived_by", "created_at", "updated_at", "counts", "total_tasks",
    }
    assert set(payload["projects"][0]["counts"]) == {
        "Estimated", "Running", "Review", "Done",
    }
    assert payload["projects"][0]["total_tasks"] == sum(payload["projects"][0]["counts"].values())


def test_react_projects_endpoint_archived_capability_reasons_are_safe(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        archived = _connect_project(database_path, tmp_path / "archived-repo")
        db.archive_connected_project(database_path, archived["id"])
        monkeypatch.setattr(
            "foreman_ai_hq.execution_backend.LocalExecutionBackend.project_capability",
            lambda self, project: {
                "state": "blocked",
                "label": "Blocked",
                "reasons": ["password=LEAKED_SECRET_999"],
            },
        )
        response = client.get("/api/projects", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["archived_projects"]) == 1
    assert "LEAKED_SECRET_999" not in response.text
    assert "***REDACTED***" in response.text
    assert payload["archived_projects"][0]["capability"]["reasons"] == ["***REDACTED***"]


def test_react_projects_endpoint_archived_absent_capability_values_are_typed_null(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        archived = _connect_project(database_path, tmp_path / "archived-repo")
        db.archive_connected_project(database_path, archived["id"])
        monkeypatch.setattr(
            "foreman_ai_hq.execution_backend.LocalExecutionBackend.project_capability",
            lambda self, project: {"state": None, "label": None, "reasons": None},
        )
        response = client.get("/api/projects", headers=_portal_headers())

    assert response.status_code == 200
    capability = response.json()["archived_projects"][0]["capability"]
    assert capability == {"state": "unknown", "label": None, "reasons": None}


def test_react_dashboard_endpoint_requires_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/api/dashboard")

    assert response.status_code == 401


def test_react_dashboard_projection_is_safe_and_bounded(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "repo")
        session = db.create_session(
            database_path,
            task_description="React dashboard active session",
            model="opencode/gpt-5.1",
            session_key_hash="dashboard-secret-hash",
            guardrail_overrides={"private": "do-not-return"},
            status="running",
        )
        db.record_token_turn(
            database_path,
            session_id=session["id"],
            model="opencode/gpt-5.1",
            prompt_tokens=100,
            completion_tokens=50,
            cost=0.01,
            raw_usage={
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
                "private": "do-not-return",
            },
        )
        db.record_alarm(
            database_path,
            session_id=session["id"],
            alarm={
                "id": "react-dashboard-open",
                "type": "BUDGET_YELLOW",
                "severity": "LOW",
                "context": {"private": "do-not-return"},
                "recommended_action": "Review spend.",
            },
        )
        db.record_alarm(
            database_path,
            session_id=session["id"],
            alarm={
                "id": "react-dashboard-resolved",
                "type": "BUDGET_RED",
                "severity": "HIGH",
                "context": {},
                "recommended_action": "Stop launches.",
            },
        )
        db.resolve_alarm(
            database_path,
            alarm_id="react-dashboard-resolved",
            action="continue",
        )
        db.create_task(
            database_path,
            description="Accuracy parity",
            status="Done",
            estimate_tokens=100,
            actual_tokens=150,
        )

        api = client.get("/api/dashboard", headers=_portal_headers())

    assert api.status_code == 200
    payload = api.json()
    assert set(payload) == {
        "next_actions",
        "budget",
        "worker_execution",
        "spend",
        "alarms",
        "active_sessions",
        "estimation_accuracy",
        "estimation_coefficients",
        "needs_you",
        "projects",
    }
    assert set(payload["next_actions"][0]) == {"label", "detail", "href", "tone"}
    assert set(payload["budget"]) == {"total_tokens", "daily_cap", "current_zone", "since"}
    assert set(payload["worker_execution"]) == {"token_total", "status_split", "components"}
    assert set(payload["worker_execution"]["status_split"]) == {
        "completed",
        "failed_retry",
        "unknown",
    }
    assert set(payload["worker_execution"]["components"]) == {"available", "items", "cost"}
    component_items = payload["worker_execution"]["components"]["items"]
    assert component_items
    assert all(set(item) == {"label", "value"} for item in component_items)
    assert set(payload["spend"]) == {
        "worker_execution",
        "orchestration",
        "agent_review_reporting",
        "planning_estimation",
        "setup_verification",
        "other",
        "pricing_coverage",
        "cost_by_category",
        "total_cost",
        "priced_tokens",
        "unpriced_tokens",
    }
    assert set(payload["spend"]["pricing_coverage"]) == {
        "worker_execution",
        "agent_review_reporting",
        "planning_estimation",
        "setup_verification",
        "other",
        "orchestration",
        "total",
    }
    assert set(payload["spend"]["pricing_coverage"]["worker_execution"]) == {
        "state",
        "cost",
        "priced_tokens",
        "unpriced_tokens",
        "coverage_percent",
    }
    assert set(payload["spend"]["cost_by_category"]) == {
        "control_plane",
        "task_breakdown",
        "worker_execution",
        "adapter_verification",
        "reporting_summary",
        "other",
    }
    assert payload["spend"]["cost_by_category"]["worker_execution"] == 0.01
    assert payload["spend"]["total_cost"] == 0.01
    assert payload["spend"]["priced_tokens"] == 150
    assert payload["spend"]["unpriced_tokens"] == 0
    assert set(payload["alarms"]) == {"total", "open", "critical", "recent"}
    assert payload["budget"]["total_tokens"] == 150
    assert payload["worker_execution"]["token_total"] == 150
    assert payload["active_sessions"] == [
        {
            "id": session["id"],
            "task_description": "React dashboard active session",
            "model": "opencode/gpt-5.1",
            "status": "running",
        }
    ]
    assert payload["alarms"]["recent"] == [
        {
            "id": "react-dashboard-open",
            "type": "BUDGET_YELLOW",
            "severity": "LOW",
            "session_id": session["id"],
            "recommended_action": "Review spend.",
        }
    ]
    assert payload["estimation_accuracy"] == {
        "completed_count": 1,
        "median_error_ratio": 1.5,
        "within_2x_pct": 100.0,
    }
    assert payload["projects"][0]["id"] == project["id"]
    assert payload["projects"][0]["name"] == project["name"]
    assert payload["projects"][0]["task_count"] == 0
    assert payload["projects"][0]["needs_you_count"] == 0
    assert set(payload["projects"][0]) == {"id", "name", "task_count", "needs_you_count", "capability"}
    assert set(payload["projects"][0]["capability"]) == {"state"}
    assert payload["needs_you"] == {"count": 0, "project_count": 1, "projects_with_needs_you": 0}
    assert set(payload["estimation_coefficients"]) == {"available", "scope", "factors"}
    assert payload["estimation_coefficients"]["available"] is True
    assert all(
        set(factor) == {"key", "label", "value", "provenance"}
        for factor in payload["estimation_coefficients"]["factors"]
    )
    serialized = json.dumps(payload)
    assert "dashboard-secret-hash" not in serialized
    assert "do-not-return" not in serialized
    assert "root_path" not in serialized
    # These previously round-tripped through the Jinja dashboard, which acted as
    # the oracle for "both surfaces read one calculation". That page is retired,
    # so the same claims are asserted against the projection directly.
    recent_alarm_ids = [alarm["id"] for alarm in payload["alarms"]["recent"]]
    assert "react-dashboard-open" in recent_alarm_ids
    assert "react-dashboard-resolved" not in recent_alarm_ids
    assert payload["next_actions"]
    assert payload["budget"]["since"]


def test_react_dashboard_previews_are_newest_first_bounded_and_unresolved(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    sessions = []
    with _client(tmp_path) as client:
        for index in range(6):
            session = db.create_session(
                database_path,
                task_description=f"Dashboard session {index}",
                model="opencode/gpt-5.1",
                session_key_hash=f"dashboard-hash-{index}",
                guardrail_overrides={},
                status="running",
            )
            sessions.append(session)
            db.record_alarm(
                database_path,
                session_id=session["id"],
                alarm={
                    "id": f"dashboard-alarm-{index}",
                    "type": "BUDGET_YELLOW",
                    "severity": "LOW",
                    "context": {},
                    "recommended_action": "Review spend.",
                },
            )
        with db.connect(database_path) as conn:
            for index, session in enumerate(sessions):
                timestamp = f"2099-01-01T00:00:0{index}+00:00"
                conn.execute("update sessions set started_at = ? where id = ?", (timestamp, session["id"]))
                conn.execute(
                    "update alarms set created_at = ? where id = ?",
                    (timestamp, f"dashboard-alarm-{index}"),
                )
        db.resolve_alarm(
            database_path,
            alarm_id="dashboard-alarm-0",
            action="continue",
        )
        response = client.get("/api/dashboard", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["active_sessions"]] == [
        session["id"] for session in reversed(sessions[1:])
    ]
    assert [item["id"] for item in payload["alarms"]["recent"]] == [
        f"dashboard-alarm-{index}" for index in range(5, 0, -1)
    ]


def test_react_json_endpoints_require_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        dashboard = client.get("/api/dashboard")
        workspace = client.get("/api/projects/1/workspace")
        board = client.get("/api/projects/1/board")
        shell = client.get("/app/projects/1")

    assert dashboard.status_code == 401
    assert workspace.status_code == 401
    assert board.status_code == 401
    assert shell.status_code == 401


def test_react_workspace_state_reuses_project_helpers(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "repo")
        response = client.get(
            f"/api/projects/{project['id']}/workspace", headers=_portal_headers()
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["id"] == project["id"]
    assert set(payload["summary"]["counts"]) == {
        "Estimated",
        "Running",
        "Review",
        "Done",
    }
    assert "launch_ready" in payload["summary"]


def test_react_workspace_state_uses_exact_contract_and_route_ownership(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "workspace-contract-repo")
        db.create_task(
            database_path,
            description="DEMO running workspace slice 999",
            status="Running",
            metadata=project_task_metadata(project),
        )
        db.create_task(
            database_path,
            description="DEMO blocked workspace slice 999",
            status="Estimated",
            metadata={
                **project_task_metadata(project),
                "blocked_condition": {"reason": "Manual estimate required"},
            },
        )
        response = client.get(
            f"/api/projects/{project['id']}/workspace", headers=_portal_headers()
        )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"project", "summary", "controls", "links"}
    assert set(payload["project"]) == {
        "id", "name", "root_path", "archived_at", "capability", "profile",
    }
    assert set(payload["project"]["capability"]) == {"state", "label", "reasons"}
    assert set(payload["project"]["profile"]) == {
        "git_branch", "language_hints", "framework_hints", "package_manager_hints",
        "test_command", "test_command_suggested", "test_command_confirmed",
        "run_command", "relevant_docs",
    }
    assert set(payload["summary"]) == {
        "counts", "total_tasks", "launch_ready", "capability_state", "attention_actions",
    }
    assert set(payload["summary"]["counts"]) == {
        "Estimated", "Running", "Review", "Done",
    }
    assert set(payload["controls"]) == {"can_open_board", "can_restore"}
    assert set(payload["links"]) == {
        "board_href", "floor_href", "task_history_href", "sessions_href", "worker_setup_href",
        "project_settings_href", "restore_href",
    }
    assert payload["links"]["board_href"] == f"/projects/{project['id']}"
    assert payload["links"]["floor_href"] == f"/projects/{project['id']}/floor"
    assert payload["links"] == {
        "board_href": f"/projects/{project['id']}",
        "floor_href": f"/projects/{project['id']}/floor",
        "task_history_href": f"/projects/{project['id']}/task-history",
        "sessions_href": "/sessions",
        "worker_setup_href": "/settings/workers",
        "project_settings_href": "/settings/project",
        "restore_href": None,
    }
    running = next(
        action for action in payload["summary"]["attention_actions"]
        if action["label"] == "Running work"
    )
    assert running["href"] == f"/projects/{project['id']}/floor"
    assert set(running) == {"label", "detail", "href", "tone"}
    blocked = next(
        action for action in payload["summary"]["attention_actions"]
        if action["label"] == "Blocked work"
    )
    assert blocked["href"] == f"/projects/{project['id']}/needs-you"
    serialized = json.dumps(payload)
    for excluded in (
        "backend_id", "archived_by", "created_at", "updated_at", "can_launch",
    ):
        assert excluded not in serialized


def test_react_workspace_projection_applies_every_bound_and_redacts():
    project_id = "project-" + "9" * 200
    bounded_id = project_id[:128]
    safe_long = "x" * 5000
    action = {
        "label": "l" * 500,
        "detail": "d" * 1500,
        "href": f"/projects/{bounded_id}/board",
        "tone": "t" * 100,
    }
    payload = react_shell._react_workspace_projection(
        {
            "id": project_id,
            "name": "n" * 500,
            "root_path": safe_long,
            "archived_at": None,
            "capability": {
                "state": "s" * 100,
                "label": "c" * 500,
                "reasons": ["r" * 1500 for _ in range(25)],
                "secret": "DEMO_CAPABILITY_SECRET_999",
            },
            "profile": {
                "git_branch": "b" * 800,
                "language_hints": ["l" * 300 for _ in range(25)],
                "framework_hints": ["f" * 300 for _ in range(25)],
                "package_manager_hints": ["p" * 300 for _ in range(25)],
                "test_command": "t" * 5000,
                "run_command": "password=DEMO_RUN_SECRET_999 " + safe_long,
                "relevant_docs": ["d" * 1500 for _ in range(60)],
                "internal_config": {"token": "DEMO_PROFILE_SECRET_999"},
            },
            "backend_id": "DEMO_BACKEND_SECRET_999",
        },
        {
            "counts": {
                "Estimated": 1,
                "Running": -1,
                "Review": True,
                "Done": "4",
                "Blocked": 5,
            },
            "launch_ready": True,
            "capability_state": "q" * 100,
            "attention_actions": [
                {**action, "href": "/unsafe/path"},
                *[action for _ in range(25)],
            ],
            "command_plan": {"token": "DEMO_SUMMARY_SECRET_999"},
        },
    )

    project = payload["project"]
    profile = project["profile"]
    capability = project["capability"]
    summary = payload["summary"]
    assert len(project["id"]) == 128
    assert len(project["name"]) == 200
    assert len(project["root_path"]) == 4096
    assert len(capability["state"]) == 64
    assert len(capability["label"]) == 200
    assert len(capability["reasons"]) == 20
    assert all(len(item) == 1000 for item in capability["reasons"])
    assert len(profile["git_branch"]) == 500
    for key in ("language_hints", "framework_hints", "package_manager_hints"):
        assert len(profile[key]) == 20
        assert all(len(item) == 200 for item in profile[key])
    assert len(profile["test_command"]) == 4000
    assert len(profile["run_command"]) <= 4000
    assert len(profile["relevant_docs"]) == 50
    assert all(len(item) == 1000 for item in profile["relevant_docs"])
    assert summary["counts"] == {
        "Estimated": 1, "Running": 0, "Review": 0, "Done": 0,
    }
    assert summary["total_tasks"] == 1
    assert len(summary["capability_state"]) == 64
    assert len(summary["attention_actions"]) == 20
    assert all(len(item["label"]) == 200 for item in summary["attention_actions"])
    assert all(len(item["detail"]) == 1000 for item in summary["attention_actions"])
    assert all(len(item["tone"]) == 32 for item in summary["attention_actions"])
    assert all(
        item["href"] == f"/projects/{bounded_id}"
        for item in summary["attention_actions"]
    )
    serialized = json.dumps(payload)
    for secret in (
        "DEMO_RUN_SECRET_999", "DEMO_CAPABILITY_SECRET_999", "DEMO_PROFILE_SECRET_999",
        "DEMO_BACKEND_SECRET_999", "DEMO_SUMMARY_SECRET_999",
    ):
        assert secret not in serialized


def test_react_workspace_projection_uses_typed_defaults_for_malformed_values():
    payload = react_shell._react_workspace_projection(
        {
            "id": "project-DEMO-999",
            "name": ["bad"],
            "root_path": {"bad": True},
            "archived_at": {"bad": True},
            "capability": "bad",
            "profile": "bad",
        },
        {
            "counts": "bad",
            "launch_ready": "yes",
            "capability_state": ["bad"],
            "attention_actions": "bad",
        },
    )

    assert payload["project"] == {
        "id": "project-DEMO-999",
        "name": "",
        "root_path": "",
        "archived_at": None,
        "capability": {"state": "", "label": "", "reasons": []},
        "profile": {
            "git_branch": None,
            "language_hints": [],
            "framework_hints": [],
            "package_manager_hints": [],
            "test_command": None,
            "test_command_suggested": None,
            "test_command_confirmed": False,
            "run_command": None,
            "relevant_docs": [],
        },
    }
    assert payload["summary"] == {
        "counts": {column: 0 for column in (
            "Estimated", "Running", "Review", "Done"
        )},
        "total_tasks": 0,
        "launch_ready": False,
        "capability_state": "",
        "attention_actions": [],
    }


    archived = react_shell._react_workspace_projection(
        {
            "id": "project-DEMO-999",
            "name": "DEMO archived project",
            "root_path": "/DEMO/2099/repo",
            "archived_at": "a" * 100,
            "capability": {},
            "profile": {},
        },
        {},
    )
    assert len(archived["project"]["archived_at"]) == 64
    assert archived["controls"] == {"can_open_board": False, "can_restore": True}


def test_react_workspace_endpoint_tolerates_malformed_stored_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "malformed-workspace-repo")
        with db.connect(database_path) as conn:
            conn.execute(
                "update connected_projects set profile_json = ?, capability_json = ? where id = ?",
                ('"bad-profile"', '"bad-capability"', project["id"]),
            )
        response = client.get(
            f"/api/projects/{project['id']}/workspace", headers=_portal_headers()
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["profile"] == {
        "git_branch": None,
        "language_hints": [],
        "framework_hints": [],
        "package_manager_hints": [],
        "test_command": None,
        "test_command_suggested": None,
        "test_command_confirmed": False,
        "run_command": None,
        "relevant_docs": [],
    }
    assert set(payload["project"]["capability"]) == {"state", "label", "reasons"}


def test_react_archived_workspace_is_restore_first(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "react-archived-repo")
        db.archive_connected_project(database_path, project["id"])
        workspace = client.get(
            f"/api/projects/{project['id']}/workspace", headers=_portal_headers()
        )
        board = client.get(
            f"/api/projects/{project['id']}/board", headers=_portal_headers()
        )

    assert workspace.status_code == 200
    payload = workspace.json()
    assert payload["project"]["archived_at"]
    assert payload["summary"]["launch_ready"] is False
    assert payload["summary"]["capability_state"] == "archived"
    assert payload["controls"] == {"can_open_board": False, "can_restore": True}
    assert payload["links"]["board_href"] is None
    assert payload["links"]["restore_href"] == f"/projects/{project['id']}/restore"
    assert board.status_code == 409
    assert "restore archived project" in board.json()["detail"]


def test_react_restore_json_success_is_idempotent_and_bounded(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    headers = {**_portal_headers(), "Accept": "application/json"}
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "react-restore-repo")
        db.archive_connected_project(database_path, project["id"])
        restored = client.post(f"/projects/{project['id']}/restore", headers=headers)
        repeated = client.post(f"/projects/{project['id']}/restore", headers=headers)

    expected = {
        "ok": True,
        "error": None,
        "next_href": f"/projects/{project['id']}",
        "retry_href": None,
        "project": {"id": project["id"], "archived": False},
    }
    assert restored.status_code == 200
    assert restored.json() == expected
    assert repeated.status_code == 200
    assert repeated.json() == expected
    assert db.get_connected_project(database_path, project["id"])["archived_at"] is None


@pytest.mark.parametrize(
    ("accept", "expected_status"),
    [
        ("Application/JSON", 200),
        ("application/json;q=0", 303),
        ("text/html, application/json; q=0", 303),
        ("text/html, Application/JSON; charset=utf-8; Q=0.5", 200),
    ],
)
def test_react_restore_respects_accept_quality_and_casing(
    tmp_path, monkeypatch, accept, expected_status
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "react-restore-accept-repo")
        response = client.post(
            f"/projects/{project['id']}/restore",
            headers={**_portal_headers(), "Accept": accept},
            follow_redirects=False,
        )

    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.json()["ok"] is True
    else:
        assert response.headers["location"] == f"/projects/{project['id']}"


def test_react_restore_html_caller_gets_303_to_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "html-restore-repo")
        db.archive_connected_project(database_path, project["id"])
        response = client.post(
            f"/projects/{project['id']}/restore",
            headers=_portal_headers(),
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == f"/projects/{project['id']}"


@pytest.mark.parametrize(
    ("accept", "expects_react_json"),
    [
        ("Application/JSON", True),
        ("application/json;q=0", False),
        ("text/html, application/json; q=0", False),
        ("text/html, Application/JSON; charset=utf-8; Q=0.5", True),
    ],
)
@pytest.mark.parametrize(
    ("path", "data"),
    [
        ("/tasks/missing-DEMO-999/launch", {}),
        ("/tasks/missing-DEMO-999/refresh", {}),
        ("/tasks/missing-DEMO-999/review", {"action": "save_prompt"}),
    ],
)
def test_react_task_actions_respect_accept_quality_and_casing(
    tmp_path, monkeypatch, accept, expects_react_json, path, data
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.post(
            path,
            headers={**_portal_headers(), "Accept": accept},
            data=data,
            follow_redirects=False,
        )

    assert ("ok" in response.json()) is expects_react_json


def test_react_restore_json_unknown_project_is_fixed_404(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    headers = {**_portal_headers(), "Accept": "application/json"}
    with _client(tmp_path) as client:
        response = client.post("/projects/missing-DEMO-999/restore", headers=headers)

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "error": "connected project not found",
        "next_href": None,
        "retry_href": "/projects",
        "project": None,
    }


def test_react_restore_does_not_convert_infrastructure_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "react-restore-error-repo")
        monkeypatch.setattr(
            db,
            "restore_connected_project",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("DEMO DB failure 999")),
        )
        with pytest.raises(RuntimeError, match="DEMO DB failure 999"):
            client.post(
                f"/projects/{project['id']}/restore",
                headers={**_portal_headers(), "Accept": "application/json"},
            )


def test_react_board_state_reuses_board_context(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "repo")
        response = client.get(
            f"/api/projects/{project['id']}/board", headers=_portal_headers()
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["id"] == project["id"]
    assert payload["columns"] == [
        "Estimated",
        "Running",
        "Review",
        "Done",
    ]
    assert set(payload["tasks_by_status"]) == set(payload["columns"])
    assert "board_empty_states" in payload


def test_react_board_state_and_frontend_use_estimate_token_field(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "repo")
        task = db.create_task(
            database_path,
            description="Display estimated token field in React board",
            status="Estimated",
            estimate_tokens=9_999,
            metadata=project_task_metadata(project),
        )
        response = client.get(
            f"/api/projects/{project['id']}/board", headers=_portal_headers()
        )

    assert response.status_code == 200
    estimated = response.json()["tasks_by_status"]["Estimated"][0]
    assert estimated["id"] == task["id"]
    assert estimated["summary"]["text"] == "Display estimated token field in React board"
    assert estimated["estimate_tokens"] == 9_999
    assert "description" not in estimated
    assert "estimated_tokens" not in estimated

    board_source = Path("frontend/src/views/Board.jsx").read_text(encoding="utf-8")
    assert "task.summary.text" in board_source
    assert "task.estimate_tokens" in board_source
    assert "task.estimated_tokens" not in board_source
    assert "Accept: \"application/json\"" in board_source
    assert "status.reload_required" in board_source
    for action_path in (
        "/run-next",
        "/queue/start",
        "/queue/stop",
        "/tasks/archive-done",
        "/archive",
        "/tasks/${task.id}/launch",
        "/tasks/${task.id}/refresh",
        "/tasks/${task.id}/review",
    ):
        assert action_path in board_source
    for chat_path in (
        "PlanningChat",
        "onTurnComplete",
    ):
        assert chat_path in board_source
    for form_field in (
        'form.set("project_id"',
        'form.set("adapter_id"',
        'form.set("model"',
        'form.set("budget_override"',
        'form.set("native_budget_acknowledged"',
        "review_prompt",
        "blocked_reason",
        "auto_agent_review",
    ):
        assert form_field in board_source


@pytest.mark.parametrize(
    ("metadata_key", "metadata_value"),
    [
        ("workdir_evidence", "bad-shape"),
        ("last_launch_failure", "bad-shape"),
        ("worker_run_events", "bad-shape"),
    ],
)
def test_react_board_projection_tolerates_malformed_nested_metadata(
    tmp_path, monkeypatch, metadata_key, metadata_value
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "repo")
        db.create_task(
            database_path,
            description="Malformed metadata must not break project board",
            status="Estimated",
            estimate_tokens=9_999,
            metadata={
                **project_task_metadata(project),
                metadata_key: metadata_value,
            },
        )

        response = client.get(
            f"/api/projects/{project['id']}/board", headers=_portal_headers()
        )

    assert response.status_code == 200
    card = response.json()["tasks_by_status"]["Estimated"][0]
    assert "details" not in card
    assert card["timeline"] == []


def test_react_board_projection_sanitizes_and_bounds_timeline_labels(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "repo")
        db.create_task(
            database_path,
            description="Timeline labels stay safe",
            status="Estimated",
            estimate_tokens=9_999,
            metadata={
                **project_task_metadata(project),
                "worker_run_events": [
                    {
                        "created_at": "2099-01-01T00:00:00Z",
                        "kind": "Bearer DEMO_SECRET_999 " + "k" * 200,
                        "title": "password=DEMO_SECRET_999 " + "t" * 500,
                        "detail_summary": "Bearer DEMO_DETAIL_SECRET_999",
                    }
                ],
            },
        )

        response = client.get(
            f"/api/projects/{project['id']}/board", headers=_portal_headers()
        )

    assert response.status_code == 200
    event = response.json()["tasks_by_status"]["Estimated"][0]["timeline"][0]
    serialized = json.dumps(event)
    assert "DEMO_SECRET_999" not in serialized
    assert "DEMO_DETAIL_SECRET_999" not in serialized
    assert len(event["kind"]) <= 100
    assert len(event["title"]) <= 400


def test_react_board_projection_uses_exact_nested_allowlists_and_safe_evidence():
    columns = ["Estimated", "Running", "Review", "Done"]
    metadata = {
        "review_actions_available": True,
        "budget_override_available": True,
        "native_usage_override_ack_required": True,
        "native_usage_override_ack_text": "Acknowledge DEMO native usage",
        "active_worker_run_id": "wr_DEMO_999",
        "launch_adapter_id": "codex",
        "launch_model": "gpt-5.6-terra",
        "tracking_mode": "native_usage",
        "usage_source": "worker",
        "worker_run_status": "completed",
        "launch_returncode": 0,
        "launch_error": "password=DEMO_LAUNCH_SECRET_999",
        "workdir_evidence": {"configured_workdir": "/tmp/DEMO_2099_repo"},
        "blocked_condition": {
            "reason": "password=DEMO_BLOCKED_SECRET_999",
            "origin": "review",
            "timestamp": "2099-01-01T00:00:00Z",
        },
        "last_launch_failure": {
            "returncode": 1,
            "error": "Bearer DEMO_FAILURE_SECRET_999",
            "stdout": "safe stdout",
            "stderr": "password=DEMO_STDERR_SECRET_999",
        },
        "launch_diagnostic": {
            "summary": "safe diagnostic",
            "next_action": "open setup",
            "setup_href": "/settings/workers?adapter_id=codex",
        },
        "worker_token_components": {
            "available": True,
            "items": [{
                "key": "password=DEMO_TOKEN_KEY_999" + "k" * 200,
                "label": "Bearer DEMO_TOKEN_LABEL_999" + "l" * 300,
                "value": "password=DEMO_TOKEN_VALUE_999" + "v" * 500,
            }],
            "cost": 0.25,
            "turn_count": 2,
        },
        "worker_run_events": [{
            "created_at": f"2099-01-0{index}T00:00:00Z",
            "kind": "worker_event",
            "title": f"event {index}",
            "detail_summary": f"detail {index}",
        } for index in range(1, 8)],
        "review_prompt": "Review DEMO evidence",
        "agent_review": {
            "status": "completed",
            "recommendation": "approve",
            "summary": "safe review",
            "findings": [{
                "severity": "password=DEMO_SEVERITY_SECRET_999",
                "message": "Bearer DEMO_FINDING_SECRET_999",
                "path": "password=DEMO_PATH_SECRET_999" + "p" * 500,
                "line": 99,
            }],
            "review_session_id": "sess_DEMO_999",
            "model": "password=DEMO_MODEL_SECRET_999" + "m" * 300,
            "token_totals": {"total_tokens": 42},
        },
    }
    context = {
        "board_summary": {
            "launch_ready": True, "total_tasks": 1, "counts": {"Review": 1},
            "archived_count": 0, "history_total_tasks": 1,
        },
        "automation_summary": {
            "counts": {"Review": 1}, "eligible_count": 0,
            "queue": {
                "status": "stopped", "auto_agent_review": True,
                "latest_stop_reason": "operator_stop",
            },
            "live_refresh_enabled": False,
        },
        "board_empty_states": {column: f"No {column}" for column in columns},
        "adapters": [{
            "id": "codex", "name": "Codex", "is_default": True, "launchable": True,
            "supported_models": ["gpt-5.6-terra"], "tracking_label": "Native",
            "tracking": {
                "mode": "native_usage", "runtime_request_guardrails": True,
                "accounting": "authoritative", "budget_authoritative": True,
                "launchable_for_board": True,
            },
        }],
        "tasks_by_status": {
            column: ([{
                "id": "task_DEMO_999", "status": "Review", "description": "Review DEMO task",
                "estimate_tokens": 9000, "actual_tokens": 4000,
                "recommended_model": "gpt-5.6-terra", "session_id": "sess_DEMO_999",
                "metadata": metadata,
            }] if column == "Review" else [])
            for column in columns
        },
    }

    payload = react_shell._react_board_projection(
        {"id": "proj_DEMO_999", "name": "DEMO project"}, context
    )
    card = payload["tasks_by_status"]["Review"][0]

    assert set(payload) == {
        "project", "columns", "board_summary", "history_href", "board_empty_states",
        "automation", "adapters", "tasks_by_status",
    }
    assert set(payload["board_summary"]) == {
        "launch_ready", "total_tasks", "counts", "archived_count", "history_total_tasks",
    }
    assert set(payload["automation"]) == {
        "counts", "eligible_count", "queue", "live_refresh_enabled",
    }
    assert set(payload["automation"]["queue"]) == {
        "status", "auto_agent_review", "latest_stop_reason",
    }
    assert set(payload["adapters"][0]) == {
        "id", "name", "is_default", "launchable", "allowed_models", "tracking",
    }
    assert set(card) == {
        "id", "status", "summary", "task_kind", "estimate_tokens", "actual_tokens",
        "recommended_model", "launch_model", "session_href", "task_branch",
        "harness_commit", "pull_request", "blocked_condition", "launch_failure",
        "review_prompt", "timeline", "controls",
        "intake_decision", "intake_decision_reason",
    }
    assert set(card["controls"]) == {
        "can_launch", "can_refresh", "can_save_review_prompt", "can_agent_review",
        "can_mark_done", "can_block", "can_approve_commit", "can_open_pr",
        "pr_unavailable_reason", "can_archive", "can_dismiss",
        "requires_manual_estimate",
        "budget_override_available", "native_usage_override_ack_required",
        "native_usage_override_ack_text", "setup_href",
    }
    assert card["review_prompt"] == {"text": "Review DEMO evidence", "truncated": False}
    assert [event["title"] for event in card["timeline"]] == [
        f"event {index}" for index in range(2, 8)
    ]
    serialized = json.dumps(card)
    for secret in (
        "DEMO_LAUNCH_SECRET_999", "DEMO_FAILURE_SECRET_999", "DEMO_STDERR_SECRET_999",
        "DEMO_TOKEN_KEY_999", "DEMO_TOKEN_LABEL_999", "DEMO_TOKEN_VALUE_999",
        "DEMO_SEVERITY_SECRET_999", "DEMO_FINDING_SECRET_999", "DEMO_PATH_SECRET_999",
        "DEMO_MODEL_SECRET_999", "DEMO_BLOCKED_SECRET_999",
    ):
        assert secret not in serialized
    assert card["blocked_condition"] == {
        "reason": "***REDACTED***",
        "origin": "review",
        "timestamp": "2099-01-01T00:00:00Z",
    }
    assert "details" not in card
    assert "safe stdout" not in serialized
    assert "safe review" not in serialized


def test_react_task_projection_omits_non_card_evidence():
    secret = "password=DEMO_NUMERIC_SECRET_999"
    card = react_shell._react_task({
        "id": "task_DEMO_999",
        "status": "Review",
        "metadata": {
            "launch_returncode": {"secret": secret},
            "last_launch_failure": {"returncode": secret},
            "worker_token_components": {
                "cost": {"secret": secret},
                "turn_count": [secret],
            },
            "agent_review": {
                "findings": [{"message": "DEMO finding", "line": {"secret": secret}}],
                "token_totals": {"total_tokens": secret},
            },
        },
    })

    assert "details" not in card
    assert card["timeline"] == []
    assert "DEMO_NUMERIC_SECRET_999" not in json.dumps(card)


def test_react_task_projection_has_stable_null_and_empty_defaults():
    card = react_shell._react_task(
        {"id": "task_DEMO_999", "status": "Review", "description": "", "metadata": {}}
    )

    assert card["summary"] == {"text": "", "truncated": False}
    assert card["estimate_tokens"] is None
    assert card["actual_tokens"] is None
    assert card["recommended_model"] is None
    assert card["launch_model"] is None
    assert card["session_href"] is None
    assert card["task_branch"] is None
    assert card["harness_commit"] is None
    assert card["pull_request"] is None
    assert card["blocked_condition"] is None
    assert card["review_prompt"] == {"text": "", "truncated": False}
    assert card["timeline"] == []
    assert "details" not in card


def test_react_task_title_preserves_safe_secret_word_and_redacts_embedded_value():
    safe_title = "Implement Secret scanner parity"
    safe_card = react_shell._react_task(
        {
            "id": "task_DEMO_998",
            "status": "Review",
            "description": safe_title,
            "metadata": {},
        }
    )
    card = react_shell._react_task(
        {
            "id": "task_DEMO_999",
            "status": "Review",
            "description": f"{safe_title}; secret=DEMO-TITLE-SECRET-999",
            "metadata": {},
        }
    )

    assert safe_card["summary"]["text"] == safe_title
    assert safe_title in card["summary"]["text"]
    assert "DEMO-TITLE-SECRET-999" not in card["summary"]["text"]
    assert "***REDACTED***" in card["summary"]["text"]


def test_react_json_missing_project_is_404(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get(
            "/api/projects/does-not-exist/workspace", headers=_portal_headers()
        )

    assert response.status_code == 404


# test_jinja_project_pages_remain_available asserted that the workspace and
# board rendered server-side without a React build. Both are React-owned now;
# test_canonical_project_workspace_and_board_routing covers both build states.


def test_portal_nav_requires_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/api/portal/nav")

    assert response.status_code == 401


def test_portal_nav_shape(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        # No projects connected yet.
        empty = client.get("/api/portal/nav", headers=_portal_headers())
        assert empty.status_code == 200
        body = empty.json()
        assert body["portal_auth_required"] is True
        assert body["sidebar_projects"] == []

        # Connect a project and re-request.
        project = _connect_project(database_path, tmp_path / "repo")
        populated = client.get("/api/portal/nav", headers=_portal_headers())
        assert populated.status_code == 200
        projects = populated.json()["sidebar_projects"]
        assert len(projects) == 1
        item = projects[0]
        assert item["id"] == str(project["id"])
        assert item["name"] == project["name"]
        assert "task_count" in item
        assert populated.json()["portal_auth_required"] is True


def test_portal_nav_auth_disabled_no_projects(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path, portal_auth_required=False) as client:
        response = client.get("/api/portal/nav")

    assert response.status_code == 200
    body = response.json()
    assert body["portal_auth_required"] is False
    assert body["sidebar_projects"] == []


def test_authenticated_shell_keeps_project_switching_logout_and_canonical_route_boundaries(
    tmp_path, monkeypatch
):
    """The presentation shell keeps server-owned auth and project routes unchanged."""
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    database_path = tmp_path / "harness.db"

    with _client(tmp_path) as client:
        first = _connect_project(database_path, tmp_path / "first-shell-repo")
        second = _connect_project(database_path, tmp_path / "second-shell-repo")
        nav = client.get("/api/portal/nav", headers=_portal_headers())
        direct_loads = [
            client.get(f"/projects/{first['id']}", headers=_portal_headers()),
            client.get(f"/projects/{second['id']}", headers=_portal_headers()),
            client.get(f"/projects/{second['id']}/floor", headers=_portal_headers()),
        ]
        logout = client.post("/logout", follow_redirects=False)

    assert nav.status_code == 200
    assert {project["id"] for project in nav.json()["sidebar_projects"]} == {
        first["id"], second["id"]
    }
    assert all(response.status_code == 200 for response in direct_loads)
    assert all('id="root"' in response.text for response in direct_loads)
    assert logout.status_code == 303
    assert logout.headers["location"] == "/login"


def test_legacy_aliases_remain_server_owned_redirects(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    database_path = tmp_path / "harness.db"

    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "legacy-shell-repo")
        alias = client.get(
            f"/app/projects/{project['id']}/floor",
            headers=_portal_headers(),
            follow_redirects=False,
        )

    assert alias.status_code == 301
    assert alias.headers["location"] == f"/projects/{project['id']}/floor"


def test_react_dashboard_source_contract():
    app_source = Path("frontend/src/App.jsx").read_text(encoding="utf-8")
    routes_source = Path("frontend/src/routes.js").read_text(encoding="utf-8")
    shell_source = Path("frontend/src/components/Shell.jsx").read_text(encoding="utf-8")
    dashboard_source = Path("frontend/src/views/Dashboard.jsx").read_text(encoding="utf-8")

    assert 'view: "dashboard"' in routes_source
    assert "<Dashboard />" in app_source
    assert 'to="/app"' in shell_source
    assert 'activeView === "dashboard"' in shell_source
    assert "sidebar-action active" not in shell_source
    assert 'useResource("/api/dashboard")' in dashboard_source
    assert 'href={action.href}' in dashboard_source
    assert "<AppLink" in dashboard_source
    assert "/projects/${project.id}" in dashboard_source


def test_css_react_board_controls_and_details_present():
    css_source = Path("frontend/src/tokens.css").read_text(encoding="utf-8")
    assert ".card-controls" in css_source
    assert ".check-row" in css_source
    assert ".detail-grid" in css_source
    assert ".btn.danger" in css_source
    assert ".board-input" in css_source
    assert ".board-file::file-selector-button" in css_source
    assert ".raw-evidence" in css_source


def test_canonical_sessions_routes_use_complete_build_and_validate_report(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    db.init_db(tmp_path / "harness.db")
    session = db.create_session(
        tmp_path / "harness.db",
        task_description="DEMO React session 2099",
        model="demo-model-999",
        session_key_hash="s" * 64,
        guardrail_overrides={},
    )
    with _client(tmp_path) as client:
        sessions = client.get("/sessions", headers=_portal_headers())
        report = client.get(f"/sessions/{session['id']}", headers=_portal_headers())
        missing = client.get("/sessions/missing", headers=_portal_headers())
        unauthenticated = client.get("/sessions", follow_redirects=False)
        unknown_alias = client.get("/app/sessions", headers=_portal_headers())
    assert sessions.status_code == report.status_code == 200
    assert '<div id="root"></div>' in sessions.text and '<div id="root"></div>' in report.text
    assert missing.status_code == 404
    assert unauthenticated.status_code in {302, 303, 401}
    assert unknown_alias.status_code == 404


def test_react_task_history_endpoint_requires_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/api/projects/does-not-exist/task-history")
    assert response.status_code == 401


def test_react_task_history_json_uses_exact_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "repo")
        session = db.create_session(
            database_path,
            task_description="DEMO task history session",
            model="demo-model-999",
            session_key_hash="s" * 64,
            guardrail_overrides={},
        )
        task = db.create_task(
            database_path,
            description="DEMO archived history task",
            status="Done",
            estimate_tokens=1_000,
            actual_tokens=2_000,
            recommended_model="demo-model-999",
            session_id=session["id"],
            metadata={
                **project_task_metadata(project),
                "active_worker_run_id": "run-123",
                "blocked_reason": "DEMO blocked reason",
                "requires_manual_estimate": True,
            },
        )
        db.archive_task(database_path, task["id"])
        response = client.get(
            f"/api/projects/{project['id']}/task-history?filter=archived",
            headers=_portal_headers(),
        )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"filters", "selected_filter", "tasks"}
    assert all(set(filter) == {"label", "value", "count", "active"} for filter in payload["filters"])
    assert payload["selected_filter"] == "archived"
    assert len(payload["tasks"]) == 1
    task = payload["tasks"][0]
    assert set(task) == {
        "id", "description", "status", "task_kind", "archived", "archived_at", "estimate_tokens",
        "actual_tokens", "recommended_model", "session_href", "worker_run_id",
        "blocked_reason", "requires_manual_estimate",
    }
    assert task["status"] == "Done"
    assert task["archived"] is True
    assert task["archived_at"]
    assert task["estimate_tokens"] == 1_000
    assert task["actual_tokens"] == 2_000
    assert task["recommended_model"] == "demo-model-999"
    assert task["session_href"] == f"/sessions/{session['id']}"
    assert task["worker_run_id"] == "run-123"
    assert task["blocked_reason"] == "DEMO blocked reason"
    assert task["requires_manual_estimate"] is True


def test_react_task_history_unknown_project_is_404(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get(
            "/api/projects/does-not-exist/task-history",
            headers=_portal_headers(),
        )
    assert response.status_code == 404


def test_canonical_task_history_route_serves_react_when_built(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "repo")
        response = client.get(
            f"/projects/{project['id']}/task-history", headers=_portal_headers()
        )
    assert response.status_code == 200
    assert '<div id="root"></div>' in response.text


def test_unarchive_task_content_negotiation(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "repo")
        task = db.create_task(
            database_path,
            description="DEMO unarchive task",
            status="Done",
            metadata=project_task_metadata(project),
        )
        db.archive_task(database_path, task["id"])
        json_response = client.post(
            f"/projects/{project['id']}/tasks/{task['id']}/unarchive",
            headers={**_portal_headers(), "Accept": "application/json"},
        )
        html_response = client.post(
            f"/projects/{project['id']}/tasks/{task['id']}/unarchive",
            headers={**_portal_headers(), "Accept": "text/html"},
            follow_redirects=False,
        )
    assert json_response.status_code == 200
    payload = json_response.json()
    assert set(payload) == {"ok", "task_id", "status", "archived"}
    assert payload["ok"] is True
    assert payload["task_id"] == task["id"]
    assert payload["status"] == "Done"
    assert payload["archived"] is False
    assert html_response.status_code == 303
    assert html_response.headers["location"] == f"/projects/{project['id']}/task-history"


def test_task_history_view_source_contract():
    """Frontend source/contract: no stale field names, all evidence fields rendered."""
    source = Path("frontend/src/views/TaskHistory.jsx").read_text(encoding="utf-8")
    for field in (
        "task.description",
        "task.id",
        "task.status",
        "task.archived",
        "task.archived_at",
        "task.estimate_tokens",
        "task.actual_tokens",
        "task.recommended_model",
        "task.session_href",
        "task.worker_run_id",
        "task.blocked_reason",
        "task.requires_manual_estimate",
    ):
        assert field in source, f"{field} missing from TaskHistory.jsx"
    assert "?filter=" in source
    assert "`/projects/${projectId}/tasks/${taskId}/unarchive`" in source
    assert "Accept: \"application/json\"" in source
    assert "aria-live" in source
    assert "aria-pressed" in source
    assert "colSpan" in source


def test_react_budget_settings_requires_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/api/settings/budget")
    assert response.status_code == 401


def test_react_budget_settings_json_uses_exact_contract_and_null_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        db.set_token_budget_settings(
            database_path,
            daily_cap_tokens=1000,
            session_cap_tokens=200,
        )
        db.reset_daily_budget_counter(database_path)
        response = client.get("/api/settings/budget", headers=_portal_headers())
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "daily_cap_tokens",
        "session_cap_tokens",
        "current_window_used_tokens",
        "current_window_remaining_tokens",
        "budget_since",
        "daily_usage_reset_at",
    }
    assert payload["daily_cap_tokens"] == 1000
    assert payload["session_cap_tokens"] == 200
    assert payload["current_window_used_tokens"] == 0
    assert payload["current_window_remaining_tokens"] == 1000
    assert payload["daily_usage_reset_at"]
    assert payload["budget_since"]


def test_react_budget_settings_absent_caps_report_typed_null(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        guardrails = client.app.state.guardrails
        disabled = replace(
            guardrails,
            daily_cap=replace(guardrails.daily_cap, enabled=False),
            session_cap=replace(guardrails.session_cap, enabled=False),
        )
        monkeypatch.setattr(client.app.state, "guardrails", disabled)
        response = client.get("/api/settings/budget", headers=_portal_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["daily_cap_tokens"] is None
    assert payload["session_cap_tokens"] is None
    assert payload["current_window_remaining_tokens"] is None
    assert payload["daily_usage_reset_at"] is None
    assert payload["current_window_used_tokens"] == 0


def test_react_budget_save_json_outcome_and_persistence(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    headers = {**_portal_headers(), "Accept": "application/json"}
    with _client(tmp_path) as client:
        response = client.post(
            "/settings/budget",
            headers=headers,
            json={"daily_cap_tokens": 5000, "session_cap_tokens": 1000},
        )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "error", "budget"}
    assert payload["ok"] is True
    assert payload["error"] is None
    assert payload["budget"]["daily_cap_tokens"] == 5000
    assert payload["budget"]["session_cap_tokens"] == 1000
    saved = db.get_token_budget_settings(database_path)
    assert saved["daily_cap_tokens"] == 5000
    assert saved["session_cap_tokens"] == 1000
    assert saved["confirmed"] is True


def test_react_budget_save_json_rejects_invalid_caps_and_preserves_state(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    headers = {**_portal_headers(), "Accept": "application/json"}
    with _client(tmp_path) as client:
        db.set_token_budget_settings(
            database_path,
            daily_cap_tokens=1000,
            session_cap_tokens=200,
        )
        response = client.post(
            "/settings/budget",
            headers=headers,
            json={"daily_cap_tokens": -1, "session_cap_tokens": 0},
        )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "error", "budget"}
    assert payload["ok"] is False
    assert payload["error"]
    assert "Traceback" not in payload["error"]
    assert payload["budget"] is None
    saved = db.get_token_budget_settings(database_path)
    assert saved["daily_cap_tokens"] == 1000
    assert saved["session_cap_tokens"] == 200


def test_react_budget_save_html_redirect_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        response = client.post(
            "/settings/budget",
            headers=_portal_headers(),
            data={"daily_cap_tokens": "3000", "session_cap_tokens": "500"},
            follow_redirects=False,
        )
    assert response.status_code == 303
    assert response.headers["location"] == "/setup"
    saved = db.get_token_budget_settings(database_path)
    assert saved["daily_cap_tokens"] == 3000
    assert saved["session_cap_tokens"] == 500


def test_react_budget_reset_json_outcome_and_persistence(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    headers = {**_portal_headers(), "Accept": "application/json"}
    with _client(tmp_path) as client:
        db.set_token_budget_settings(
            database_path,
            daily_cap_tokens=1000,
            session_cap_tokens=200,
        )
        response = client.post(
            "/settings/budget/reset",
            headers=headers,
            json={},
        )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "error", "budget"}
    assert payload["ok"] is True
    assert payload["error"] is None
    assert payload["budget"]["daily_usage_reset_at"]
    assert payload["budget"]["daily_cap_tokens"] == 1000


def test_react_budget_reset_html_redirect_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.post(
            "/settings/budget/reset",
            headers=_portal_headers(),
            follow_redirects=False,
        )
    assert response.status_code == 303
    assert response.headers["location"] == "/settings/budget"


def test_canonical_settings_budget_route_serves_react_when_built(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    with _client(tmp_path) as client:
        response = client.get("/settings/budget", headers=_portal_headers())
    assert response.status_code == 200
    assert 'id="root"' in response.text


def test_react_budget_settings_source_contract():
    """Frontend BudgetSettings view matches the backend contract and route wiring."""
    app_source = Path("frontend/src/App.jsx").read_text(encoding="utf-8")
    routes_source = Path("frontend/src/routes.js").read_text(encoding="utf-8")
    shell_source = Path("frontend/src/components/Shell.jsx").read_text(encoding="utf-8")
    source = Path("frontend/src/views/BudgetSettings.jsx").read_text(encoding="utf-8")
    api_source = Path("frontend/src/api.js").read_text(encoding="utf-8")

    assert 'view: "budgetSettings"' in routes_source
    assert "<BudgetSettings />" in app_source
    assert 'activeView === "budgetSettings"' in shell_source
    assert 'to="/settings/budget"' in shell_source
    assert 'href="/setup"' in source
    assert 'useResource("/api/settings/budget"' in source
    assert 'postJSON("/settings/budget"' in source
    assert 'postJSON("/settings/budget/reset"' in source
    for field in (
        "daily_cap_tokens",
        "session_cap_tokens",
        "current_window_used_tokens",
        "current_window_remaining_tokens",
        "budget_since",
        "daily_usage_reset_at",
    ):
        assert field in source, f"{field} missing from BudgetSettings.jsx"
    assert "aria-live" in source
    assert "role=\"dialog\"" in source
    assert "aria-modal" in source
    assert 'Accept: "application/json"' in api_source


def test_react_alarms_api_requires_auth_and_bounded_projection(tmp_path, monkeypatch):
    """GET /api/alarms is authenticated and returns bounded projection fields."""
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "alarms-repo")
        session = db.create_session(
            database_path,
            task_description="Alarm test",
            model="claude-haiku",
            session_key_hash="alarm-hash",
            guardrail_overrides={},
            status="running",
        )
        db.record_alarm(
            database_path,
            session_id=session["id"],
            alarm={
                "id": "alarm-open-1",
                "type": "DAILY_CAP_EXCEEDED",
                "severity": "HIGH",
                "context": {"daily_cap_tokens": 1000, "daily_used_tokens": 100},
                "recommended_action": "Raise daily cap.",
            },
        )
        db.record_alarm(
            database_path,
            session_id=session["id"],
            alarm={
                "id": "alarm-resolved-1",
                "type": "SESSION_CAP_EXCEEDED",
                "severity": "MEDIUM",
                "context": {"session_cap_tokens": 500, "session_used_tokens": 500},
                "recommended_action": "Raise session cap.",
            },
        )
        db.resolve_alarm(
            database_path,
            alarm_id="alarm-resolved-1",
            action="continue",
        )

        no_auth = client.get("/api/alarms")
        open_auth = client.get("/api/alarms?filter=open", headers=_portal_headers())
        resolved_auth = client.get("/api/alarms?filter=resolved", headers=_portal_headers())
        all_auth = client.get("/api/alarms?filter=all", headers=_portal_headers())

    assert no_auth.status_code == 401
    assert open_auth.status_code == 200
    assert resolved_auth.status_code == 200
    assert all_auth.status_code == 200

    payload = open_auth.json()
    assert set(payload) == {"filters", "selected_filter", "alarms"}
    assert payload["selected_filter"] == "open"
    assert len(payload["alarms"]) == 1
    assert payload["alarms"][0]["id"] == "alarm-open-1"
    assert payload["alarms"][0]["available_actions"] == [
        {"action": "continue"},
        {"action": "raise_budget", "cap_key": "daily_cap_tokens", "current_cap": 1000},
    ]
    assert payload["alarms"][0]["session_href"] == f"/sessions/{session['id']}"

    resolved = resolved_auth.json()
    assert resolved["selected_filter"] == "resolved"
    assert len(resolved["alarms"]) == 1
    assert resolved["alarms"][0]["resolved_at"]
    assert resolved["alarms"][0]["resolved_action"] == "continue"
    assert resolved["alarms"][0]["resolved_payload_summary"]
    assert resolved["alarms"][0]["available_actions"] == []

    all_payload = all_auth.json()
    assert all_payload["selected_filter"] == "all"
    assert {alarm["id"] for alarm in all_payload["alarms"]} == {"alarm-open-1", "alarm-resolved-1"}

    filters = payload["filters"]
    assert [f["value"] for f in filters] == ["open", "resolved", "all"]
    assert [f["selected"] for f in filters] == [True, False, False]


def test_react_alarms_resolve_positive_cap_guard_and_json_outcome(tmp_path, monkeypatch):
    """raise_budget rejects non-increasing caps and returns a sanitized JSON outcome."""
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        session = db.create_session(
            database_path,
            task_description="Guard test",
            model="claude-haiku",
            session_key_hash="guard-hash",
            guardrail_overrides={"budget": {"session_cap_tokens": 1000}},
            status="running",
        )
        db.record_alarm(
            database_path,
            session_id=session["id"],
            alarm={
                "id": "alarm-guard-1",
                "type": "SESSION_CAP_EXCEEDED",
                "severity": "HIGH",
                "context": {"session_cap_tokens": 1000, "session_used_tokens": 1000},
                "recommended_action": "Raise session cap.",
            },
        )

        bad = client.post(
            "/alarms/alarm-guard-1/resolve",
            headers={**_portal_headers(), "Accept": "application/json"},
            json={"action": "raise_budget", "payload": {"session_cap_tokens": 500}},
        )
        equal = client.post(
            "/alarms/alarm-guard-1/resolve",
            headers={**_portal_headers(), "Accept": "application/json"},
            json={"action": "raise_budget", "payload": {"session_cap_tokens": 1000}},
        )
        good = client.post(
            "/alarms/alarm-guard-1/resolve",
            headers={**_portal_headers(), "Accept": "application/json"},
            json={"action": "raise_budget", "payload": {"session_cap_tokens": 1001}},
        )

    assert bad.status_code == 200
    assert bad.json()["ok"] is False
    assert bad.json()["alarm"] is None
    assert bad.json()["action"] is None
    assert "strictly greater" in bad.json()["error"]

    assert equal.json()["ok"] is False
    assert good.json()["ok"] is True
    assert good.json()["alarm"]["resolved_at"]
    assert db.get_session(database_path, session["id"])["guardrail_overrides"]["budget"]["session_cap_tokens"] == 1001


def test_react_alarms_resolve_preserves_html_redirect_and_no_auth_json_stays_open(tmp_path, monkeypatch):
    """HTML resolve still redirects; JSON resolve returns the outcome without new auth."""
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        session = db.create_session(
            database_path,
            task_description="Resolve test",
            model="claude-haiku",
            session_key_hash="resolve-hash",
            guardrail_overrides={},
            status="running",
        )
        db.record_alarm(
            database_path,
            session_id=session["id"],
            alarm={
                "id": "alarm-resolve-2",
                "type": "DAILY_CAP_EXCEEDED",
                "severity": "HIGH",
                "context": {"daily_cap_tokens": 100, "daily_used_tokens": 50},
                "recommended_action": "Raise daily cap.",
            },
        )

        html = client.post(
            "/alarms/alarm-resolve-2/resolve",
            headers={**_portal_headers(), "accept": "text/html"},
            data={"action": "continue"},
            follow_redirects=False,
        )
        json = client.post(
            "/alarms/alarm-resolve-2/resolve",
            headers={"Accept": "application/json"},
            json={"action": "continue"},
        )

    assert html.status_code == 303
    assert html.headers["location"] == "/alarms"
    assert json.status_code == 200
    assert json.json()["ok"] is True
    assert json.json()["alarm"]["resolved_at"]


def test_react_alarms_canonical_route_serves_react_when_built(tmp_path, monkeypatch):
    """GET /alarms with a complete build returns the React shell."""
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    with _client(tmp_path) as client:
        response = client.get(
            "/alarms",
            headers={**_portal_headers(), "Accept": "text/html"},
        )
    assert response.status_code == 200
    assert 'id="root"' in response.text


def test_react_alarms_source_contract():
    """Frontend Alarms view matches the backend contract and routing expectations."""
    routes_source = Path("frontend/src/routes.js").read_text(encoding="utf-8")
    shell_source = Path("frontend/src/components/Shell.jsx").read_text(encoding="utf-8")
    source = Path("frontend/src/views/Alarms.jsx").read_text(encoding="utf-8")

    assert 'view: "alarms"' in routes_source
    assert 'to="/alarms"' in shell_source
    assert 'activeView === "alarms"' in shell_source
    api_source = Path("frontend/src/api.js").read_text(encoding="utf-8")

    assert "available_actions" in source
    assert '"/api/alarms?filter="' in source or "`/api/alarms?filter=${" in source
    assert "/alarms/${" in source and "resolve" in source
    assert "postJSON" in source
    assert 'Accept: "application/json"' in api_source
    assert "aria-live" in source
    assert "aria-pressed" in source
    assert "raise_budget" in source
    assert "abort" not in source.lower()
    assert "adjust_guardrail" not in source


def test_react_control_plane_settings_requires_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/api/settings/control-plane")
    assert response.status_code == 401


def test_react_control_plane_settings_json_uses_exact_contract_and_key_value_never_present(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.setenv("TEST_CONTROL_PLANE_KEY", "sk_secret_value_999")
    with _client(tmp_path) as client:
        response = client.get("/api/settings/control-plane", headers=_portal_headers())
    assert response.status_code == 200
    payload = response.json()
    # The credential trio and the curated list are gone; pi's inventory replaces them.
    assert set(payload) == {
        "model",
        "configured",
        "inventory",
        "verification",
        "diverging_jobs",
        "shadowed_settings",
        "connection_status",
    }
    assert payload["configured"] is True
    assert payload["inventory"]["models"] == [TEST_ORCHESTRATOR_MODEL]
    assert payload["inventory"]["needs_authentication"] is False
    assert payload["verification"]["passed"] is False
    assert isinstance(payload["shadowed_settings"], dict)
    assert "sk_secret_value_999" not in str(payload)
    assert "sk_secret_value_999" not in response.text


def test_react_control_plane_connection_status_mapping(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.setattr(
        portal,
        "discover_orchestrator_models",
        lambda _p: OrchestratorModelDiscoveryResult(
            state="ready", models=[TEST_ORCHESTRATOR_MODEL], reasons=[], evidence={}
        ),
    )
    with _client(tmp_path) as client:
        save = client.post(
            "/settings/control-plane",
            headers={**_portal_headers(), "Accept": "application/json"},
            json={"control_plane_model": TEST_ORCHESTRATOR_MODEL},
        )
        assert save.status_code == 200, save.text
        # A save is never trusted until a real metered turn proves it.
        assert save.json()["status"]["state"] == "needs_verification"

        read = client.get("/api/settings/control-plane", headers=_portal_headers())
    assert read.json()["connection_status"]["state"] == "needs_verification"


def test_react_control_plane_save_json_outcome_key_free_and_persistence(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.setenv("TEST_CONTROL_PLANE_KEY", "sk_real_key_999")
    monkeypatch.setattr(
        portal,
        "discover_orchestrator_models",
        lambda _p: OrchestratorModelDiscoveryResult(
            state="ready", models=["openai-codex/gpt-5.4"], reasons=[], evidence={}
        ),
    )
    with _client(tmp_path) as client:
        response = client.post(
            "/settings/control-plane",
            headers={**_portal_headers(), "Accept": "application/json"},
            json={"control_plane_model": "openai-codex/gpt-5.4"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "error", "settings", "status", "shadowed_settings", "diverging_jobs"}
    assert payload["ok"] is True
    assert payload["error"] is None
    assert payload["settings"]["orchestrator_model"] == "openai-codex/gpt-5.4"
    assert payload["status"]["state"] == "needs_verification"
    # The env override is exported here, so the save reports itself as shadowed by it
    # rather than silently disagreeing with the environment.
    assert payload["shadowed_settings"] == {"orchestrator_model": "FOREMAN_AI_HQ_ORCHESTRATOR_MODEL"}
    assert "sk_real_key_999" not in str(payload)


def test_react_control_plane_save_error_sanitized(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)

    def fail_write(**_updates):
        raise OSError("disk full at /secret/path")

    monkeypatch.setattr(portal, "update_operator_config", fail_write)
    monkeypatch.setattr(
        portal,
        "discover_orchestrator_models",
        lambda _p: OrchestratorModelDiscoveryResult(
            state="ready", models=[TEST_ORCHESTRATOR_MODEL], reasons=[], evidence={}
        ),
    )
    with _client(tmp_path) as client:
        response = client.post(
            "/settings/control-plane",
            headers={**_portal_headers(), "Accept": "application/json"},
            json={"control_plane_model": TEST_ORCHESTRATOR_MODEL},
        )
    assert response.status_code == 500
    payload = response.json()
    assert set(payload) == {"ok", "error", "settings", "status", "shadowed_settings", "diverging_jobs"}
    assert payload["ok"] is False
    assert payload["error"]
    assert "secret" not in payload["error"]
    assert "disk full" not in payload["error"].lower()
    assert "/secret/path" not in str(payload)


def test_react_control_plane_save_html_redirect_preserved(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.setattr(
        portal,
        "discover_orchestrator_models",
        lambda _p: OrchestratorModelDiscoveryResult(
            state="ready", models=[TEST_ORCHESTRATOR_MODEL], reasons=[], evidence={}
        ),
    )
    with _client(tmp_path) as client:
        response = client.post(
            "/settings/control-plane",
            headers={**_portal_headers(), "Accept": "text/html"},
            data={"control_plane_model": TEST_ORCHESTRATOR_MODEL},
            follow_redirects=False,
        )
    assert response.status_code == 303
    assert response.headers["location"] == "/settings/control-plane"


def test_react_control_plane_verify_html_redirect_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.setattr(
        portal,
        "verify_orchestrator_model",
        lambda _p, model, **kw: OrchestratorVerificationResult(
            passed=True, model=model, session_id="sess_x", reasons=[], evidence={}
        ),
    )
    with _client(tmp_path) as client:
        response = client.post(
            "/settings/control-plane/verify",
            headers={**_portal_headers(), "Accept": "text/html"},
            follow_redirects=False,
        )
    assert response.status_code == 303
    assert response.headers["location"] == "/settings/control-plane"


def test_canonical_settings_control_plane_route_serves_react_when_built(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    with _client(tmp_path) as client:
        response = client.get("/settings/control-plane", headers=_portal_headers())
    assert response.status_code == 200
    assert 'id="root"' in response.text


def test_react_control_plane_offers_no_harness_authored_model_list(tmp_path, monkeypatch):
    """Every offered choice originates from pi's inventory.

    This used to assert the handoff projected CURATED_CONTROL_PLANE_MODELS exactly.
    That list is deleted: a harness-authored catalogue is precisely what let a model
    be offered that pi could not run.
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    assert not hasattr(portal, "CURATED_CONTROL_PLANE_MODELS")
    with _client(tmp_path) as client:
        payload = client.get("/api/settings/control-plane", headers=_portal_headers()).json()
    assert "curated_models" not in payload
    assert payload["inventory"]["models"] == [TEST_ORCHESTRATOR_MODEL]


def test_react_control_plane_settings_source_contract():
    """Frontend ControlPlaneSettings view matches the backend contract and route wiring."""
    app_source = Path("frontend/src/App.jsx").read_text(encoding="utf-8")
    routes_source = Path("frontend/src/routes.js").read_text(encoding="utf-8")
    shell_source = Path("frontend/src/components/Shell.jsx").read_text(encoding="utf-8")
    source = Path("frontend/src/views/ControlPlaneSettings.jsx").read_text(encoding="utf-8")

    assert 'view: "controlPlaneSettings"' in routes_source
    assert "<ControlPlaneSettings />" in app_source
    assert 'activeView === "controlPlaneSettings"' in shell_source
    assert 'to="/settings/control-plane"' in shell_source
    assert 'useResource("/api/settings/control-plane"' in source
    assert 'postJSON("/settings/control-plane"' in source
    assert 'postJSON("/settings/control-plane/discover"' in source
    assert 'postJSON("/settings/control-plane/verify"' in source
    # The retired connection test must not survive anywhere in the view.
    assert "/settings/control-plane/test" not in source
    for field in ("inventory", "verification", "diverging_jobs", "configured", "connection_status"):
        assert field in source
    for retired in ("api_key", "base_url", "curated_models", "control_plane_provider"):
        assert retired not in source


def _seeded_adapter(database_path, adapter_id):
    """Return the seeded worker adapter after ensuring it exists."""
    return db.get_worker_adapter(database_path, adapter_id)


@pytest.fixture
def _workers_json_headers():
    return {**_portal_headers(), "Accept": "application/json"}


def test_react_worker_settings_requires_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/api/settings/workers")
    assert response.status_code == 401


def test_react_worker_settings_json_uses_exact_contract_and_no_path_leakage(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        adapter = db.get_worker_adapter(database_path, "codex")
        db.update_worker_adapter(
            database_path,
            "codex",
            config={
                **(adapter.get("config") or {}),
                "_diagnostics": {
                    "installed": True,
                    "callable": True,
                    "command": "codex",
                    "executable": "/secret/path/to/codex",
                    "version": "1.0.0",
                    "failure_reason": None,
                },
            },
        )
        response = client.get("/api/settings/workers", headers=_portal_headers())
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"adapters", "active_adapter_id", "next_action"}
    assert set(payload["next_action"]) == {"label", "detail", "href"}
    assert len(payload["adapters"]) == 3
    adapter = next((a for a in payload["adapters"] if a["id"] == "codex"), None)
    assert adapter is not None
    assert set(adapter) == {
        "id",
        "kind",
        "configured",
        "is_default",
        "connection_type",
        "tracking",
        "tracking_mode_options",
        "discovered_models",
        "supported_models",
        "launchable",
        "diagnostics",
        "verification_evidence",
        "verification_diagnostic",
        "model_discovery_label",
    }
    assert adapter["diagnostics"] is not None
    assert "executable" not in adapter["diagnostics"]
    assert "/secret/path" not in response.text
    assert adapter["verification_evidence"] is None
    assert adapter["verification_diagnostic"] is None
    assert adapter["supported_models"] == []
    assert adapter["discovered_models"]


def test_react_worker_settings_query_param_selects_active_adapter(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get(
            "/api/settings/workers?adapter_id=opencode", headers=_portal_headers()
        )
    assert response.status_code == 200
    assert response.json()["active_adapter_id"] == "opencode"


def test_react_worker_settings_mutation_json_set_default(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    headers = {**_portal_headers(), "Accept": "application/json"}
    with _client(tmp_path) as client:
        response = client.post(
            "/settings/workers/codex/configure",
            headers=headers,
            json={"is_default": True},
        )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"ok", "error"}
    assert payload["ok"] is True
    assert payload["error"] is None
    adapter = db.get_worker_adapter(database_path, "codex")
    assert adapter["is_default"] is True


def test_react_worker_settings_mutation_html_set_default_redirect_preserved(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.post(
            "/settings/workers/codex/configure",
            headers=_portal_headers(),
            data={"is_default": "1"},
            follow_redirects=False,
        )
    assert response.status_code == 303
    assert response.headers["location"] == "/settings/workers?adapter_id=codex"


def test_react_worker_settings_mutation_json_allowed_models_success_and_rejection(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    headers = {**_portal_headers(), "Accept": "application/json"}
    with _client(tmp_path) as client:
        success = client.post(
            "/settings/workers/codex/allowed-models",
            headers=headers,
            json={"allowed_models": ["gpt-5.6-terra"]},
        )
        reject = client.post(
            "/settings/workers/codex/allowed-models",
            headers=headers,
            json={"allowed_models": ["not-discovered-model"]},
        )
    assert success.status_code == 200
    assert success.json()["ok"] is True
    assert success.json()["error"] is None
    adapter = db.get_worker_adapter(database_path, "codex")
    assert adapter["supported_models"] == ["gpt-5.6-terra"]

    assert reject.status_code == 200
    assert reject.json()["ok"] is False
    assert reject.json()["error"]
    assert "Traceback" not in reject.json()["error"]


def test_react_worker_settings_mutation_html_allowed_models_redirect_preserved(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        success = client.post(
            "/settings/workers/codex/allowed-models",
            headers=_portal_headers(),
            data={"allowed_models": "gpt-5.6-terra"},
            follow_redirects=False,
        )
        reject = client.post(
            "/settings/workers/codex/allowed-models",
            headers=_portal_headers(),
            data={"allowed_models": "not-discovered-model"},
            follow_redirects=False,
        )
    assert success.status_code == 303
    assert success.headers["location"] == "/settings/workers?adapter_id=codex"
    assert reject.status_code == 303
    assert reject.headers["location"].startswith("/settings/workers?adapter_id=codex")
    assert "error=" in reject.headers["location"]


def test_react_worker_settings_mutation_json_refresh_diagnostics_success_and_sanitized_error(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    headers = {**_portal_headers(), "Accept": "application/json"}

    def fail_detect(_adapter):
        raise OSError("disk full at /secret/path")

    monkeypatch.setattr(portal, "detect_worker_adapter", fail_detect)
    with _client(tmp_path) as client:
        error = client.post(
            "/settings/workers/codex/refresh-diagnostics",
            headers=headers,
            json={},
        )
    assert error.status_code == 200
    payload = error.json()
    assert set(payload) == {"ok", "error"}
    assert payload["ok"] is False
    assert payload["error"]
    assert "/secret/path" not in str(payload)
    assert "Traceback" not in payload["error"]

    def ok_detect(_adapter):
        return {
            "installed": True,
            "callable": True,
            "command": "codex",
            "executable": "/secret/path/to/codex",
            "version": "1.0.0",
            "failure_reason": None,
        }

    monkeypatch.setattr(portal, "detect_worker_adapter", ok_detect)
    with _client(tmp_path) as client:
        success = client.post(
            "/settings/workers/codex/refresh-diagnostics",
            headers=headers,
            json={},
        )
    assert success.status_code == 200
    assert success.json()["ok"] is True
    adapter = db.get_worker_adapter(database_path, "codex")
    assert adapter["config"]["_diagnostics"]["command"] == "codex"


def test_react_worker_settings_mutation_html_refresh_diagnostics_redirect_preserved(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)

    def ok_detect(_adapter):
        return {
            "installed": True,
            "callable": True,
            "command": "codex",
            "executable": None,
            "version": "1.0.0",
            "failure_reason": None,
        }

    monkeypatch.setattr(portal, "detect_worker_adapter", ok_detect)
    with _client(tmp_path) as client:
        success = client.post(
            "/settings/workers/codex/refresh-diagnostics",
            headers=_portal_headers(),
            follow_redirects=False,
        )
    assert success.status_code == 303
    assert success.headers["location"] == "/settings/workers?adapter_id=codex"


def test_react_worker_settings_verify_json_shape_unchanged(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    headers = {**_portal_headers(), "Accept": "application/json"}

    fake_result = type(
        "VerificationResult",
        (),
        {
            "passed": True,
            "adapter_id": "codex",
            "session_id": "sess-123",
            "reasons": [],
            "evidence": {"safe": "evidence"},
        },
    )()
    monkeypatch.setattr(portal, "verify_worker_adapter", lambda *args, **kwargs: fake_result)
    with _client(tmp_path) as client:
        db.update_worker_adapter(
            database_path,
            "codex",
            config={"allowed_models_configured": True},
            supported_models=["gpt-5.6-terra"],
        )
        response = client.post(
            "/settings/workers/codex/verify",
            headers=headers,
            json={"model": "gpt-5.6-terra", "tracking_mode": "native_usage"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"passed", "adapter_id", "session_id", "reasons", "evidence"}
    assert payload["passed"] is True
    assert payload["adapter_id"] == "codex"
    assert payload["session_id"] == "sess-123"
    assert payload["evidence"] == {"safe": "evidence"}


def test_react_worker_settings_discover_models_json_shape_unchanged(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    headers = {**_portal_headers(), "Accept": "application/json"}

    fake_result = type(
        "ModelDiscoveryResult",
        (),
        {
            "passed": True,
            "adapter_id": "opencode",
            "models": ["opencode/gpt-5.1"],
            "reasons": [],
            "evidence": {"safe": "evidence"},
        },
    )()
    monkeypatch.setattr(portal, "discover_worker_models", lambda *args, **kwargs: fake_result)
    with _client(tmp_path) as client:
        response = client.post(
            "/settings/workers/opencode/discover-models",
            headers=headers,
            json={},
        )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"passed", "adapter_id", "models", "reasons", "evidence"}
    assert payload["passed"] is True
    assert payload["adapter_id"] == "opencode"
    assert payload["models"] == ["opencode/gpt-5.1"]


def test_canonical_settings_workers_route_serves_react_when_built(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    with _client(tmp_path) as client:
        response = client.get("/settings/workers", headers=_portal_headers())
    assert response.status_code == 200
    assert 'id="root"' in response.text


def test_react_worker_settings_source_contract():
    """Frontend WorkerSettings view matches the backend contract and route wiring."""
    app_source = Path("frontend/src/App.jsx").read_text(encoding="utf-8")
    routes_source = Path("frontend/src/routes.js").read_text(encoding="utf-8")
    shell_source = Path("frontend/src/components/Shell.jsx").read_text(encoding="utf-8")
    source = Path("frontend/src/views/WorkerSettings.jsx").read_text(encoding="utf-8")
    api_source = Path("frontend/src/api.js").read_text(encoding="utf-8")

    assert 'view: "workerSettings"' in routes_source
    assert "<WorkerSettings />" in app_source
    assert 'activeView === "workerSettings"' in shell_source
    assert 'to="/settings/workers"' in shell_source
    assert 'useResource("/api/settings/workers"' in source
    assert 'postJSON(`/settings/workers/${' in source
    assert '/configure' in source
    assert '/allowed-models' in source
    assert '/refresh-diagnostics' in source
    assert '/verify' in source
    assert '/discover-models' in source
    for field in (
        "adapters",
        "active_adapter_id",
        "next_action",
        "kind",
        "configured",
        "is_default",
        "connection_type",
        "tracking_mode_options",
        "discovered_models",
        "supported_models",
        "launchable",
        "diagnostics",
        "verification_evidence",
        "verification_diagnostic",
        "model_discovery_label",
    ):
        assert field in source, f"{field} missing from WorkerSettings.jsx"
    assert "aria-live" in source
    assert "htmlFor" in source
    assert "discovered_models" in source
    assert "supported_models" in source
    assert 'Accept: "application/json"' in api_source


def test_react_project_settings_requires_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/api/settings/project")
    assert response.status_code == 401


def test_react_project_settings_json_uses_exact_contract_and_null_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "project-settings-repo")
        response = client.get("/api/settings/project", headers=_portal_headers())
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "local_runner_enabled",
        "backend_status",
        "connected_projects",
        "archived_projects",
        "error",
    }
    assert payload["local_runner_enabled"] is True
    assert payload["error"] is None
    assert payload["archived_projects"] == []
    assert len(payload["connected_projects"]) == 1
    assert payload["connected_projects"][0]["id"] == project["id"]
    assert payload["connected_projects"][0]["name"] == project["name"]
    assert payload["connected_projects"][0]["root_path"] == project["root_path"]
    assert set(payload["connected_projects"][0]["capability"]) == {"state", "reasons"}
    assert payload["backend_status"] is not None
    assert payload["backend_status"]["online"] is True
    assert "Traceback" not in response.text


def test_react_project_settings_sanitizes_backend_and_capability_failures(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "project-settings-repo")
        client.app.state.execution_backend = None
        monkeypatch.setattr(
            "foreman_ai_hq.execution_backend.LocalExecutionBackend.status",
            lambda self: (_ for _ in ()).throw(RuntimeError("Traceback: secret sk_abc123")),
        )
        monkeypatch.setattr(
            "foreman_ai_hq.execution_backend.LocalExecutionBackend.project_capability",
            lambda self, project: (_ for _ in ()).throw(RuntimeError("Traceback: leaked-token")),
        )
        response = client.get("/api/settings/project", headers=_portal_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["backend_status"] is None
    assert len(payload["connected_projects"]) == 1
    assert payload["connected_projects"][0]["capability"]["state"] == "unknown"
    assert "Traceback" not in response.text
    assert "sk_abc123" not in response.text
    assert "leaked-token" not in response.text
    assert "sk_" not in response.text


def test_react_project_settings_json_returns_sanitized_forwarded_error(tmp_path, monkeypatch):
    """The blocked-archive redirect's ?error= survives to React, sanitized.

    HTML archive callers (the Jinja /projects list) are redirected to
    /settings/project?error=<block reason>, which now serves React. React
    forwards the param to this endpoint so the reason is not silently dropped.
    """
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get(
            "/api/settings/project",
            params={"error": "Running work blocks archiving."},
            headers=_portal_headers(),
        )
        leaky = client.get(
            "/api/settings/project",
            params={"error": "Traceback: secret sk_abc123"},
            headers=_portal_headers(),
        )
    assert response.status_code == 200
    assert response.json()["error"] == "Running work blocks archiving."
    assert leaky.status_code == 200
    assert "sk_abc123" not in leaky.text
    assert "sk_" not in leaky.text


def test_react_project_settings_archive_json_success_and_block_reason(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    headers = {**_portal_headers(), "Accept": "application/json"}
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "archive-repo")
        success = client.post(f"/projects/{project['id']}/archive", headers=headers)

        other = _connect_project(database_path, tmp_path / "archive-block-repo")
        db.create_task(
            database_path,
            description="running task",
            status="Running",
            metadata={"connected_project_id": other["id"]},
        )
        blocked = client.post(f"/projects/{other['id']}/archive", headers=headers)

    assert success.status_code == 200
    assert success.json() == {"ok": True, "error": None}
    assert db.get_connected_project(database_path, project["id"])["archived_at"] is not None

    assert blocked.status_code == 200
    blocked_payload = blocked.json()
    assert set(blocked_payload) == {"ok", "error"}
    assert blocked_payload["ok"] is False
    assert blocked_payload["error"]
    assert "Traceback" not in blocked_payload["error"]
    assert "Running work" in blocked_payload["error"]


def test_react_project_settings_archive_html_redirects_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        project = _connect_project(database_path, tmp_path / "archive-html-repo")
        success = client.post(
            f"/projects/{project['id']}/archive",
            headers=_portal_headers(),
            follow_redirects=False,
        )

        other = _connect_project(database_path, tmp_path / "archive-block-html-repo")
        db.create_task(
            database_path,
            description="running task",
            status="Running",
            metadata={"connected_project_id": other["id"]},
        )
        blocked = client.post(
            f"/projects/{other['id']}/archive",
            headers=_portal_headers(),
            follow_redirects=False,
        )

    assert success.status_code == 303
    assert success.headers["location"] == "/projects"
    assert blocked.status_code == 303
    assert blocked.headers["location"].startswith("/settings/project?error=")


def test_react_project_settings_connect_restore_json_shapes_unchanged(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    headers = {**_portal_headers(), "Accept": "application/json", "Content-Type": "application/json"}
    with _client(tmp_path) as client:
        new_root = tmp_path / "connect-repo"
        new_root.mkdir()
        connected = client.post(
            "/settings/project/connect",
            headers=headers,
            json={"root_path": str(new_root)},
        )
        assert connected.status_code == 200
        assert "project" in connected.json()
        project = connected.json()["project"]

        db.archive_connected_project(database_path, project["id"])
        restored = client.post(
            f"/projects/{project['id']}/restore",
            headers=headers,
        )
        assert restored.status_code == 200
        restored_payload = restored.json()
        assert set(restored_payload) == {"ok", "error", "next_href", "retry_href", "project"}
        assert restored_payload["ok"] is True
        assert restored_payload["project"] == {"id": project["id"], "archived": False}

        retired_proof = client.post(
            f"/settings/project/{project['id']}/read-only-proof",
            headers=headers,
        )
        assert retired_proof.status_code == 404


def test_react_project_settings_is_build_aware(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    with _client(tmp_path) as client:
        react = client.get("/settings/project", headers=_portal_headers())

    partial_dir = _build_partial_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: partial_dir)
    with _client(tmp_path) as client:
        partial = client.get("/settings/project", headers=_portal_headers())

    assert react.status_code == 200
    assert 'id="root"' in react.text
    assert partial.status_code == 503
    assert 'id="root"' not in partial.text


def test_react_project_settings_source_contract():
    """Frontend ProjectSettings view matches the backend contract and route wiring."""
    app_source = Path("frontend/src/App.jsx").read_text(encoding="utf-8")
    routes_source = Path("frontend/src/routes.js").read_text(encoding="utf-8")
    shell_source = Path("frontend/src/components/Shell.jsx").read_text(encoding="utf-8")
    source = Path("frontend/src/views/ProjectSettings.jsx").read_text(encoding="utf-8")
    api_source = Path("frontend/src/api.js").read_text(encoding="utf-8")

    assert 'view: "projectSettings"' in routes_source
    assert "<ProjectSettings />" in app_source
    assert 'activeView === "projectSettings"' in shell_source
    assert 'to="/settings/project"' in shell_source
    assert "/api/settings/project" in source
    assert "useResource(url, refreshKey)" in source
    # Errors must read as errors, not as success text: the Jinja oracle renders
    # the block reason in an `alarm high` section, so React styles it distinctly.
    assert 'className="notice danger"' in source
    assert 'aria-live="polite"' in source
    # The blocked-archive redirect lands here as ?error=; React forwards it to
    # the API so the backend sanitizes it rather than dropping it silently.
    assert 'new URLSearchParams(window.location.search).get("error")' in source
    assert "`/api/settings/project?error=${encodeURIComponent(errorParam)}`" in source
    assert 'postJSON("/settings/project/connect"' in source
    assert 'postJSON(`/projects/${' in source
    assert 'postJSON(`/projects/${' in source
    assert 'read-only-proof' not in source
    for field in (
        "local_runner_enabled",
        "backend_status",
        "connected_projects",
        "archived_projects",
        "error",
        "capability",
        "state",
        "reasons",
        "root_path",
    ):
        assert field in source, f"{field} missing from ProjectSettings.jsx"
    assert "aria-live" in source
    assert "htmlFor" in source
    assert 'Accept: "application/json"' in api_source


def test_react_setup_requires_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/api/setup")
    assert response.status_code == 401


def test_react_setup_json_uses_exact_contract_and_null_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        response = client.get("/api/setup", headers=_portal_headers())
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"steps", "ready_to_launch", "next_step", "active_adapter"}
    assert set(payload["next_step"]) == {"label", "href", "detail"}
    assert len(payload["steps"]) == 4
    for step in payload["steps"]:
        assert set(step) == {"name", "state", "href", "detail"}
    assert isinstance(payload["ready_to_launch"], bool)
    assert payload["ready_to_launch"] is False
    assert payload["active_adapter"] is not None
    assert set(payload["active_adapter"]) == {
        "name",
        "verification_status",
        "launchable",
        "tracking_mode",
    }
    assert "verification_evidence" not in payload["active_adapter"]
    assert payload["active_adapter"]["launchable"] is False


def test_react_setup_active_adapter_tracking_mode_from_view_model(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        adapter = db.get_worker_adapter(database_path, "opencode")
        db.update_worker_adapter(
            database_path,
            "opencode",
            config={**(adapter.get("config") or {}), "allowed_models_configured": True},
            supported_models=["opencode/gpt-5.1"],
            is_default=True,
        )
        db.mark_worker_adapter_verification(
            database_path,
            "opencode",
            verified=True,
            evidence={"tracking_mode": "native_usage"},
        )
        response = client.get("/api/setup", headers=_portal_headers())
    assert response.status_code == 200
    payload = response.json()
    active = payload["active_adapter"]
    assert active["name"] == "OpenCode"
    assert active["verification_status"] == "verified"
    assert active["launchable"] is True
    assert active["tracking_mode"] == "native_usage"
    assert "verification_evidence" not in active


def test_react_setup_adapter_id_passthrough(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get(
            "/api/setup?adapter_id=opencode", headers=_portal_headers()
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["active_adapter"]["name"] == "OpenCode"
    worker_step = next(step for step in payload["steps"] if step["name"] == "Worker adapter")
    assert worker_step["href"] == "/settings/workers?adapter_id=opencode"

    with _client(tmp_path) as client:
        response = client.get(
            "/api/setup?adapter_id=unknown-adapter", headers=_portal_headers()
        )
    assert response.status_code == 200
    payload = response.json()
    # Unknown id falls back to the default active adapter selection.
    assert payload["active_adapter"]["name"] in {"Claude Code", "Codex", "OpenCode"}


def test_react_setup_readiness_regression_no_launch_ready_project(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.setenv("FOREMAN_AI_HQ_CONTROL_API_KEY", "sk_test_control_key")
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        db.set_token_budget_settings(
            database_path, daily_cap_tokens=1000, session_cap_tokens=500
        )
        adapter = db.get_worker_adapter(database_path, "opencode")
        db.update_worker_adapter(
            database_path,
            "opencode",
            config={**(adapter.get("config") or {}), "allowed_models_configured": True},
            supported_models=["opencode/gpt-5.1"],
            is_default=True,
        )
        db.mark_worker_adapter_verification(
            database_path,
            "opencode",
            verified=True,
            evidence={"tracking_mode": "native_usage"},
        )
        response = client.get("/api/setup", headers=_portal_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["ready_to_launch"] is False
    project_step = next(step for step in payload["steps"] if step["name"] == "Projects")
    assert project_step["state"] != "ready"
    assert project_step["detail"] == "Connect a project for local Worker runs"


def test_canonical_setup_route_serves_react_when_built(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    build_dir = _build_react_assets(tmp_path)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)
    with _client(tmp_path) as client:
        response = client.get("/setup", headers=_portal_headers())
    assert response.status_code == 200
    assert 'id="root"' in response.text


def test_setup_normalizes_tracking_through_the_view_model(tmp_path, monkeypatch):
    """Tracking is read from the view model, never from raw verification evidence.

    Two renderers used to read this and the Jinja one was the oracle. Only the
    handoff is left, which makes the normalization more load-bearing, not less:
    an unrecognized stored mode must surface as `unverified` rather than being
    passed through to the operator.
    """
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        adapter = db.get_worker_adapter(database_path, "opencode")
        db.update_worker_adapter(
            database_path,
            "opencode",
            config={**(adapter.get("config") or {}), "allowed_models_configured": True},
            supported_models=["opencode/gpt-5.1"],
            is_default=True,
        )
        db.mark_worker_adapter_verification(
            database_path,
            "opencode",
            verified=True,
            evidence={"tracking_mode": "not_a_real_mode"},
        )
        api = client.get("/api/setup?adapter_id=opencode", headers=_portal_headers())

    assert api.status_code == 200
    assert api.json()["active_adapter"]["tracking_mode"] == "unverified"
    assert "not_a_real_mode" not in api.text


def test_react_setup_source_contract():
    """Frontend Setup view matches the backend contract and route wiring."""
    app_source = Path("frontend/src/App.jsx").read_text(encoding="utf-8")
    routes_source = Path("frontend/src/routes.js").read_text(encoding="utf-8")
    shell_source = Path("frontend/src/components/Shell.jsx").read_text(encoding="utf-8")
    source = Path("frontend/src/views/Setup.jsx").read_text(encoding="utf-8")
    api_source = Path("frontend/src/api.js").read_text(encoding="utf-8")

    assert 'view: "setup"' in routes_source
    assert "<Setup />" in app_source
    assert 'activeView === "setup"' in shell_source
    assert 'to="/setup"' in shell_source
    assert "useResource(" in source
    assert '"/api/setup"' in source
    assert "adapter_id" in source
    assert "active_adapter" in source
    assert "tracking_mode" in source
    assert "ready_to_launch" in source
    assert "next_step" in source
    assert "steps" in source
    assert "aria-live" in source
    assert "aria-label" in source
    assert 'href={step.href}' in source
    assert "active_adapter" in source
    assert "setup" in app_source
    assert 'Accept: "application/json"' in api_source


def test_chat_front_door_has_no_legacy_intake_form_and_pane_state_matches_surface():
    """9.6: The board has no short-task form and Planning stays secondary."""
    board_source = Path("frontend/src/views/Board.jsx").read_text(encoding="utf-8")
    assert "board-intake" not in board_source
    assert "estimate-form" not in board_source
    assert '"/tasks/estimate-form"' not in board_source
    assert "PlanningChat" in board_source
    assert "function PipelineSurface(" in board_source
    assert "function FloorSurface(" in board_source
    assert "function PlanningPane(" in board_source
    assert "pipeline: false" in board_source
    assert "floor: false" in board_source
    assert "aria-expanded={expanded}" in board_source
    assert "is-collapsed" in board_source
    app_source = Path("frontend/src/App.jsx").read_text(encoding="utf-8")
    assert 'route.view === "planningChat"' in app_source
    assert 'surface="pipeline"' in app_source


def test_floor_evidence_drawer_retains_fixed_width_beside_collapsed_pane():
    """4.5: The Evidence Drawer is a fixed overlay so its width is unaffected by
    the Floor planning rail. Its width is expressed in viewport units, not a
    percentage of the board layout."""
    css_source = Path("frontend/src/tokens.css").read_text(encoding="utf-8")
    assert ".evidence-drawer {" in css_source
    assert "position: fixed" in css_source
    assert "width: min(760px, 92vw)" in css_source
    board_source = Path("frontend/src/views/Board.jsx").read_text(encoding="utf-8")
    # EvidenceDrawer is a top-level sibling, not nested inside the floor layout.
    assert "<EvidenceDrawer" in board_source
    assert "<EvidenceDrawer" in board_source.split("function FloorSurface")[0]


def test_completed_turn_reloads_board_without_starting_background_polling():
    """9.7: A planning turn completion calls the same load() used on mount, and
    the live-refresh effect returns early when the backend reports it disabled."""
    board_source = Path("frontend/src/views/Board.jsx").read_text(encoding="utf-8")
    assert "onTurnComplete={load}" in board_source
    assert "onTurnComplete={onTurnComplete}" in board_source
    assert "if (!state.data?.automation?.live_refresh_enabled) return undefined;" in board_source
    assert "window.setInterval" in board_source
