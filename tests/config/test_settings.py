from pathlib import Path


def test_settings_defaults_point_to_local_development_files(monkeypatch):
    monkeypatch.delenv("TOKEN_TRACKER_DATABASE_PATH", raising=False)
    monkeypatch.delenv("TOKEN_TRACKER_GUARDRAILS_PATH", raising=False)
    monkeypatch.delenv("TOKEN_TRACKER_TIMEZONE", raising=False)
    monkeypatch.delenv("FOREMAN_AI_HQ_CONTROL_PROVIDER", raising=False)
    monkeypatch.delenv("FOREMAN_AI_HQ_ORCHESTRATOR_MODEL", raising=False)
    monkeypatch.delenv("TOKEN_TRACKER_ORCHESTRATOR_MODEL", raising=False)
    monkeypatch.delenv("FOREMAN_AI_HQ_CONTROL_MODEL", raising=False)
    monkeypatch.delenv("FOREMAN_AI_HQ_CONTROL_API_KEY_ENV", raising=False)
    monkeypatch.delenv("FOREMAN_AI_HQ_CONTROL_BASE_URL", raising=False)
    monkeypatch.delenv("TOKEN_TRACKER_PROVIDER_API_KEY_ENV", raising=False)
    monkeypatch.delenv("TOKEN_TRACKER_ESTIMATOR_MODEL", raising=False)
    monkeypatch.delenv("TOKEN_TRACKER_TASK_BREAKDOWN_MODEL", raising=False)
    monkeypatch.delenv("TOKEN_TRACKER_TASK_BREAKDOWN_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("FOREMAN_AI_HQ_TASK_BREAKDOWN_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("TOKEN_TRACKER_PORTAL_TOKEN_ENV", raising=False)
    monkeypatch.delenv("TOKEN_TRACKER_PORTAL_COOKIE_SECURE", raising=False)

    from foreman_ai_hq.settings import Settings

    settings = Settings(operator_config={})

    assert settings.database_path == Path("harness.db")
    assert settings.guardrails_path == Path("guardrails.yaml")
    assert settings.timezone == "local"
    assert settings.control_plane_provider == "openai"
    assert settings.control_plane_model == "gpt-5.4"
    assert settings.control_plane_api_key_env == "FOREMAN_AI_HQ_CONTROL_API_KEY"
    assert settings.control_plane_base_url == ""
    assert settings.provider_api_key_env == "PROVIDER_API_KEY"
    assert settings.estimator_model == "gpt-5.4"
    assert settings.task_breakdown_model == "gpt-5.4"
    assert settings.task_breakdown_timeout_seconds == 120
    assert settings.portal_token_env == "TOKEN_TRACKER_PORTAL_TOKEN"
    assert settings.portal_cookie_secure is False


def test_settings_reads_environment_overrides(monkeypatch, tmp_path):
    database_path = tmp_path / "custom-harness.db"
    guardrails_path = tmp_path / "custom-guardrails.yaml"
    monkeypatch.setenv("TOKEN_TRACKER_DATABASE_PATH", str(database_path))
    monkeypatch.setenv("TOKEN_TRACKER_GUARDRAILS_PATH", str(guardrails_path))
    monkeypatch.setenv("TOKEN_TRACKER_TIMEZONE", "America/Chicago")
    monkeypatch.setenv("FOREMAN_AI_HQ_CONTROL_PROVIDER", "anthropic")
    monkeypatch.setenv("FOREMAN_AI_HQ_CONTROL_MODEL", "anthropic/claude-sonnet-4-20250514")
    monkeypatch.setenv("FOREMAN_AI_HQ_CONTROL_API_KEY_ENV", "CUSTOM_CONTROL_KEY")
    monkeypatch.setenv("FOREMAN_AI_HQ_CONTROL_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("TOKEN_TRACKER_PROVIDER_API_KEY_ENV", "ANTHROPIC_API_KEY")
    monkeypatch.setenv("TOKEN_TRACKER_ESTIMATOR_MODEL", "openai/gpt-4.1-mini")
    monkeypatch.setenv("TOKEN_TRACKER_TASK_BREAKDOWN_MODEL", "openai/gpt-4.1-breakdown")
    monkeypatch.setenv("TOKEN_TRACKER_TASK_BREAKDOWN_TIMEOUT_SECONDS", "240")
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN_ENV", "CUSTOM_PORTAL_TOKEN")
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_COOKIE_SECURE", "true")

    from foreman_ai_hq.settings import Settings

    settings = Settings(operator_config={})

    assert settings.database_path == database_path
    assert settings.guardrails_path == guardrails_path
    assert settings.timezone == "America/Chicago"
    assert settings.control_plane_provider == "anthropic"
    assert settings.control_plane_model == "anthropic/claude-sonnet-4-20250514"
    assert settings.control_plane_api_key_env == "CUSTOM_CONTROL_KEY"
    assert settings.control_plane_base_url == "https://provider.example/v1"
    assert settings.provider_api_key_env == "ANTHROPIC_API_KEY"
    assert settings.estimator_model == "openai/gpt-4.1-mini"
    assert settings.task_breakdown_model == "openai/gpt-4.1-breakdown"
    assert settings.task_breakdown_timeout_seconds == 240
    assert settings.portal_token_env == "CUSTOM_PORTAL_TOKEN"
    assert settings.portal_cookie_secure is True


def test_settings_keeps_legacy_estimator_model_as_control_plane_alias(monkeypatch):
    monkeypatch.delenv("FOREMAN_AI_HQ_CONTROL_MODEL", raising=False)
    monkeypatch.setenv("TOKEN_TRACKER_ESTIMATOR_MODEL", "openai/gpt-4.1-mini")

    from foreman_ai_hq.settings import Settings

    settings = Settings(operator_config={})

    assert settings.control_plane_model == "openai/gpt-4.1-mini"
    assert settings.estimator_model == "openai/gpt-4.1-mini"


def test_settings_reads_operator_config_when_env_missing(monkeypatch):
    monkeypatch.delenv("TOKEN_TRACKER_DATABASE_PATH", raising=False)
    monkeypatch.delenv("FOREMAN_AI_HQ_ORCHESTRATOR_MODEL", raising=False)
    monkeypatch.delenv("TOKEN_TRACKER_ORCHESTRATOR_MODEL", raising=False)
    monkeypatch.delenv("FOREMAN_AI_HQ_CONTROL_MODEL", raising=False)
    monkeypatch.delenv("TOKEN_TRACKER_LOCAL_RUNNER", raising=False)

    from foreman_ai_hq.settings import Settings

    settings = Settings(
        operator_config={
            "database_path": ".foreman/configured.db",
            "control_plane_model": "gpt-5.4-mini",
            "task_breakdown_timeout_seconds": 180,
            "local_runner_enabled": True,
        }
    )

    assert settings.database_path == Path(".foreman/configured.db")
    assert settings.control_plane_model == "gpt-5.4-mini"
    assert settings.task_breakdown_timeout_seconds == 180
    assert settings.local_runner_enabled is True


def test_settings_environment_overrides_operator_config(monkeypatch):
    monkeypatch.setenv("FOREMAN_AI_HQ_CONTROL_MODEL", "env-model")
    monkeypatch.setenv("TOKEN_TRACKER_LOCAL_RUNNER", "0")

    from foreman_ai_hq.settings import Settings

    settings = Settings(
        operator_config={
            "control_plane_model": "config-model",
            "local_runner_enabled": True,
        }
    )

    assert settings.control_plane_model == "env-model"
    assert settings.local_runner_enabled is False
