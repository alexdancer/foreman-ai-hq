from __future__ import annotations

import os
import re
import secrets
import shlex
import tomllib
from importlib import resources
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path(".foreman/config.toml")
DEFAULT_SECRETS_PATH = Path(".foreman/secrets.env")
CONTROL_API_KEY_PLACEHOLDER = "<your-control-plane-api-key>"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"
DEFAULT_LOCAL_CONFIG: dict[str, Any] = {
    "database_path": ".foreman/harness.db",
    "guardrails_path": ".foreman/guardrails.yaml",
    "host": "127.0.0.1",
    "port": 8000,
    "portal_token_env": "TOKEN_TRACKER_PORTAL_TOKEN",
    # Harness Proxy upstream for proxy_governed Workers only; the Orchestrator Model
    # is deliberately absent, because seeding one would seed a value pi never offered.
    "control_plane_provider": "openai",
    "control_plane_api_key_env": "FOREMAN_AI_HQ_CONTROL_API_KEY",
    "local_runner_enabled": True,
}


def load_operator_config(path: Path | str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return {}
    with config_path.open("rb") as handle:
        payload = tomllib.load(handle)
    if not isinstance(payload, dict):
        return {}
    _sanitize_env_name_fields(payload)
    return payload


def write_default_operator_config(path: Path | str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = dict(DEFAULT_LOCAL_CONFIG)
    config.update(load_operator_config(config_path))
    config_path.write_text(_render_config(config), encoding="utf-8")
    return config


def write_default_guardrails_file(config: dict[str, Any], base_dir: Path | str | None = None) -> Path:
    guardrails_path = Path(str(config.get("guardrails_path") or DEFAULT_LOCAL_CONFIG["guardrails_path"]))
    if base_dir is not None and not guardrails_path.is_absolute():
        guardrails_path = Path(base_dir) / guardrails_path
    guardrails_path.parent.mkdir(parents=True, exist_ok=True)
    if not guardrails_path.exists():
        default_text = (
            resources.files("foreman_ai_hq")
            .joinpath("defaults/guardrails.yaml")
            .read_text(encoding="utf-8")
        )
        guardrails_path.write_text(default_text, encoding="utf-8")
    return guardrails_path


def update_operator_config(path: Path | str = DEFAULT_CONFIG_PATH, **updates: Any) -> dict[str, Any]:
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = dict(DEFAULT_LOCAL_CONFIG)
    config.update(load_operator_config(config_path))
    config.update({key: value for key, value in updates.items() if value is not None})
    # The OpenRouter preset branch is gone with the settings page that sent a provider.
    # `control_plane_provider_defaults` survives for the Harness Proxy upstream in settings.py.
    _sanitize_env_name_fields(config)
    config_path.write_text(_render_config(config), encoding="utf-8")
    return config


def control_plane_provider_defaults(provider: str) -> dict[str, str]:
    if provider.lower().strip() == "openrouter":
        return {
            "control_plane_api_key_env": OPENROUTER_API_KEY_ENV,
            "control_plane_base_url": OPENROUTER_BASE_URL,
        }
    return {}


def write_default_secrets_env(
    config: dict[str, Any], path: Path | str = DEFAULT_SECRETS_PATH
) -> dict[str, str]:
    secrets_path = Path(path)
    secrets_path.parent.mkdir(parents=True, exist_ok=True)
    existing = _parse_env_file(secrets_path) if secrets_path.exists() else {}
    portal_token_env, control_key_env = secret_env_names(config)
    values = dict(existing)
    values.setdefault(portal_token_env, f"foremanctl-{secrets.token_urlsafe(18)}")
    # Never invent provider credentials; leave a placeholder for the operator to replace.
    values.setdefault(control_key_env, CONTROL_API_KEY_PLACEHOLDER)
    secrets_path.write_text(_render_secrets_env(values), encoding="utf-8")
    return values


def ensure_secret_placeholder(env_name: str, path: Path | str = DEFAULT_SECRETS_PATH) -> dict[str, str]:
    secrets_path = Path(path)
    secrets_path.parent.mkdir(parents=True, exist_ok=True)
    values = _parse_env_file(secrets_path) if secrets_path.exists() else {}
    values.setdefault(env_name, CONTROL_API_KEY_PLACEHOLDER)
    secrets_path.write_text(_render_secrets_env(values), encoding="utf-8")
    return values


def write_control_plane_secret(
    env_name: str, api_key: str, path: Path | str = DEFAULT_SECRETS_PATH
) -> dict[str, str]:
    secrets_path = Path(path)
    secrets_path.parent.mkdir(parents=True, exist_ok=True)
    values = _parse_env_file(secrets_path) if secrets_path.exists() else {}
    values[env_name] = api_key
    secrets_path.write_text(_render_secrets_env(values), encoding="utf-8")
    os.environ[env_name] = api_key
    return values


def load_operator_secrets_env(
    config: dict[str, Any], path: Path | str = DEFAULT_SECRETS_PATH
) -> dict[str, str]:
    secrets_path = Path(path)
    if not secrets_path.exists():
        return {}
    values = _parse_env_file(secrets_path)
    for name, value in values.items():
        # Placeholders stay on disk but are not exported into the live process environment.
        if _is_placeholder_secret(value):
            continue
        os.environ.setdefault(name, value)
    return values


def secret_env_names(config: dict[str, Any]) -> tuple[str, str]:
    portal_token_env = str(config.get("portal_token_env") or DEFAULT_LOCAL_CONFIG["portal_token_env"])
    control_key_env = str(
        config.get("control_plane_api_key_env") or DEFAULT_LOCAL_CONFIG["control_plane_api_key_env"]
    )
    return portal_token_env, control_key_env


def secret_export_lines(config: dict[str, Any]) -> list[str]:
    portal_token_env, control_key_env = secret_env_names(config)
    portal_token = f"foremanctl-{secrets.token_urlsafe(18)}"
    return [
        f"# {portal_token_env} is the portal token for shared/non-loopback access. Replace the generated value if you want your own.",
        f"export {portal_token_env}={shlex.quote(portal_token)}",
        f"# {control_key_env} is your provider API key value: OpenAI, Anthropic, or OpenAI-compatible.",
        f"export {control_key_env}={shlex.quote(CONTROL_API_KEY_PLACEHOLDER)}",
    ]


def _render_config(config: dict[str, Any]) -> str:
    lines = [
        "# Foreman AI HQ operator config. Non-secrets only.",
        "# portal_token_env and control_plane_api_key_env are env var NAMES, not secret values.",
        "# Set actual secret values in .foreman/secrets.env. .foreman/ is ignored by git.",
    ]
    for key, value in config.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, int):
            rendered = str(value)
        else:
            rendered = _quote_toml(str(value))
        lines.append(f"{key} = {rendered}")
    return "\n".join(lines) + "\n"


def _render_secrets_env(values: dict[str, str]) -> str:
    lines = [
        "# Local Foreman AI HQ secrets. .foreman/ is ignored by git.",
        "# Edit values here instead of typing export commands.",
    ]
    for key, value in values.items():
        lines.append(f"{key}={shlex.quote(value)}")
    return "\n".join(lines) + "\n"


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = _unquote_env_value(value.strip())
    return values


def _unquote_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _is_placeholder_secret(value: str) -> bool:
    return value == CONTROL_API_KEY_PLACEHOLDER or value == ""


def _sanitize_env_name_fields(config: dict[str, Any]) -> None:
    for key in ["portal_token_env", "control_plane_api_key_env"]:
        value = config.get(key)
        # These config fields are environment variable names, so reject shell fragments or secret values.
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            config[key] = DEFAULT_LOCAL_CONFIG[key]

def _quote_toml(value: str) -> str:
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
