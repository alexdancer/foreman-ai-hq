from pathlib import Path

from fastapi.testclient import TestClient

from foreman_ai_hq import db
from foreman_ai_hq.app import create_app
from foreman_ai_hq.settings import Settings

ROOT = Path(__file__).resolve().parents[2]


class FakeStreamingLLMClient:
    def __init__(self):
        self.requests = []

    async def acompletion(self, request):
        self.requests.append(request)

        async def chunks():
            yield {"id": "chunk-1", "choices": [{"delta": {"content": "hel"}}]}
            yield {"id": "chunk-2", "choices": [{"delta": {"content": "lo"}}], "usage": {"prompt_tokens": 999, "completion_tokens": 999, "total_tokens": 1998}}
            yield {"id": "chunk-3", "choices": [], "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6}}

        return chunks()


class FakeCostStreamingLLMClient:
    async def acompletion(self, _request):
        async def chunks():
            yield {
                "id": "chunk-1",
                "choices": [{"delta": {"content": "done"}}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
            }
            yield {
                "id": "chunk-2",
                "choices": [],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost": 0.0042},
            }

        return chunks()


def test_streaming_chat_completions_passes_chunks_and_persists_final_usage_only(tmp_path):
    settings = Settings(database_path=tmp_path / "harness.db", guardrails_path=ROOT / "guardrails.yaml")
    app = create_app(settings)
    fake = FakeStreamingLLMClient()
    app.state.llm_client = fake

    with TestClient(app) as client:
        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Stream request", "model": "claude-haiku"},
        ).json()
        with client.stream(
            "POST",
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {started['session_api_key']}"},
            json={"model": "claude-haiku", "messages": [{"role": "user", "content": "hi"}], "stream": True},
        ) as response:
            body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert "data: " in body
    assert '"content":"hel"' in body
    assert '"content":"lo"' in body
    assert body.rstrip().endswith("data: [DONE]")
    assert fake.requests[0]["stream_options"] == {"include_usage": True}

    artifact = db.build_session_artifact(tmp_path / "harness.db", started["session_id"])
    assert artifact["token_log"][0]["prompt_tokens"] == 4
    assert artifact["token_log"][0]["completion_tokens"] == 2
    assert artifact["token_log"][0]["total_tokens"] == 6
    assert artifact["guardrail_snapshots"][0]["zone"] == "green"


def test_streaming_chat_completions_records_cost_from_zero_token_usage_tail(tmp_path):
    settings = Settings(database_path=tmp_path / "harness.db", guardrails_path=ROOT / "guardrails.yaml")
    app = create_app(settings)
    app.state.llm_client = FakeCostStreamingLLMClient()

    with TestClient(app) as client:
        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Stream request", "model": "claude-haiku"},
        ).json()
        with client.stream(
            "POST",
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {started['session_api_key']}"},
            json={"model": "claude-haiku", "messages": [{"role": "user", "content": "hi"}], "stream": True},
        ) as response:
            response.read()

    artifact = db.build_session_artifact(tmp_path / "harness.db", started["session_id"])
    assert response.status_code == 200
    assert artifact["token_log"][0]["total_tokens"] == 6
    assert artifact["token_log"][0]["cost"] == 0.0042


def test_streaming_chat_completions_on_planning_session_records_planning_turn(tmp_path):
    settings = Settings(database_path=tmp_path / "harness.db", guardrails_path=ROOT / "guardrails.yaml")
    app = create_app(settings)
    app.state.llm_client = FakeStreamingLLMClient()

    with TestClient(app) as client:
        planning_session, bearer_key = db.create_planning_session(
            tmp_path / "harness.db",
            task_description="Planning stream",
            model="claude-haiku",
        )
        with client.stream(
            "POST",
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {bearer_key}"},
            json={"model": "claude-haiku", "messages": [{"role": "user", "content": "hi"}], "stream": True},
        ) as response:
            response.read()

    assert response.status_code == 200
    artifact = db.build_session_artifact(tmp_path / "harness.db", planning_session["id"])
    assert artifact["token_log"][0]["usage_kind"] == "planning"
    assert artifact["token_log"][0]["raw_usage"]["spend_category"] == "planning"
