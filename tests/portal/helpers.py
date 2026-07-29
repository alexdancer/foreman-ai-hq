from pathlib import Path

from fastapi.testclient import TestClient

from foreman_ai_hq import db
from foreman_ai_hq.app import create_app
from foreman_ai_hq.project_context import project_task_metadata
from foreman_ai_hq.settings import Settings
from tests.conftest import git_project_profile

ROOT = Path(__file__).resolve().parents[2]
PORTAL_TOKEN = "test-portal-token"


class FakeControlPlaneLLM:
    def __init__(self, *, exc: Exception | None = None, cost: float | None = None):
        self.exc = exc
        self.cost = cost
        self.requests = []

    async def acompletion(self, request):
        self.requests.append(request)
        if self.exc:
            raise self.exc
        response = {
            "choices": [{"message": {"content": "FOREMAN_AI_HQ_CONTROL_PLANE_OK"}}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
            "api_key": "sk_sho...nder",
        }
        if self.cost is not None:
            response["usage"]["cost"] = self.cost
        return response


def _client(tmp_path, *, portal_auth_required: bool = True, local_runner_enabled: bool = True):
    settings = Settings(
        database_path=tmp_path / "harness.db",
        guardrails_path=ROOT / "guardrails.yaml",
        portal_auth_required=portal_auth_required,
        local_runner_enabled=local_runner_enabled,
        operator_config={},
    )
    # Explicit so the conftest hook that seeds orchestrator discovery evidence runs;
    # tests marked `unconfigured_orchestrator` get a bare database instead.
    db.init_db(settings.database_path)
    return TestClient(create_app(settings))


def _client_with_control_plane_llm(
    tmp_path,
    llm,
    *,
    control_plane_provider="anthropic",
    control_plane_model="claude-sonnet-4-6",
    control_plane_base_url="",
):
    settings = Settings(
        database_path=tmp_path / "harness.db",
        guardrails_path=ROOT / "guardrails.yaml",
        control_plane_provider=control_plane_provider,
        control_plane_model=control_plane_model,
        control_plane_api_key_env="TEST_CONTROL_PLANE_KEY",
        control_plane_base_url=control_plane_base_url,
        operator_config={},
    )
    app = create_app(settings)
    app.state.llm_client = llm
    return TestClient(app)


def _portal_headers():
    return {"Authorization": f"Bearer {PORTAL_TOKEN}"}


def _connect_project(database_path: Path, root: Path) -> dict:
    root.mkdir(exist_ok=True)
    return db.upsert_connected_project(
        database_path,
        name=root.name,
        root_path=str(root.resolve()),
        profile=git_project_profile(root),
        capability={"state": "launch_ready", "can_launch": True},
    )


def _project_metadata(database_path: Path, root: Path) -> dict:
    return project_task_metadata(_connect_project(database_path, root))
