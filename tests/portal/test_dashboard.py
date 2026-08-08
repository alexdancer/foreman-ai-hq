from fastapi.testclient import TestClient

from foreman_ai_hq import db
from foreman_ai_hq.app import create_app
from foreman_ai_hq.settings import Settings
from tests.portal.helpers import ROOT, PORTAL_TOKEN, _client, _portal_headers

# These tests used to read the Jinja dashboard.html markup as the oracle for
# dashboard business rules (budget accounting, next-action prioritization,
# alarm visibility, estimation accuracy). The Jinja Portal is retired; every
# assertion below now reads the same `_dashboard_context` computation through
# its JSON handoff, `GET /api/dashboard` (see react_dashboard_state in
# src/foreman_ai_hq/routes/react_shell.py). Purely presentational assertions
# (nav chrome, page titles, static JSX copy, CDN script absence) are dropped
# inline with a comment rather than converted, per design Decision 9.


def test_dashboard_renders_budget_alarm_and_navigation_sections(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Build portal", "model": "claude-haiku"},
        ).json()
        db.record_token_turn(
            tmp_path / "harness.db",
            session_id=started["session_id"],
            model="claude-haiku",
            prompt_tokens=100,
            completion_tokens=50,
            cost=0.01,
            raw_usage={"total_tokens": 150},
        )
        db.record_alarm(
            tmp_path / "harness.db",
            session_id=started["session_id"],
            alarm={
                "id": "alarm-dashboard-1",
                "type": "BUDGET_YELLOW",
                "severity": "LOW",
                "context": {},
                "recommended_action": "Review spend.",
            },
        )

        response = client.get("/api/dashboard", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    actions_by_label = {action["label"]: action for action in payload["next_actions"]}
    assert actions_by_label["Set up Worker adapter"]["href"] == "/settings/workers"
    assert actions_by_label["Review 1 open alarm"]["href"] == "/alarms"
    assert actions_by_label["Open task board"]["href"] == "/board"
    assert payload["budget"]["total_tokens"] == 150
    assert payload["active_sessions"] == [
        {
            "id": started["session_id"],
            "task_description": "Build portal",
            "model": "claude-haiku",
            "status": "running",
        }
    ]
    # Nav section headings ("Sessions", "Alarms", "Task board", "Active
    # sessions"), the page title ("Foreman AI HQ"), and the CDN script
    # absence checks asserted Jinja sidebar/base chrome that no longer
    # exists; there is no JSON equivalent to move them to. The secret
    # checks (PROVIDER_API_KEY, sk_sess_) never had a value from this test
    # reach the dashboard context in the first place — nothing here sets
    # provider_api_key_env or threads a raw session key into it — and the
    # real redaction guarantee is proven with actual injected secrets by
    # test_react_shell.py's test_react_dashboard_projection_is_safe_and_bounded.


def test_dashboard_next_actions_count_launch_and_review_tasks(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        db.create_task(
            database_path,
            description="Ready launch task",
            status="Estimated",
            estimate_tokens=1000,
            recommended_model="5.4",
        )
        session = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Completed Worker task", "model": "5.4"},
        ).json()
        db.update_session_status(database_path, session["session_id"], "completed")
        db.create_task(
            database_path,
            description="Needs review",
            status="Review",
            estimate_tokens=1000,
            recommended_model="5.4",
            session_id=session["session_id"],
        )

        response = client.get("/api/dashboard", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    actions_by_label = {action["label"]: action for action in payload["next_actions"]}
    assert actions_by_label["Launch 1 estimated task"]["href"] == "/board"
    assert actions_by_label["Review 1 task"]["href"] == "/board"
    assert sum(1 for action in payload["next_actions"] if action["href"] == "/board") >= 3


def test_dashboard_next_actions_hide_worker_setup_when_adapter_launchable(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        db.update_worker_adapter(
            database_path,
            "opencode",
            workdir=str(tmp_path),
            config={"native_launch_template": ["opencode", "run"]},
            supported_models=["openai/gpt-5.1"],
            is_default=True,
        )
        db.mark_worker_adapter_verification(
            database_path,
            "opencode",
            verified=True,
            evidence={"tracking_mode": "native_usage", "tracking_authoritative": True},
        )

        response = client.get("/api/dashboard", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    labels = {action["label"] for action in payload["next_actions"]}
    assert "Set up Worker adapter" not in labels
    assert "Open task board" in labels


def test_dashboard_next_actions_prioritize_critical_alarms(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        session = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Budget alarm", "model": "claude-haiku"},
        ).json()
        db.record_alarm(
            database_path,
            session_id=session["session_id"],
            alarm={
                "id": "critical-dashboard-alarm",
                "type": "DAILY_CAP_EXCEEDED",
                "severity": "HIGH",
                "context": {},
                "recommended_action": "Stop launches.",
            },
        )

        response = client.get("/api/dashboard", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    actions_by_label = {action["label"]: action for action in payload["next_actions"]}
    assert actions_by_label["Handle 1 critical alarm"]["href"] == "/alarms"
    assert "Review 1 open alarm" not in actions_by_label


def test_dashboard_recent_alarms_hides_dismissed_alarms(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        session = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Budget alarm", "model": "claude-haiku"},
        ).json()
        for alarm_id in ["dismissed-dashboard-alarm", "open-dashboard-alarm"]:
            db.record_alarm(
                database_path,
                session_id=session["session_id"],
                alarm={
                    "id": alarm_id,
                    "type": "BUDGET_OVERRUN",
                    "severity": "HIGH",
                    "context": {},
                    "recommended_action": f"Review {alarm_id}.",
                },
            )

        dismissed = client.post(
            "/alarms/dismissed-dashboard-alarm/resolve",
            headers={**_portal_headers(), "accept": "text/html"},
            data={"action": "continue"},
            follow_redirects=False,
        )
        response = client.get("/api/dashboard", headers=_portal_headers())
        dismissed_last = client.post(
            "/alarms/open-dashboard-alarm/resolve",
            headers={**_portal_headers(), "accept": "text/html"},
            data={"action": "continue"},
            follow_redirects=False,
        )
        empty_response = client.get("/api/dashboard", headers=_portal_headers())

    assert dismissed.status_code == 303
    assert response.status_code == 200
    payload = response.json()
    recent_ids = [alarm["id"] for alarm in payload["alarms"]["recent"]]
    assert recent_ids == ["open-dashboard-alarm"]
    assert payload["alarms"]["recent"][0]["recommended_action"] == "Review open-dashboard-alarm."

    assert dismissed_last.status_code == 303
    assert empty_response.status_code == 200
    empty_payload = empty_response.json()
    assert empty_payload["alarms"]["recent"] == []
    assert empty_payload["alarms"]["open"] == 0


def test_dashboard_budget_ignores_previous_day_usage(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        old = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Old spend", "model": "claude-haiku"},
        ).json()
        db.record_token_turn(
            tmp_path / "harness.db",
            session_id=old["session_id"],
            model="claude-haiku",
            prompt_tokens=999000,
            completion_tokens=0,
            cost=0,
            raw_usage={"total_tokens": 999000},
        )
        with db.connect(tmp_path / "harness.db") as conn:
            conn.execute("update token_turns set created_at = ?", ("2000-01-01T00:00:00+00:00",))

        current = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Current spend", "model": "claude-haiku"},
        ).json()
        db.record_token_turn(
            tmp_path / "harness.db",
            session_id=current["session_id"],
            model="claude-haiku",
            prompt_tokens=10,
            completion_tokens=5,
            cost=0,
            raw_usage={"total_tokens": 15},
        )

        response = client.get("/api/dashboard", headers=_portal_headers())

    assert response.status_code == 200
    assert response.json()["budget"]["total_tokens"] == 15


def test_dashboard_daily_budget_uses_reset_window(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        old = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Pre-reset dashboard spend", "model": "claude-haiku"},
        ).json()
        db.record_token_turn(
            database_path,
            session_id=old["session_id"],
            model="claude-haiku",
            prompt_tokens=999000,
            completion_tokens=0,
            cost=0,
            raw_usage={"total_tokens": 999000},
        )
        with db.connect(database_path) as conn:
            conn.execute("update token_turns set created_at = ?", (db.current_day_start_iso("local"),))
        reset = db.reset_daily_budget_counter(database_path)

        current = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Post-reset dashboard spend", "model": "claude-haiku"},
        ).json()
        db.record_token_turn(
            database_path,
            session_id=current["session_id"],
            model="claude-haiku",
            prompt_tokens=10,
            completion_tokens=5,
            cost=0,
            raw_usage={"total_tokens": 15},
        )

        response = client.get("/api/dashboard", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["budget"]["total_tokens"] == 15
    assert payload["budget"]["since"] == reset["daily_usage_reset_at"]


def test_dashboard_daily_budget_counts_agent_review_reporting_tokens(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        db.set_token_budget_settings(database_path, daily_cap_tokens=1000, session_cap_tokens=500)
        review_session = db.create_session(
            database_path,
            task_description="Agent Review spend",
            model="control-plane",
            session_key_hash="r" * 64,
            guardrail_overrides={"spend_category": "agent_review"},
            status="completed",
        )
        db.record_token_turn(
            database_path,
            session_id=review_session["id"],
            usage_kind="reporting",
            model="control-plane",
            prompt_tokens=900,
            completion_tokens=0,
            cost=0,
            raw_usage={
                "total_tokens": 900,
                "spend_category": "reporting_summary",
                "usage_source": "control_plane",
                "reporting_kind": "agent_review",
            },
        )
        db.record_token_turn(
            database_path,
            session_id=review_session["id"],
            usage_kind="estimation",
            model="control-plane",
            prompt_tokens=50,
            completion_tokens=0,
            cost=0,
            raw_usage={"total_tokens": 50},
        )

        response = client.get("/api/dashboard", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["budget"]["total_tokens"] == 950
    assert payload["budget"]["daily_cap"] == 1000
    assert payload["budget"]["current_zone"] == "red"
    assert payload["spend"]["agent_review_reporting"] == 900
    assert payload["spend"]["planning_estimation"] == 50
    # The kpi-article count and the "Agent Review/reporting" /
    # "Planning/estimation" labels plus their tooltip copy are static JSX
    # text in frontend/src/views/Dashboard.jsx (rendered unconditionally,
    # not derived from this test's data) — there is no business rule left
    # to assert once the category totals above are proven correct.


def test_dashboard_counts_planning_turns_as_orchestration_spend(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        planning_session = db.create_session(
            database_path,
            task_description="Planning Chat turn",
            model="openai/gpt-5.4",
            session_key_hash="p" * 64,
            guardrail_overrides={},
            status="completed",
        )
        db.record_token_turn(
            database_path,
            session_id=planning_session["id"],
            usage_kind="planning",
            model="openai/gpt-5.4",
            prompt_tokens=400,
            completion_tokens=100,
            cost=0,
            raw_usage={"total_tokens": 500},
        )

        response = client.get("/api/dashboard", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["spend"]["planning_estimation"] == 500
    assert payload["spend"]["other"] == 0


def test_dashboard_shows_accuracy_with_enough_completed_tasks(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    settings = Settings(database_path=tmp_path / "harness.db", guardrails_path=ROOT / "guardrails.yaml")
    db.init_db(settings.database_path)
    app = create_app(settings)

    # Create 3 completed tasks with estimates and actuals
    for est, act in [(500, 550), (300, 280), (1000, 1400)]:
        db.create_task(
            settings.database_path,
            description=f"Task est={est}",
            status="Done",
            estimate_tokens=est,
            actual_tokens=act,
        )

    with TestClient(app) as client:
        response = client.get("/api/dashboard", headers={"Authorization": f"Bearer {PORTAL_TOKEN}"})
    assert response.status_code == 200
    # Ratios: 550/500=1.1, 280/300=0.9333.., 1400/1000=1.4 -> median 1.1, all within 2x.
    assert response.json()["estimation_accuracy"] == {
        "completed_count": 3,
        "median_error_ratio": 1.1,
        "within_2x_pct": 100.0,
    }


# test_dashboard_shows_placeholder_with_insufficient_completed_tasks is deleted
# rather than converted. It asserted two things, both already proven
# elsewhere: (1) the single-completed-task shape of `estimation_accuracy` is
# exactly the case covered by
# test_react_shell.py::test_react_dashboard_projection_is_safe_and_bounded
# (completed_count=1 with a real estimate/actual pair); (2) the "Not enough
# completed tasks for accuracy tracking (N of 3 needed)" placeholder is
# client-only display logic in frontend/src/views/Dashboard.jsx, gated on
# `accuracy.completed_count >= 3`, and is already locked down by
# frontend/tests/shell.test.mjs's "dashboard estimation accuracy panel shows
# absent, progress, and figures states" test (the completed_count: 1
# "progress" case asserts the exact "1 of 3 needed" copy).
