from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from foreman_ai_hq.operator_config import control_plane_provider_defaults, load_operator_config


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path("harness.db")
    guardrails_path: Path = Path("guardrails.yaml")
    timezone: str = "local"
    control_plane_provider: str = "openai"
    # There is no code default for the Orchestrator Model: pi's inventory is the
    # sole authority, so absent configuration is *not configured*, not a fallback id.
    orchestrator_model: str | None = None
    control_plane_api_key_env: str = "FOREMAN_AI_HQ_CONTROL_API_KEY"
    control_plane_base_url: str = ""
    provider_api_key_env: str = "PROVIDER_API_KEY"
    estimator_model: str | None = None
    task_breakdown_model: str | None = None
    task_breakdown_timeout_seconds: int = 120
    portal_token_env: str = "TOKEN_TRACKER_PORTAL_TOKEN"
    portal_auth_required: bool = True
    portal_cookie_secure: bool = False
    local_runner_enabled: bool = False

    @property
    def control_plane_model(self) -> str | None:
        # Back-compat alias: the orchestrator model used to be exposed as the
        # control-plane model. Every canonical caller should read orchestrator_model.
        return self.orchestrator_model

    def __init__(
        self,
        database_path: Path | str | None = None,
        guardrails_path: Path | str | None = None,
        timezone: str | None = None,
        control_plane_provider: str | None = None,
        orchestrator_model: str | None = None,
        control_plane_model: str | None = None,
        control_plane_api_key_env: str | None = None,
        control_plane_base_url: str | None = None,
        provider_api_key_env: str | None = None,
        estimator_model: str | None = None,
        task_breakdown_model: str | None = None,
        task_breakdown_timeout_seconds: int | None = None,
        portal_token_env: str | None = None,
        portal_auth_required: bool | None = None,
        portal_cookie_secure: bool | None = None,
        local_runner_enabled: bool | None = None,
        operator_config: dict[str, Any] | None = None,
    ) -> None:
        config = load_operator_config() if operator_config is None else operator_config
        # The dataclass is frozen; initialization writes through object.__setattr__ after resolving config precedence.
        object.__setattr__(
            self,
            "database_path",
            Path(database_path or os.getenv("TOKEN_TRACKER_DATABASE_PATH") or config.get("database_path") or "harness.db"),
        )
        object.__setattr__(
            self,
            "guardrails_path",
            Path(
                guardrails_path
                or os.getenv("TOKEN_TRACKER_GUARDRAILS_PATH")
                or config.get("guardrails_path")
                or "guardrails.yaml"
            ),
        )
        object.__setattr__(
            self,
            "timezone",
            timezone or os.getenv("TOKEN_TRACKER_TIMEZONE") or config.get("timezone") or "local",
        )
        # Keep the legacy provider env field so older configs still load while control-plane settings take over.
        legacy_provider_env = (
            provider_api_key_env
            or os.getenv("TOKEN_TRACKER_PROVIDER_API_KEY_ENV")
            or config.get("provider_api_key_env")
            or "PROVIDER_API_KEY"
        )
        resolved_control_provider = (
            control_plane_provider
            or os.getenv("FOREMAN_AI_HQ_CONTROL_PROVIDER")
            or os.getenv("TOKEN_TRACKER_CONTROL_PLANE_PROVIDER")
            or config.get("control_plane_provider")
            or "openai"
        )
        provider_defaults = control_plane_provider_defaults(resolved_control_provider)
        use_provider_defaults = control_plane_provider is not None and control_plane_api_key_env is None
        default_control_api_env = provider_defaults.get("control_plane_api_key_env") if use_provider_defaults else None
        resolved_control_api_env = (
            control_plane_api_key_env
            or default_control_api_env
            or os.getenv("FOREMAN_AI_HQ_CONTROL_API_KEY_ENV")
            or os.getenv("TOKEN_TRACKER_CONTROL_PLANE_API_KEY_ENV")
            or (None if use_provider_defaults else config.get("control_plane_api_key_env"))
            or provider_defaults.get("control_plane_api_key_env")
            or "FOREMAN_AI_HQ_CONTROL_API_KEY"
        )
        # The orchestrator model is the canonical model for planning, estimation,
        # task breakdown, and Agent Review. There is no code default: a value absent
        # from every source resolves to not configured, and pi's persisted inventory
        # decides whether a present value is usable.
        resolved_orchestrator_model = (
            # Explicit constructor arguments win over ambient environment so a leaked
            # FOREMAN_AI_HQ_ORCHESTRATOR_MODEL cannot override an explicit model.
            orchestrator_model
            or control_plane_model
            or os.getenv("FOREMAN_AI_HQ_ORCHESTRATOR_MODEL")
            or config.get("orchestrator_model")
            # Read as a candidate so an existing configuration is validated against
            # the inventory rather than silently ignored.
            or config.get("control_plane_model")
            or None
        )
        object.__setattr__(
            self,
            "control_plane_provider",
            resolved_control_provider,
        )
        object.__setattr__(self, "orchestrator_model", resolved_orchestrator_model)
        object.__setattr__(self, "control_plane_api_key_env", resolved_control_api_env)
        default_control_base_url = (
            provider_defaults.get("control_plane_base_url")
            if control_plane_provider is not None and control_plane_base_url is None
            else None
        )
        object.__setattr__(
            self,
            "control_plane_base_url",
            control_plane_base_url
            or default_control_base_url
            or os.getenv("FOREMAN_AI_HQ_CONTROL_BASE_URL")
            or os.getenv("TOKEN_TRACKER_CONTROL_PLANE_BASE_URL")
            or (None if control_plane_provider is not None and control_plane_base_url is None else config.get("control_plane_base_url"))
            or provider_defaults.get("control_plane_base_url")
            or "",
        )
        object.__setattr__(
            self,
            "provider_api_key_env",
            legacy_provider_env,
        )
        object.__setattr__(
            self,
            "estimator_model",
            estimator_model or config.get("estimator_model") or resolved_orchestrator_model,
        )
        object.__setattr__(
            self,
            "task_breakdown_model",
            task_breakdown_model or config.get("task_breakdown_model") or resolved_orchestrator_model,
        )
        object.__setattr__(
            self,
            "task_breakdown_timeout_seconds",
            _positive_int(
                task_breakdown_timeout_seconds
                or os.getenv("FOREMAN_AI_HQ_TASK_BREAKDOWN_TIMEOUT_SECONDS")
                or os.getenv("TOKEN_TRACKER_TASK_BREAKDOWN_TIMEOUT_SECONDS")
                or config.get("task_breakdown_timeout_seconds"),
                120,
            ),
        )
        object.__setattr__(
            self,
            "portal_token_env",
            portal_token_env
            or os.getenv("TOKEN_TRACKER_PORTAL_TOKEN_ENV")
            or config.get("portal_token_env")
            or "TOKEN_TRACKER_PORTAL_TOKEN",
        )
        object.__setattr__(
            self,
            "portal_auth_required",
            portal_auth_required
            if portal_auth_required is not None
            else _env_bool("TOKEN_TRACKER_PORTAL_AUTH_REQUIRED", _config_bool(config, "portal_auth_required", True)),
        )
        object.__setattr__(
            self,
            "portal_cookie_secure",
            portal_cookie_secure
            if portal_cookie_secure is not None
            else _env_bool("TOKEN_TRACKER_PORTAL_COOKIE_SECURE", _config_bool(config, "portal_cookie_secure")),
        )
        object.__setattr__(
            self,
            "local_runner_enabled",
            local_runner_enabled
            if local_runner_enabled is not None
            else _env_bool("TOKEN_TRACKER_LOCAL_RUNNER", _config_bool(config, "local_runner_enabled")),
        )


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _config_bool(config: dict[str, Any], name: str, default: bool = False) -> bool:
    if name not in config:
        return default
    return bool(config.get(name))


def _positive_int(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default
