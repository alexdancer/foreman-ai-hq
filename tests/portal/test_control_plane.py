import os

import pytest
from fastapi.testclient import TestClient

from foreman_ai_hq import db
from foreman_ai_hq.app import create_app
from foreman_ai_hq.operator_config import CONTROL_API_KEY_PLACEHOLDER, load_operator_config
from foreman_ai_hq.settings import Settings
from tests.portal.helpers import (
    ROOT,
    PORTAL_TOKEN,
    FakeControlPlaneLLM,
    _client,
    _client_with_control_plane_llm,
    _portal_headers,
)


def test_control_plane_save_persists_and_hot_swaps_settings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    for name in [
        "FOREMAN_AI_HQ_CONTROL_PROVIDER",
        "FOREMAN_AI_HQ_CONTROL_MODEL",
        "FOREMAN_AI_HQ_CONTROL_BASE_URL",
        "FOREMAN_AI_HQ_CONTROL_API_KEY_ENV",
        "FOREMAN_AI_HQ_ESTIMATOR_MODEL",
        "FOREMAN_AI_HQ_TASK_BREAKDOWN_MODEL",
    ]:
        monkeypatch.delenv(name, raising=False)

    class CapturingLLM:
        def __init__(self, settings):
            self.settings = settings
            self.requests = []

        async def acompletion(self, request):
            self.requests.append(request)
            return {"choices": [{"message": {"content": "FOREMAN_AI_HQ_CONTROL_PLANE_OK"}}]}

    from foreman_ai_hq.routes import portal

    monkeypatch.setattr(portal, "LLMClient", CapturingLLM)
    app = create_app(Settings(database_path=tmp_path / "harness.db", guardrails_path=ROOT / "guardrails.yaml"))
    with TestClient(app) as client:
        response = client.post(
            "/settings/control-plane",
            headers=_portal_headers(),
            json={
                "control_plane_provider": "anthropic",
                "control_plane_model": "claude-haiku-4-5",
                "control_plane_base_url": "",
                "control_plane_api_key_env": "ANTHROPIC_API_KEY",
                "apply_to_estimator_breakdown": True,
            },
        )
        test_response = client.post("/settings/control-plane/test", headers=_portal_headers())
        app_settings = app.state.settings
        llm = app.state.llm_client

    assert response.status_code == 200
    body = response.json()
    assert body["settings"]["control_plane_provider"] == "anthropic"
    assert body["settings"]["orchestrator_model"] == "claude-haiku-4-5"
    assert body["settings"]["estimator_model"] == "claude-haiku-4-5"
    assert body["settings"]["task_breakdown_model"] == "claude-haiku-4-5"
    assert body["status"]["online"] is False
    assert body["status"]["details"]["status"] == "needs_test"
    assert app_settings.control_plane_api_key_env == "ANTHROPIC_API_KEY"
    assert llm.settings.control_plane_model == "claude-haiku-4-5"
    assert test_response.status_code == 200
    assert llm.requests[0]["model"] == "claude-haiku-4-5"
    config = load_operator_config(tmp_path / ".foreman" / "config.toml")
    assert config["control_plane_provider"] == "anthropic"
    assert config["control_plane_model"] == "claude-haiku-4-5"
    assert config["estimator_model"] == "claude-haiku-4-5"
    assert config["task_breakdown_model"] == "claude-haiku-4-5"
    assert config["control_plane_api_key_env"] == "ANTHROPIC_API_KEY"
    secrets_text = (tmp_path / ".foreman" / "secrets.env").read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY" in secrets_text
    assert CONTROL_API_KEY_PLACEHOLDER in secrets_text

def test_control_plane_save_updates_bootstrap_env_override(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.setenv("FOREMAN_AI_HQ_CONTROL_PROVIDER", "openai")
    monkeypatch.setenv("FOREMAN_AI_HQ_CONTROL_MODEL", "gpt-5.4")
    monkeypatch.setenv("FOREMAN_AI_HQ_CONTROL_API_KEY_ENV", "FOREMAN_AI_HQ_CONTROL_API_KEY")

    app = create_app(Settings(database_path=tmp_path / "harness.db", guardrails_path=ROOT / "guardrails.yaml"))
    with TestClient(app) as client:
        response = client.post(
            "/settings/control-plane",
            headers=_portal_headers(),
            json={
                "control_plane_provider": "openai",
                "control_plane_model": "gpt-5.5",
                "control_plane_base_url": "",
                "control_plane_api_key_env": "FOREMAN_AI_HQ_CONTROL_API_KEY",
                "apply_to_estimator_breakdown": True,
            },
        )

    assert response.status_code == 200
    assert response.json()["settings"]["orchestrator_model"] == "gpt-5.5"
    assert app.state.settings.control_plane_model == "gpt-5.5"
    assert app.state.settings.estimator_model == "gpt-5.5"
    assert os.environ["FOREMAN_AI_HQ_CONTROL_MODEL"] == "gpt-5.5"
    assert load_operator_config(tmp_path / ".foreman" / "config.toml")["control_plane_model"] == "gpt-5.5"

def test_control_plane_save_loads_existing_secret_env_for_new_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.delenv("NEW_CONTROL_KEY", raising=False)
    secrets_path = tmp_path / ".foreman" / "secrets.env"
    secrets_path.parent.mkdir()
    secrets_path.write_text("NEW_CONTROL_KEY='real-test-key'\n", encoding="utf-8")

    app = create_app(Settings(database_path=tmp_path / "harness.db", guardrails_path=ROOT / "guardrails.yaml"))
    with TestClient(app) as client:
        response = client.post(
            "/settings/control-plane",
            headers=_portal_headers(),
            json={
                "control_plane_provider": "openai",
                "control_plane_model": "gpt-5.4",
                "control_plane_base_url": "",
                "control_plane_api_key_env": "NEW_CONTROL_KEY",
            },
        )

    assert response.status_code == 200
    assert os.getenv("NEW_CONTROL_KEY") == "real-test-key"


def test_control_plane_save_defaults_openrouter_connection_and_secret_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with _client(tmp_path) as client:
        response = client.post(
            "/settings/control-plane",
            headers=_portal_headers(),
            json={
                "control_plane_provider": "openrouter",
                "control_plane_model": "anthropic/claude-sonnet-5",
            },
        )

    assert response.status_code == 200
    settings = response.json()["settings"]
    assert settings["control_plane_provider"] == "openrouter"
    assert settings["control_plane_api_key_env"] == "OPENROUTER_API_KEY"
    assert settings["control_plane_base_url"] == "https://openrouter.ai/api/v1"
    config = load_operator_config(tmp_path / ".foreman" / "config.toml")
    assert config["control_plane_api_key_env"] == "OPENROUTER_API_KEY"
    assert config["control_plane_base_url"] == "https://openrouter.ai/api/v1"
    assert "OPENROUTER_API_KEY" in (tmp_path / ".foreman" / "secrets.env").read_text(encoding="utf-8")


def test_control_plane_save_writes_submitted_api_key_without_config_leak(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    app = create_app(Settings(database_path=tmp_path / "harness.db", guardrails_path=ROOT / "guardrails.yaml"))
    with TestClient(app) as client:
        response = client.post(
            "/settings/control-plane",
            headers=_portal_headers(),
            json={
                "control_plane_provider": "anthropic",
                "control_plane_model": "claude-haiku-4-5",
                "control_plane_base_url": "",
                "control_plane_api_key_env": "ANTHROPIC_API_KEY",
                "control_plane_api_key": "DEMO_KEY_VALUE_999",
            },
        )
        # The Jinja settings page used to be the oracle for "the key was saved and
        # never rendered back"; that page is retired, so both halves of the claim
        # move to the JSON handoff (design Decision 9, bucket 1: backend state).
        handoff = client.get("/api/settings/control-plane", headers=_portal_headers())

    assert response.status_code == 200
    assert os.getenv("ANTHROPIC_API_KEY") == "DEMO_KEY_VALUE_999"
    config_text = (tmp_path / ".foreman" / "config.toml").read_text(encoding="utf-8")
    secrets_text = (tmp_path / ".foreman" / "secrets.env").read_text(encoding="utf-8")
    assert "DEMO_KEY_VALUE_999" not in config_text
    assert "ANTHROPIC_API_KEY=DEMO_KEY_VALUE_999" in secrets_text
    assert "DEMO_KEY_VALUE_999" not in str(response.json())
    assert "DEMO_KEY_VALUE_999" not in handoff.text
    assert handoff.json()["api_key_present"] is True


def test_control_plane_blank_api_key_preserves_existing_secret(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    secrets_path = tmp_path / ".foreman" / "secrets.env"
    secrets_path.parent.mkdir()
    secrets_path.write_text("ANTHROPIC_API_KEY='DEMO_KEY_VALUE_999'\n", encoding="utf-8")

    app = create_app(Settings(database_path=tmp_path / "harness.db", guardrails_path=ROOT / "guardrails.yaml"))
    with TestClient(app) as client:
        response = client.post(
            "/settings/control-plane",
            headers=_portal_headers(),
            json={
                "control_plane_provider": "anthropic",
                "control_plane_model": "claude-haiku-4-5",
                "control_plane_base_url": "",
                "control_plane_api_key_env": "ANTHROPIC_API_KEY",
                "control_plane_api_key": "",
            },
        )

    text = secrets_path.read_text(encoding="utf-8")
    assert response.status_code == 200
    assert "DEMO_KEY_VALUE_999" in text
    assert CONTROL_API_KEY_PLACEHOLDER not in text
    assert os.getenv("ANTHROPIC_API_KEY") == "DEMO_KEY_VALUE_999"

def test_control_plane_save_rejects_blank_model_and_invalid_base_url(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        blank_model = client.post(
            "/settings/control-plane",
            headers=_portal_headers(),
            json={
                "control_plane_provider": "openai",
                "control_plane_model": "   ",
                "control_plane_base_url": "",
                "control_plane_api_key_env": "OPENAI_API_KEY",
            },
        )
        invalid_base_url = client.post(
            "/settings/control-plane",
            headers=_portal_headers(),
            json={
                "control_plane_provider": "openai-compatible",
                "control_plane_model": "custom-model",
                "control_plane_base_url": "not a url",
                "control_plane_api_key_env": "COMPATIBLE_API_KEY",
            },
        )
        missing_base_url = client.post(
            "/settings/control-plane",
            headers=_portal_headers(),
            json={
                "control_plane_provider": "openai-compatible",
                "control_plane_model": "custom-model",
                "control_plane_base_url": "",
                "control_plane_api_key_env": "COMPATIBLE_API_KEY",
                "control_plane_api_key": "DEMO_SECRET_VALUE_999",
            },
        )
        unresolved_custom = client.post(
            "/settings/control-plane",
            headers=_portal_headers(),
            json={
                "control_plane_provider": "openai-compatible",
                "control_plane_model": "__custom__",
                "control_plane_base_url": "https://example.invalid/v1",
                "control_plane_api_key_env": "COMPATIBLE_API_KEY",
            },
        )

    assert blank_model.status_code == 422
    assert invalid_base_url.status_code == 422
    assert missing_base_url.status_code == 422
    assert unresolved_custom.status_code == 422
    assert "DEMO_SECRET_VALUE_999" not in missing_base_url.text
    assert all("input" not in detail for detail in missing_base_url.json()["detail"])

def test_control_plane_save_failure_keeps_running_settings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    from foreman_ai_hq.routes import portal

    def fail_write(**_updates):
        raise OSError("disk full")

    monkeypatch.setattr(portal, "update_operator_config", fail_write)
    app = create_app(Settings(database_path=tmp_path / "harness.db", guardrails_path=ROOT / "guardrails.yaml"))
    with TestClient(app) as client:
        before = app.state.settings
        response = client.post(
            "/settings/control-plane",
            headers=_portal_headers(),
            json={
                "control_plane_provider": "anthropic",
                "control_plane_model": "claude-haiku-4-5",
                "control_plane_base_url": "",
                "control_plane_api_key_env": "ANTHROPIC_API_KEY",
            },
        )
        after = app.state.settings

    assert response.status_code == 500
    assert before is after
    assert after.control_plane_model != "claude-haiku-4-5"

def test_control_plane_settings_json_handoff_shows_presets_and_needs_test(tmp_path, monkeypatch):
    """Backend-state half of the retired preset/needs-test settings page.

    The old test also asserted Jinja-only markup (a plain ``<select>`` with no
    datalist, a password-typed input, an "Advanced connection settings"
    <details> disclosure, static copy like "Leave blank to keep the existing
    key"). None of that is backend state -- it is retired Jinja presentation
    with no server-computed value behind it, so it is dropped rather than
    reinvented against React's actual (structurally different) markup.
    """

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    db.upsert_execution_backend_status(
        database_path,
        "control_plane_model",
        name="Control Plane Model",
        online=False,
        details={"status": "needs_test", "reason": "configuration changed; test required"},
    )
    with _client(tmp_path) as client:
        response = client.get("/api/settings/control-plane", headers=_portal_headers())
        setup = client.get("/api/setup", headers=_portal_headers())

    assert response.status_code == 200
    body = response.json()
    curated = {(model["provider"], model["model"]): model["label"] for model in body["curated_models"]}
    assert set(curated) == {
        ("openai", "gpt-5.6-sol"),
        ("openai", "gpt-5.6-terra"),
        ("openai", "gpt-5.6-luna"),
        ("anthropic", "claude-fable-5"),
        ("anthropic", "claude-sonnet-5"),
        ("anthropic", "claude-opus-4-8"),
        ("anthropic", "claude-haiku-4-5"),
        ("openrouter", "anthropic/claude-sonnet-5"),
        ("openrouter", "openai/gpt-5.6-terra"),
        ("openrouter", "google/gemini-3.5-flash"),
    }
    assert body["connection_status"]["state"] == "needs_test"

    assert setup.status_code == 200
    control_plane_step = next(
        step for step in setup.json()["steps"] if step["name"] == "Control plane model"
    )
    assert control_plane_step["state"] == "needs test"

def test_control_plane_json_handoff_separates_control_model_from_worker_auth(tmp_path, monkeypatch):
    """Backend-state half of the retired control-model/worker-auth separation page.

    The static copy this used to check ("Foreman AI HQ orchestration model",
    "Worker Harness") is presentational Jinja text with no backend computation
    behind it -- dropped, not reinvented. The redaction claim (the raw secret
    and its old truncated-markup form must never render) is real backend
    behavior and stays, migrated to the JSON handoff.
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.setenv("TEST_CONTROL_PLANE_KEY", "sk_should_not_render")
    with _client_with_control_plane_llm(tmp_path, FakeControlPlaneLLM()) as client:
        response = client.get("/api/settings/control-plane", headers=_portal_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "anthropic"
    assert body["model"] == "claude-sonnet-4-6"
    assert body["api_key_env"] == "TEST_CONTROL_PLANE_KEY"
    assert body["api_key_present"] is True
    curated_by_model = {model["model"]: model["provider"] for model in body["curated_models"]}
    assert curated_by_model["gpt-5.6-sol"] == "openai"
    assert curated_by_model["gpt-5.6-terra"] == "openai"
    assert curated_by_model["gpt-5.6-luna"] == "openai"
    assert curated_by_model["claude-fable-5"] == "anthropic"
    assert curated_by_model["claude-sonnet-5"] == "anthropic"
    assert curated_by_model["claude-opus-4-8"] == "anthropic"
    assert curated_by_model["claude-haiku-4-5"] == "anthropic"
    assert "sk_should_not_render" not in response.text
    assert "sk_sho...nder" not in response.text


@pytest.mark.parametrize(
    "control_plane_provider,control_plane_model,control_plane_base_url",
    [
        pytest.param("anthropic", "acme/custom-control-plane-999", "", id="existing_custom_model"),
        pytest.param(
            "openai-compatible",
            "openai-compatible/custom-control-plane-999",
            "https://example.invalid/v1",
            id="openai_compatible_model",
        ),
        pytest.param("openai", "claude-sonnet-4-6", "", id="provider_incompatible_curated_name"),
        pytest.param(
            "anthropic",
            "anthropic/claude-sonnet-4-20250514",
            "",
            id="stale_provider_prefixed_model",
        ),
    ],
)
def test_control_plane_json_handoff_echoes_stored_model_verbatim_for_react_custom_resolution(
    tmp_path, monkeypatch, control_plane_provider, control_plane_model, control_plane_base_url,
):
    """Consolidates the four retired "preserves ... as custom" tests.

    Each used to assert Jinja rendered ``<option selected>``/``hidden``/
    ``disabled`` markup, hand-picking which stored (provider, model) pair the
    *server* decided was "custom". That decision no longer exists server-side:
    ``ControlPlaneSettings.jsx``'s ``dataToForm`` now makes it entirely
    client-side, by checking whether (provider, model) is present in
    ``curated_models``. The four cases here differ only in *what string is
    stored*, so the backend's whole remaining job is to store and echo that
    string back unmodified -- which is what all four really tested underneath
    the retired markup. The client-side custom-vs-curated resolution itself is
    covered by "ControlPlaneSettings dataToForm resolves curated vs. custom
    models by provider+model pair" in frontend/tests/shell.test.mjs.
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client_with_control_plane_llm(
        tmp_path,
        FakeControlPlaneLLM(),
        control_plane_provider=control_plane_provider,
        control_plane_model=control_plane_model,
        control_plane_base_url=control_plane_base_url,
    ) as client:
        response = client.get("/api/settings/control-plane", headers=_portal_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == control_plane_provider
    assert body["model"] == control_plane_model
    assert body["api_key_env"] == "TEST_CONTROL_PLANE_KEY"

def test_control_plane_form_custom_model_submission_uses_custom_value(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    custom_model = "acme/custom-control-plane-999"

    with _client(tmp_path) as client:
        # Any form-encoded POST to this route is treated as a browser submission
        # and always 303-redirects to the (retired) settings page regardless of
        # Accept (see `_control_plane_payload_from_request` in routes/portal.py),
        # so the persisted state is verified through `load_operator_config`
        # instead of reading the response body.
        response = client.post(
            "/settings/control-plane",
            headers=_portal_headers(),
            data={
                "control_plane_provider": "openai-compatible",
                "control_plane_model": "__custom__",
                "custom_control_plane_model": custom_model,
                "control_plane_base_url": "https://example.invalid/v1",
                "control_plane_api_key_env": "COMPATIBLE_API_KEY",
                "apply_to_estimator_breakdown": "on",
            },
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/settings/control-plane"
    config = load_operator_config(tmp_path / ".foreman" / "config.toml")
    assert config["control_plane_provider"] == "openai-compatible"
    assert config["control_plane_model"] == custom_model
    assert config["estimator_model"] == custom_model
    assert config["task_breakdown_model"] == custom_model

def test_control_plane_connection_test_records_sanitized_status(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeControlPlaneLLM()
    with _client_with_control_plane_llm(tmp_path, llm) as client:
        response = client.post("/settings/control-plane/test", headers=_portal_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["passed"] is True
    assert body["status"]["online"] is True
    assert body["status"]["details"]["model"] == "claude-sonnet-4-6"
    assert body["status"]["details"]["usage"]["total_tokens"] == 10
    assert "«redacted:sk_…»" not in str(body)
    assert llm.requests[0]["model"] == "claude-sonnet-4-6"


def test_control_plane_connection_test_records_reported_cost(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeControlPlaneLLM(cost=0.0042)
    with _client_with_control_plane_llm(
        tmp_path,
        llm,
        control_plane_provider="openrouter",
        control_plane_model="anthropic/claude-sonnet-5",
        control_plane_base_url="https://openrouter.ai/api/v1",
    ) as client:
        response = client.post("/settings/control-plane/test", headers=_portal_headers())

    assert response.status_code == 200
    assert response.json()["status"]["details"]["cost"] == pytest.approx(0.0042)


def test_control_plane_connection_test_browser_success_returns_to_settings_ui(tmp_path, monkeypatch):
    """The POST redirect is unchanged (design Decision 8: action-endpoint
    redirects stay as-is). The "then read the settings page" half migrates to
    the JSON handoff -- the Jinja page it used to read no longer exists.
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeControlPlaneLLM()
    headers = {**_portal_headers(), "accept": "text/html"}
    with _client_with_control_plane_llm(tmp_path, llm) as client:
        response = client.post("/settings/control-plane/test", headers=headers, follow_redirects=False)
        handoff = client.get("/api/settings/control-plane", headers=_portal_headers())

    assert response.status_code == 303
    assert response.headers["location"] == "/settings/control-plane"
    body = handoff.json()
    assert body["connection_status"]["state"] == "online"
    assert body["connection_status"]["details"]["usage"]["total_tokens"] == 10
    assert "sk_sho...nder" not in handoff.text

def test_control_plane_connection_test_does_not_cap_gpt5_smoke_response(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeControlPlaneLLM()
    with _client_with_control_plane_llm(
        tmp_path,
        llm,
        control_plane_provider="openai",
        control_plane_model="gpt-5.4",
    ) as client:
        response = client.post("/settings/control-plane/test", headers=_portal_headers())

    assert response.status_code == 200
    assert llm.requests[0]["model"] == "gpt-5.4"
    assert "max_tokens" not in llm.requests[0]
    assert "max_completion_tokens" not in llm.requests[0]

def test_control_plane_connection_failure_records_no_secret_values(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeControlPlaneLLM(exc=RuntimeError("secret sk_bad_key"))
    with _client_with_control_plane_llm(tmp_path, llm) as client:
        response = client.post("/settings/control-plane/test", headers=_portal_headers())

    assert response.status_code == 503
    body = response.json()
    assert body["passed"] is False
    assert body["status"]["online"] is False
    assert "sk_bad_key" not in str(body)
    assert "***REDACTED***" in body["status"]["details"]["error"]


def test_control_plane_connection_test_browser_failure_returns_to_settings_ui(tmp_path, monkeypatch):
    """The POST redirect is unchanged (design Decision 8). The "then read the
    settings page" half migrates to the JSON handoff, same as the success case.
    """

    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    llm = FakeControlPlaneLLM(exc=RuntimeError("secret sk_bad_key"))
    headers = {**_portal_headers(), "accept": "text/html"}
    with _client_with_control_plane_llm(tmp_path, llm) as client:
        response = client.post("/settings/control-plane/test", headers=headers, follow_redirects=False)
        handoff = client.get("/api/settings/control-plane", headers=_portal_headers())

    assert response.status_code == 303
    assert response.headers["location"] == "/settings/control-plane"
    body = handoff.json()
    assert body["connection_status"]["state"] == "offline"
    assert body["connection_status"]["details"]["error_type"] == "RuntimeError"
    assert "***REDACTED***" in body["connection_status"]["details"]["error"]
    assert "sk_bad_key" not in handoff.text

