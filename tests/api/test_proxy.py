from pathlib import Path

from fastapi.testclient import TestClient

from foreman_ai_hq import db
from foreman_ai_hq.app import create_app
from foreman_ai_hq.routes import proxy
from foreman_ai_hq.settings import Settings

ROOT = Path(__file__).resolve().parents[2]


class FakeLLMClient:
    def __init__(self):
        self.requests = []

    async def acompletion(self, request):
        self.requests.append(request)
        return {
            "id": "chatcmpl_fake",
            "object": "chat.completion",
            "model": request["model"],
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "done"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 600, "completion_tokens": 500, "total_tokens": 1100},
        }


def _client(tmp_path):
    settings = Settings(database_path=tmp_path / "harness.db", guardrails_path=ROOT / "guardrails.yaml")
    app = create_app(settings)
    fake = FakeLLMClient()
    app.state.llm_client = fake
    return TestClient(app), fake


def test_chat_completions_requires_session_bearer_token(tmp_path):
    client, _fake = _client(tmp_path)
    with client:
        response = client.post("/v1/chat/completions", json={"model": "claude-haiku", "messages": []})

    assert response.status_code == 401


def test_chat_completions_governs_forwards_persists_usage_snapshot_and_alarms(tmp_path):
    client, fake = _client(tmp_path)
    with client:
        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={
                "task_description": "Proxy request",
                "model": "claude-haiku",
                "budget": {"daily_used_tokens": 849_000, "daily_cap_tokens": 1_000_000, "session_cap_tokens": 1_000},
            },
        ).json()
        response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {started['session_api_key']}"},
            json={
                "model": "claude-haiku",
                "messages": [{"role": "user", "content": "finish"}],
                "max_tokens": 4096,
                "tools": [
                    {"type": "function", "function": {"name": "web_search"}},
                    {"type": "function", "function": {"name": "terminal"}},
                ],
            },
        )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "done"
    forwarded = fake.requests[0]
    assert forwarded["messages"][0]["role"] == "system"
    assert forwarded["max_tokens"] == 2048
    assert [tool["function"]["name"] for tool in forwarded["tools"]] == ["terminal"]

    artifact = db.build_session_artifact(tmp_path / "harness.db", started["session_id"])
    assert artifact["token_log"][0]["total_tokens"] == 1100
    assert artifact["guardrail_snapshots"][0]["zone"] == "yellow"
    assert artifact["guardrail_snapshots"][0]["decision"]["blocked_tools"] == ["web_search"]
    assert {alarm["type"] for alarm in artifact["alarms"]} == {"BUDGET_RED", "SESSION_CAP_EXCEEDED"}


def test_chat_completions_budget_zone_counts_prior_agent_review_spend(tmp_path):
    client, fake = _client(tmp_path)
    with client:
        review_session = db.create_session(
            tmp_path / "harness.db",
            task_description="Agent Review spend",
            model="control-plane",
            session_key_hash="d" * 64,
            guardrail_overrides={"spend_category": "agent_review"},
            status="completed",
        )
        db.record_token_turn(
            tmp_path / "harness.db",
            session_id=review_session["id"],
            usage_kind="reporting",
            model="control-plane",
            prompt_tokens=1300,
            completion_tokens=0,
            cost=0,
            raw_usage={
                "total_tokens": 1300,
                "spend_category": "reporting_summary",
                "usage_source": "control_plane",
                "reporting_kind": "agent_review",
            },
        )
        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={
                "task_description": "Worker request after review spend",
                "model": "claude-haiku",
                "budget": {"daily_cap_tokens": 2_000, "session_cap_tokens": 5_000},
            },
        ).json()
        response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {started['session_api_key']}"},
            json={
                "model": "claude-haiku",
                "messages": [{"role": "user", "content": "finish"}],
                "max_tokens": 4096,
                "tools": [{"type": "function", "function": {"name": "web_search"}}],
            },
        )

    assert response.status_code == 200
    forwarded = fake.requests[0]
    assert forwarded["max_tokens"] == 2048
    assert forwarded["tools"] == []
    artifact = db.build_session_artifact(tmp_path / "harness.db", started["session_id"])
    assert artifact["guardrail_snapshots"][0]["zone"] == "yellow"


def test_chat_completions_uses_request_model_for_cost_resolution(tmp_path, monkeypatch):
    seen = {}

    def fake_resolve_cost(model, response):
        seen.update({"model": model, "response": response})
        return 0.42

    monkeypatch.setattr(proxy, "resolve_cost", fake_resolve_cost)
    client, _fake = _client(tmp_path)
    with client:
        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Proxy request", "model": "session-model"},
        ).json()
        client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {started['session_api_key']}"},
            json={"model": "request-model", "messages": [{"role": "user", "content": "finish"}]},
        )

    assert seen == {
        "model": "request-model",
        "response": {
            "id": "chatcmpl_fake",
            "object": "chat.completion",
            "model": "request-model",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "done"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 600, "completion_tokens": 500, "total_tokens": 1100},
        },
    }
    artifact = db.build_session_artifact(tmp_path / "harness.db", started["session_id"])
    assert artifact["token_log"][0]["cost"] == 0.42


def test_chat_completions_persists_null_when_cost_is_unavailable(tmp_path):
    client, _fake = _client(tmp_path)
    with client:
        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Proxy request", "model": "unpriced-worker-model"},
        ).json()
        response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {started['session_api_key']}"},
            json={
                "model": "unpriced-worker-model",
                "messages": [{"role": "user", "content": "finish"}],
            },
        )

    assert response.status_code == 200
    artifact = db.build_session_artifact(tmp_path / "harness.db", started["session_id"])
    assert artifact["token_log"][0]["cost"] is None


def test_chat_completions_ignores_previous_day_usage_for_zone_selection(tmp_path):
    client, fake = _client(tmp_path)
    with client:
        old = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Old session", "model": "claude-haiku"},
        ).json()
        db.record_token_turn(
            tmp_path / "harness.db",
            session_id=old["session_id"],
            model="claude-haiku",
            prompt_tokens=900_000,
            completion_tokens=0,
            cost=0,
            raw_usage={"total_tokens": 900_000},
        )
        with db.connect(tmp_path / "harness.db") as conn:
            conn.execute("update token_turns set created_at = ?", ("2000-01-01T00:00:00+00:00",))

        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={
                "task_description": "New session",
                "model": "claude-haiku",
                "budget": {"daily_cap_tokens": 1_000_000},
            },
        ).json()
        response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {started['session_api_key']}"},
            json={"model": "claude-haiku", "messages": [{"role": "user", "content": "finish"}], "max_tokens": 4096},
        )

    assert response.status_code == 200
    assert fake.requests[-1]["max_tokens"] == 4096
    artifact = db.build_session_artifact(tmp_path / "harness.db", started["session_id"])
    assert artifact["guardrail_snapshots"][0]["zone"] == "green"


def test_chat_completions_honors_daily_budget_reset_window_for_zone_selection(tmp_path):
    client, fake = _client(tmp_path)
    with client:
        old = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Pre-reset spend", "model": "claude-haiku"},
        ).json()
        db.record_token_turn(
            tmp_path / "harness.db",
            session_id=old["session_id"],
            model="claude-haiku",
            prompt_tokens=900_000,
            completion_tokens=0,
            cost=0,
            raw_usage={"total_tokens": 900_000},
        )
        with db.connect(tmp_path / "harness.db") as conn:
            conn.execute("update token_turns set created_at = ?", (db.current_day_start_iso("local"),))
        db.reset_daily_budget_counter(tmp_path / "harness.db")

        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={
                "task_description": "New budget window",
                "model": "claude-haiku",
                "budget": {"daily_cap_tokens": 1_000_000},
            },
        ).json()
        response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {started['session_api_key']}"},
            json={"model": "claude-haiku", "messages": [{"role": "user", "content": "finish"}], "max_tokens": 4096},
        )

    assert response.status_code == 200
    assert fake.requests[-1]["max_tokens"] == 4096
    artifact = db.build_session_artifact(tmp_path / "harness.db", started["session_id"])
    assert artifact["guardrail_snapshots"][0]["zone"] == "green"
    assert artifact["alarms"] == []


def test_chat_completions_rejects_aborted_session(tmp_path):
    client, _fake = _client(tmp_path)
    with client:
        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Abort", "model": "claude-haiku"},
        ).json()
        with db.connect(tmp_path / "harness.db") as conn:
            conn.execute("update sessions set status = 'aborted' where id = ?", (started["session_id"],))

        response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {started['session_api_key']}"},
            json={"model": "claude-haiku", "messages": [{"role": "user", "content": "finish"}]},
        )

    assert response.status_code == 403


def test_chat_completions_worker_session_records_worker_turn(tmp_path):
    client, _fake = _client(tmp_path)
    with client:
        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Worker request", "model": "claude-haiku"},
        ).json()
        response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {started['session_api_key']}"},
            json={"model": "claude-haiku", "messages": [{"role": "user", "content": "finish"}]},
        )

    assert response.status_code == 200
    artifact = db.build_session_artifact(tmp_path / "harness.db", started["session_id"])
    assert artifact["token_log"][0]["usage_kind"] == "worker"
    assert artifact["token_log"][0]["raw_usage"]["spend_category"] == "worker_execution"
    assert artifact["token_log"][0]["raw_usage"]["usage_source"] == "harness_proxy"


def test_chat_completions_on_planning_session_records_planning_turn_and_budget_governance(tmp_path):
    client, fake = _client(tmp_path)
    with client:
        planning_session, bearer_key = db.create_planning_session(
            tmp_path / "harness.db",
            task_description="Planning anchor",
            model="claude-haiku",
        )
        response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {bearer_key}"},
            json={
                "model": "claude-haiku",
                "messages": [{"role": "user", "content": "plan something"}],
                "max_tokens": 4096,
            },
        )

    assert response.status_code == 200
    assert fake.requests[0]["max_tokens"] == 4096
    artifact = db.build_session_artifact(tmp_path / "harness.db", planning_session["id"])
    turn = artifact["token_log"][0]
    assert turn["usage_kind"] == "planning"
    assert turn["raw_usage"]["spend_category"] == "planning"
    assert turn["raw_usage"]["usage_source"] == "harness_proxy"
    assert artifact["guardrail_snapshots"][0]["zone"] == "green"


def test_chat_completions_on_planning_session_does_not_count_against_worker_session_cap(tmp_path):
    client, _fake = _client(tmp_path)
    with client:
        planning_session, bearer_key = db.create_planning_session(
            tmp_path / "harness.db",
            task_description="Planning anchor",
            model="claude-haiku",
        )
        response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {bearer_key}"},
            json={
                "model": "claude-haiku",
                "messages": [{"role": "user", "content": "plan something"}],
                "budget": {"session_cap_tokens": 500},
            },
        )

    assert response.status_code == 200
    artifact = db.build_session_artifact(tmp_path / "harness.db", planning_session["id"])
    assert {alarm["type"] for alarm in artifact["alarms"]} == set()
    assert db.session_token_breakdown(tmp_path / "harness.db", planning_session["id"])["by_category"]["worker_execution"] == 0


def test_chat_completions_planning_is_client_agnostic(tmp_path):
    client, _fake = _client(tmp_path)
    sessions = []
    with client:
        for i in range(2):
            session, bearer_key = db.create_planning_session(
                tmp_path / "harness.db",
                task_description=f"Planning anchor {i}",
                model="claude-haiku",
            )
            sessions.append((session, bearer_key))
        for _session, bearer_key in sessions:
            response = client.post(
                "/v1/chat/completions",
                headers={"Authorization": f"Bearer {bearer_key}"},
                json={"model": "claude-haiku", "messages": [{"role": "user", "content": "hi"}]},
            )
            assert response.status_code == 200

    for session, _ in sessions:
        artifact = db.build_session_artifact(tmp_path / "harness.db", session["id"])
        assert len(artifact["token_log"]) == 1
        assert artifact["token_log"][0]["usage_kind"] == "planning"
