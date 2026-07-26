from pathlib import Path

from fastapi.testclient import TestClient

from foreman_ai_hq.app import create_app
from foreman_ai_hq.db import record_alarm, record_token_turn, record_tool_trace
from foreman_ai_hq.settings import Settings


ROOT = Path(__file__).resolve().parents[2]
PORTAL_TOKEN = "test-portal-token"


def _client(tmp_path):
    settings = Settings(database_path=tmp_path / "harness.db", guardrails_path=ROOT / "guardrails.yaml")
    return TestClient(create_app(settings))


def _portal_headers():
    return {"Authorization": f"Bearer {PORTAL_TOKEN}"}


def test_session_start_requires_portal_auth_before_key_mint(tmp_path):
    with _client(tmp_path) as client:
        response = client.post(
            "/session/start",
            json={"task_description": "Unauthed spend path", "model": "claude-haiku"},
        )

    assert response.status_code == 401
    assert "session_api_key" not in response.text


def test_session_start_returns_key_zone_and_report_url(tmp_path):
    with _client(tmp_path) as client:
        response = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={
                "task_description": "Implement a tiny CLI command",
                "model": "claude-haiku",
                "budget": {"daily_used_tokens": 0, "daily_cap_tokens": 1_000_000},
                "guardrail_overrides": {"session_cap": {"tokens": 50_000}},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"].startswith("sess_")
    assert body["session_api_key"].startswith("sk_sess_")
    assert body["starting_zone"] == "green"
    assert body["report_url"] == f"/session/{body['session_id']}/report"


def test_session_report_current_zone_includes_prior_daily_budget_usage(tmp_path):
    with _client(tmp_path) as client:
        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={
                "task_description": "Finish under tight budget",
                "model": "claude-haiku",
                "budget": {"daily_used_tokens": 900_000, "daily_cap_tokens": 1_000_000},
            },
        ).json()
        report = client.get(f"/session/{started['session_id']}/report", headers=_portal_headers())

    assert started["starting_zone"] == "red"
    assert report.status_code == 200
    assert report.json()["current_zone"] == "red"


def test_session_report_artifact_and_checkpoint_evaluation(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Investigate loop", "model": "claude-sonnet"},
        ).json()
        session_id = started["session_id"]
        db_path = tmp_path / "harness.db"
        record_token_turn(
            db_path,
            session_id=session_id,
            model="claude-sonnet",
            prompt_tokens=1000,
            completion_tokens=500,
            cost=0.01,
            raw_usage={"total_tokens": 1500},
        )
        record_tool_trace(
            db_path,
            session_id=session_id,
            tool_name="read_file",
            input_hash="a",
            duration_ms=10,
            metadata={},
        )
        record_alarm(
            db_path,
            session_id=session_id,
            alarm={
                "id": "alarm-session-1",
                "type": "BUDGET_YELLOW",
                "severity": "LOW",
                "context": {"zone": "yellow"},
                "recommended_action": "Review spend.",
            },
        )

        report = client.get(f"/session/{session_id}/report", headers=_portal_headers())
        artifact_without_auth = client.get(f"/session/{session_id}/artifact")
        artifact = client.get(f"/session/{session_id}/artifact", headers=_portal_headers())
        checkpoints = client.post(f"/session/{session_id}/checkpoint/evaluate", headers=_portal_headers())
        report_after = client.get(f"/session/{session_id}/report", headers=_portal_headers())

    assert report.status_code == 200
    report_body = report.json()
    assert report_body["session"]["id"] == session_id
    assert report_body["token_totals"] == {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}
    assert report_body["current_zone"] == "green"
    assert report_body["tool_breakdown"] == {"read_file": {"calls": 1}}
    assert report_body["alarms"][0]["id"] == "alarm-session-1"
    assert artifact_without_auth.status_code == 401
    assert artifact.status_code == 200
    assert artifact.json()["token_log"][0]["total_tokens"] == 1500
    assert checkpoints.status_code == 200
    assert {result["name"] for result in checkpoints.json()["checkpoint_results"]} == {
        "budget_health",
        "stuck_loop_score",
        "tool_diversity",
        "timeout_respect",
    }
    assert len(report_after.json()["checkpoints"]) == 4


def test_session_routes_return_404_for_missing_session(tmp_path):
    with _client(tmp_path) as client:
        response = client.get("/session/missing/report", headers=_portal_headers())

    assert response.status_code == 404


def test_session_report_requires_portal_auth(tmp_path):
    with _client(tmp_path) as client:
        started = client.post(
            "/session/start",
            headers=_portal_headers(),
            json={"task_description": "Report leaks spend evidence", "model": "claude-haiku"},
        ).json()
        without_auth = client.get(f"/session/{started['session_id']}/report")
        with_auth = client.get(f"/session/{started['session_id']}/report", headers=_portal_headers())

    assert without_auth.status_code == 401
    assert with_auth.status_code == 200
    assert with_auth.json()["session"]["id"] == started["session_id"]


def test_session_checkpoint_evaluation_requires_portal_auth(tmp_path):
    with _client(tmp_path) as client:
        started = client.post(
            "/session/start",
            headers=_portal_headers(),
            json={"task_description": "Checkpoint writes need auth", "model": "claude-haiku"},
        ).json()
        session_id = started["session_id"]
        without_auth = client.post(f"/session/{session_id}/checkpoint/evaluate")
        # An unauthenticated call must not have persisted checkpoint rows before the auth check.
        report_after_rejection = client.get(f"/session/{session_id}/report", headers=_portal_headers())
        with_auth = client.post(f"/session/{session_id}/checkpoint/evaluate", headers=_portal_headers())

    assert without_auth.status_code == 401
    assert report_after_rejection.json()["checkpoints"] == []
    assert with_auth.status_code == 200
    assert with_auth.json()["session_id"] == session_id
