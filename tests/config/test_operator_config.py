import os

from foreman_ai_hq.operator_config import (
    CONTROL_API_KEY_PLACEHOLDER,
    control_plane_provider_defaults,
    OPENROUTER_API_KEY_ENV,
    OPENROUTER_BASE_URL,
    ensure_secret_placeholder,
    load_operator_config,
    update_operator_config,
    write_control_plane_secret,
)


def test_update_operator_config_preserves_unrelated_values(tmp_path):
    config_path = tmp_path / ".foreman" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text(
        'database_path = "custom.db"\n'
        'control_plane_model = "old-model"\n'
        'local_runner_enabled = true\n',
        encoding="utf-8",
    )

    config = update_operator_config(
        config_path,
        control_plane_provider="anthropic",
        control_plane_model="claude-haiku-4-5",
        control_plane_api_key_env="ANTHROPIC_API_KEY",
    )

    assert config["database_path"] == "custom.db"
    assert config["local_runner_enabled"] is True
    assert config["control_plane_provider"] == "anthropic"
    assert config["control_plane_model"] == "claude-haiku-4-5"
    assert load_operator_config(config_path)["control_plane_api_key_env"] == "ANTHROPIC_API_KEY"


def test_update_operator_config_no_longer_applies_openrouter_presets(tmp_path):
    """The preset branch went with the settings page that sent a provider.

    `control_plane_provider_defaults` itself survives for the Harness Proxy upstream
    that `settings.py` resolves for proxy_governed Workers; what is gone is
    `update_operator_config` silently rewriting connection fields behind a save.
    """
    config = update_operator_config(
        tmp_path / ".foreman" / "config.toml",
        control_plane_provider="openrouter",
    )

    assert config["control_plane_api_key_env"] != OPENROUTER_API_KEY_ENV
    assert "control_plane_base_url" not in config
    assert control_plane_provider_defaults("openrouter") == {
        "control_plane_api_key_env": OPENROUTER_API_KEY_ENV,
        "control_plane_base_url": OPENROUTER_BASE_URL,
    }


def test_ensure_secret_placeholder_adds_missing_env_without_overwriting(tmp_path):
    secrets_path = tmp_path / ".foreman" / "secrets.env"
    secrets_path.parent.mkdir()
    secrets_path.write_text("EXISTING_KEY='real-value'\n", encoding="utf-8")

    values = ensure_secret_placeholder("NEW_CONTROL_KEY", secrets_path)

    assert values["EXISTING_KEY"] == "real-value"
    assert values["NEW_CONTROL_KEY"] == CONTROL_API_KEY_PLACEHOLDER
    text = secrets_path.read_text(encoding="utf-8")
    assert "EXISTING_KEY=real-value" in text or "EXISTING_KEY='real-value'" in text
    assert f"NEW_CONTROL_KEY='{CONTROL_API_KEY_PLACEHOLDER}'" in text


def test_ensure_secret_placeholder_preserves_existing_secret(tmp_path):
    secrets_path = tmp_path / ".foreman" / "secrets.env"
    secrets_path.parent.mkdir()
    secrets_path.write_text("CONTROL_KEY='keep-me'\n", encoding="utf-8")

    values = ensure_secret_placeholder("CONTROL_KEY", secrets_path)

    assert values["CONTROL_KEY"] == "keep-me"
    assert "keep-me" in secrets_path.read_text(encoding="utf-8")


def test_write_control_plane_secret_preserves_unrelated_values_and_sets_env(tmp_path, monkeypatch):
    monkeypatch.delenv("CONTROL_KEY", raising=False)
    secrets_path = tmp_path / ".foreman" / "secrets.env"
    secrets_path.parent.mkdir()
    secrets_path.write_text("OTHER_KEY='keep-me'\nCONTROL_KEY='old-value'\n", encoding="utf-8")

    values = write_control_plane_secret("CONTROL_KEY", "DEMO_CONTROL_KEY_999", secrets_path)

    text = secrets_path.read_text(encoding="utf-8")
    assert values["OTHER_KEY"] == "keep-me"
    assert values["CONTROL_KEY"] == "DEMO_CONTROL_KEY_999"
    assert "OTHER_KEY=keep-me" in text
    assert "CONTROL_KEY=DEMO_CONTROL_KEY_999" in text
    assert os.environ["CONTROL_KEY"] == "DEMO_CONTROL_KEY_999"
