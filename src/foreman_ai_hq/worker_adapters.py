from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol, TypedDict

from foreman_ai_hq import db
from foreman_ai_hq.model_identity import looks_like_model_id
from foreman_ai_hq.native_usage import native_sentinel_matched, parse_native_usage_evidence
from foreman_ai_hq.native_cli_diagnostics import (
    native_cli_diagnostic,
    redact_cli_value,
    redact_native_cli_text,
)
from foreman_ai_hq.tracking_modes import NATIVE_USAGE, OBSERVED_ONLY, PROXY_GOVERNED
from foreman_ai_hq.worker_model_allowlist import (
    allowed_worker_model_ids,
    selectable_worker_model_ids,
)

SENTINEL_RESPONSE = "FOREMAN_AI_HQ_ADAPTER_OK"
SENTINEL_PROMPT = (
    "Verification only. Do not read files, write files, run tools, or inspect the repository. "
    f"Reply exactly {SENTINEL_RESPONSE}"
)
SECRET_ENV_TERMS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "AUTHORIZATION")
SUBPROCESS_RUNNER_TIMEOUT_SECONDS = 60
CODEX_AGENT_LAUNCH_TIMEOUT_SECONDS = 600
OPENCODE_AGENT_LAUNCH_TIMEOUT_SECONDS = 600
CLAUDE_CODE_AGENT_LAUNCH_TIMEOUT_SECONDS = 600
SECRET_COMMAND_FLAGS = {
    "--api-key",
    "--apikey",
    "--token",
    "--secret",
    "--password",
    "--authorization",
}


@dataclass(frozen=True)
class CommandPlan:
    command: list[str]
    cwd: Path | None
    env: dict[str, str]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    adapter_id: str
    session_id: str
    reasons: list[str]
    evidence: dict[str, Any]


@dataclass(frozen=True)
class ModelDiscoveryResult:
    passed: bool
    adapter_id: str
    models: list[str]
    reasons: list[str]
    evidence: dict[str, Any]


class Runner(Protocol):
    def __call__(self, plan: CommandPlan) -> Any: ...


class CommonEvent(TypedDict):
    kind: str
    title: str
    detail: dict[str, Any]


class WorkerAdapterBuilder:
    api_key_env = "OPENAI_API_KEY"
    base_url_env = "OPENAI_BASE_URL"

    def __init__(self, adapter: dict[str, Any]) -> None:
        self.adapter = adapter
        self.config = adapter.get("config", {})

    def supports_model(self, model: str) -> bool:
        supported = allowed_worker_model_ids(self.adapter)
        return bool(supported and model in supported)

    def map_stream_event(self, raw_line: str) -> CommonEvent | None:
        payload = _stream_payload(raw_line)
        return _generic_stream_event(payload) if payload is not None else None

    def build_verification_command(
        self,
        *,
        model: str,
        prompt: str,
        proxy_url: str,
        session_api_key: str,
    ) -> CommandPlan:
        return self._build_command(
            template_key="verification_template",
            fallback=[self.config.get("command") or self.adapter["kind"], "{prompt}"],
            model=model,
            prompt=prompt,
            proxy_url=proxy_url,
            session_api_key=session_api_key,
            purpose="adapter_verification",
        )

    def build_native_verification_command(
        self,
        *,
        model: str,
        prompt: str,
    ) -> CommandPlan:
        workdir = self.adapter.get("workdir")
        template = self._normalize_template(
            "native_verification_template",
            self.config.get("native_verification_template") or self._default_native_verification_template(),
        )
        command = [
            str(part).format(
                model=model,
                prompt=prompt,
                workdir=workdir or "",
                max_budget_usd=self._native_budget_cap("verification_max_budget_usd", default="0.10"),
            )
            for part in template
        ]
        return CommandPlan(
            command=command,
            cwd=Path(workdir) if workdir else None,
            env={},
            metadata={
                "adapter_id": self.adapter["id"],
                "kind": self.adapter["kind"],
                "model": model,
                "purpose": "native_adapter_verification",
                "project_root": str(workdir) if workdir else None,
                "prompt_argument_indices": _prompt_argument_indices(command, prompt),
                "tracking_mode": "native_usage",
                **self._timeout_metadata("verification_timeout_seconds"),
            },
        )

    def _default_native_verification_template(self) -> list[str]:
        command = self.config.get("command") or self.adapter["kind"]
        return [str(command), "run", "--model", "{model}", "--format", "json", "{prompt}"]

    def build_native_launch_command(
        self,
        *,
        model: str,
        task_prompt: str,
        project_root: str | None = None,
        read_only: bool = False,
    ) -> CommandPlan:
        workdir = project_root or self.adapter.get("workdir")
        template = self._normalize_template(
            "native_launch_template",
            self.config.get("native_launch_template") or self._default_native_launch_template(),
            read_only=read_only,
        )
        command = [
            str(part).format(
                model=model,
                prompt=task_prompt,
                workdir=workdir or "",
                max_budget_usd=self._native_budget_cap("launch_max_budget_usd", default="1.00"),
            )
            for part in template
        ]
        return CommandPlan(
            command=command,
            cwd=Path(workdir) if workdir else None,
            env={},
            metadata={
                "adapter_id": self.adapter["id"],
                "kind": self.adapter["kind"],
                "model": model,
                "purpose": "task_launch",
                "project_root": str(workdir) if workdir else None,
                "prompt_argument_indices": _prompt_argument_indices(command, task_prompt),
                "tracking_mode": "native_usage",
                "usage_source": "native_usage",
                "read_only": read_only,
                **self._timeout_metadata("launch_timeout_seconds"),
            },
        )

    def _default_native_launch_template(self) -> list[str]:
        command = self.config.get("command") or self.adapter["kind"]
        return [str(command), "run", "--model", "{model}", "--format", "json", "{prompt}"]

    def build_launch_command(
        self,
        *,
        model: str,
        task_prompt: str,
        proxy_url: str,
        session_api_key: str,
        project_root: str | None = None,
        read_only: bool = False,
    ) -> CommandPlan:
        return self._build_command(
            template_key="launch_template",
            fallback=[self.config.get("command") or self.adapter["kind"], "{prompt}"],
            model=model,
            prompt=task_prompt,
            proxy_url=proxy_url,
            session_api_key=session_api_key,
            purpose="task_launch",
            project_root=project_root,
            read_only=read_only,
        )

    def _build_command(
        self,
        *,
        template_key: str,
        fallback: list[str],
        model: str,
        prompt: str,
        proxy_url: str,
        session_api_key: str,
        purpose: str,
        project_root: str | None = None,
        read_only: bool = False,
    ) -> CommandPlan:
        template = self._normalize_template(template_key, self.config.get(template_key) or fallback, read_only=read_only)
        command = [
            str(part).format(
                model=model,
                prompt=prompt,
                proxy_url=proxy_url,
                session_api_key=session_api_key,
            )
            for part in template
        ]
        env = self._env(proxy_url=proxy_url, session_api_key=session_api_key)
        for key, value in (self.config.get("env") or {}).items():
            # Session credentials are injected by the harness; adapter config cannot override secrets.
            if not _is_secret_name(key):
                env[str(key)] = str(value)
        workdir = project_root or self.adapter.get("workdir")
        return CommandPlan(
            command=command,
            cwd=Path(workdir) if workdir else None,
            env=env,
            metadata={
                "adapter_id": self.adapter["id"],
                "kind": self.adapter["kind"],
                "model": model,
                "purpose": purpose,
                "prompt_argument_indices": _prompt_argument_indices(command, prompt),
                "read_only": read_only,
                **self._timeout_metadata(
                    "verification_timeout_seconds" if purpose == "adapter_verification" else "launch_timeout_seconds"
                ),
            },
        )

    def _env(self, *, proxy_url: str, session_api_key: str) -> dict[str, str]:
        return {
            self.base_url_env: proxy_url,
            self.api_key_env: session_api_key,
            "FOREMAN_AI_HQ_PROXY_URL": proxy_url,
            "FOREMAN_AI_HQ_SESSION_API_KEY": session_api_key,
        }

    def _normalize_template(self, template_key: str, template: list[Any], read_only: bool = False) -> list[Any]:
        return template

    def _timeout_metadata(self, purpose_key: str) -> dict[str, int]:
        timeout = self.config.get(purpose_key, self.config.get("subprocess_timeout_seconds"))
        if timeout is None:
            return {}
        try:
            seconds = int(timeout)
        except (TypeError, ValueError):
            return {}
        return {"timeout_seconds": seconds} if seconds > 0 else {}

    def _native_budget_cap(self, key: str, *, default: str) -> str:
        value = self.config.get(key, self.config.get("max_budget_usd", default))
        try:
            cap = float(value)
        except (TypeError, ValueError):
            return default
        return f"{cap:.2f}" if cap > 0 else default


class ClaudeCodeAdapterBuilder(WorkerAdapterBuilder):
    api_key_env = "ANTHROPIC_API_KEY"
    base_url_env = "ANTHROPIC_BASE_URL"

    def map_stream_event(self, raw_line: str) -> CommonEvent | None:
        payload = _stream_payload(raw_line)
        if payload is None:
            return None
        message = payload.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "tool_use":
                    return _tool_stream_event(item.get("name"), item.get("input"))
                if item.get("text"):
                    return _message_stream_event(item["text"], title="Claude Code message")
        if payload.get("type") == "result" and isinstance(payload.get("usage"), dict):
            return _token_stream_event(payload["usage"])
        if payload.get("result"):
            return _message_stream_event(payload["result"], title="Claude Code result")
        return _generic_stream_event(payload)

    def _default_native_verification_template(self) -> list[str]:
        return [
            "claude",
            "-p",
            "--model",
            "{model}",
            "--output-format",
            "stream-json",
            "--verbose",
            "--max-budget-usd",
            "{max_budget_usd}",
            "{prompt}",
        ]

    def _default_native_launch_template(self) -> list[str]:
        return [
            "claude",
            "-p",
            "--model",
            "{model}",
            "--output-format",
            "stream-json",
            "--verbose",
            "--permission-mode",
            "acceptEdits",
            "--allowedTools",
            "Bash,Write,Edit,MultiEdit",
            "--max-budget-usd",
            "{max_budget_usd}",
            "{prompt}",
        ]

    def _timeout_metadata(self, purpose_key: str) -> dict[str, int]:
        metadata = super()._timeout_metadata(purpose_key)
        if metadata or purpose_key != "launch_timeout_seconds":
            return metadata
        return {"timeout_seconds": CLAUDE_CODE_AGENT_LAUNCH_TIMEOUT_SECONDS}


class CodexAdapterBuilder(WorkerAdapterBuilder):
    api_key_env = "OPENAI_API_KEY"
    base_url_env = "OPENAI_BASE_URL"

    def map_stream_event(self, raw_line: str) -> CommonEvent | None:
        payload = _stream_payload(raw_line)
        if payload is None:
            return None
        item = payload.get("item")
        if isinstance(item, dict):
            item_type = str(item.get("type") or "")
            if item_type in {"agent_message", "message"}:
                return _message_stream_event(item.get("text") or item.get("content"), title="Codex message")
            if item_type in {"command_execution", "function_call", "tool_call"}:
                return _tool_stream_event(item.get("name") or item.get("command"), item.get("arguments") or item.get("input"))
        return _generic_stream_event(payload)

    def _default_native_verification_template(self) -> list[str]:
        command = self.config.get("command") or self.adapter["kind"]
        return [str(command), "exec", "--json", "--skip-git-repo-check", "-m", "{model}", "{prompt}"]

    def _default_native_launch_template(self) -> list[str]:
        command = self.config.get("command") or self.adapter["kind"]
        return [
            str(command),
            "exec",
            "--json",
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            "-m",
            "{model}",
            "--cd",
            "{workdir}",
            "{prompt}",
        ]

    def _normalize_template(self, template_key: str, template: list[Any], read_only: bool = False) -> list[Any]:
        command = [str(part) for part in template]
        if template_key in {"native_launch_template", "native_verification_template"} and len(command) == 1:
            # A bare configured binary expands to the safe default Codex exec template.
            command = (
                self._default_native_launch_template()
                if template_key == "native_launch_template"
                else self._default_native_verification_template()
            )
            command[0] = str(template[0])
        if template_key in {"native_launch_template", "native_verification_template"} and len(command) >= 2 and command[1] == "exec":
            command = self._ensure_native_exec_flags(command)
            if template_key == "native_launch_template":
                command = self._ensure_sandbox(command, read_only=read_only)
                command = self._ensure_cd_argument(command)
        return command

    def _ensure_native_exec_flags(self, command: list[str]) -> list[str]:
        rest = [part for part in command[2:] if part not in {"--json", "--skip-git-repo-check"}]
        return [*command[:2], "--json", "--skip-git-repo-check", *rest]

    def _ensure_sandbox(self, command: list[str], read_only: bool = False) -> list[str]:
        bypass_flags = ("--full-auto", "--dangerously-bypass-approvals-and-sandbox")
        if any(part == flag or part.startswith(f"{flag}=") for part in command for flag in bypass_flags):
            if read_only:
                raise ValueError("Configured Codex launch flags bypass the required read-only sandbox.")
            return command
        sandbox_value = "read-only" if read_only else "workspace-write"
        for flag in ("--sandbox", "-s"):
            if flag not in command:
                continue
            index = command.index(flag)
            if index + 1 < len(command) and command[index + 1] != sandbox_value:
                return [*command[: index + 1], sandbox_value, *command[index + 2 :]]
            return command
        for index, part in enumerate(command):
            if part.startswith(("--sandbox=", "-s=")):
                prefix = part.split("=", 1)[0]
                return [*command[:index], f"{prefix}={sandbox_value}", *command[index + 1 :]]
        return [*command[:4], "--sandbox", sandbox_value, *command[4:]]

    def _timeout_metadata(self, purpose_key: str) -> dict[str, int]:
        metadata = super()._timeout_metadata(purpose_key)
        if metadata or purpose_key != "launch_timeout_seconds":
            return metadata
        return {"timeout_seconds": CODEX_AGENT_LAUNCH_TIMEOUT_SECONDS}

    def _ensure_cd_argument(self, command: list[str]) -> list[str]:
        for flag in ("--cd", "-C"):
            if flag not in command:
                continue
            index = command.index(flag)
            if index + 1 < len(command):
                return [*command[: index + 1], "{workdir}", *command[index + 2 :]]
            return [*command, "{workdir}"]
        return [*command[:-1], "--cd", "{workdir}", command[-1]]


class OpenCodeAdapterBuilder(WorkerAdapterBuilder):
    api_key_env = "OPENAI_API_KEY"
    base_url_env = "OPENAI_BASE_URL"

    def map_stream_event(self, raw_line: str) -> CommonEvent | None:
        payload = _stream_payload(raw_line)
        if payload is None:
            return None
        part = payload.get("part")
        part = part if isinstance(part, dict) else payload
        event_type = str(payload.get("type") or part.get("type") or "")
        if event_type in {"text", "message"}:
            return _message_stream_event(part.get("text") or part.get("content"), title="OpenCode message")
        if event_type in {"tool", "tool_use", "tool_call"}:
            return _tool_stream_event(part.get("tool") or part.get("name"), part.get("input") or part.get("arguments"))
        return _generic_stream_event(payload)

    def build_launch_command(
        self,
        *,
        model: str,
        task_prompt: str,
        proxy_url: str,
        session_api_key: str,
        project_root: str | None = None,
        read_only: bool = False,
    ) -> CommandPlan:
        workdir = project_root or self.adapter.get("workdir")
        template = self._normalize_template(
            "launch_template",
            self.config.get("launch_template") or ["opencode", "run", "--model", "{model}", "--format", "json", "{prompt}"],
            read_only=read_only,
        )
        if workdir:
            template = self._ensure_dir_argument([str(part) for part in template], require_workdir=True)
        command = [
            str(part).format(
                model=model,
                prompt=task_prompt,
                proxy_url=proxy_url,
                session_api_key=session_api_key,
                workdir=workdir or "",
            )
            for part in template
        ]
        env = self._env(proxy_url=proxy_url, session_api_key=session_api_key)
        return CommandPlan(
            command=command,
            cwd=Path(workdir) if workdir else None,
            env=env,
            metadata={
                "adapter_id": self.adapter["id"],
                "kind": self.adapter["kind"],
                "model": model,
                "purpose": "task_launch",
                "tracking_mode": "proxy_governed",
                "usage_source": "harness_proxy",
                "read_only": read_only,
                **self._timeout_metadata("launch_timeout_seconds"),
            },
        )

    def _normalize_template(self, template_key: str, template: list[Any], read_only: bool = False) -> list[Any]:
        command = [str(part) for part in template]
        if template_key in {"launch_template", "native_launch_template", "native_verification_template"} and command == ["opencode"]:
            command = ["opencode", "run", "--model", "{model}", "--format", "json", "{prompt}"]
        if template_key in {"native_launch_template", "native_verification_template"}:
            return self._ensure_dir_argument(command)
        return command

    def _default_native_verification_template(self) -> list[str]:
        return self._ensure_dir_argument(super()._default_native_verification_template())

    def _default_native_launch_template(self) -> list[str]:
        return self._ensure_dir_argument(super()._default_native_launch_template())

    def build_native_launch_command(
        self,
        *,
        model: str,
        task_prompt: str,
        project_root: str | None = None,
        read_only: bool = False,
    ) -> CommandPlan:
        workdir = project_root or self.adapter.get("workdir")
        template = self._normalize_template(
            "native_launch_template",
            self.config.get("native_launch_template") or self._default_native_launch_template(),
            read_only=read_only,
        )
        if workdir:
            template = self._ensure_dir_argument([str(part) for part in template], require_workdir=True)
        command = [str(part).format(model=model, prompt=task_prompt, workdir=workdir or "") for part in template]
        return CommandPlan(
            command=command,
            cwd=Path(workdir) if workdir else None,
            env={},
            metadata={
                "adapter_id": self.adapter["id"],
                "kind": self.adapter["kind"],
                "model": model,
                "purpose": "task_launch",
                "project_root": str(workdir) if workdir else None,
                "prompt_argument_indices": _prompt_argument_indices(command, task_prompt),
                "tracking_mode": "native_usage",
                "usage_source": "native_usage",
                "read_only": read_only,
                **self._timeout_metadata("launch_timeout_seconds"),
            },
        )

    def _ensure_dir_argument(self, command: list[str], *, require_workdir: bool = False) -> list[str]:
        if not require_workdir and not self.adapter.get("workdir"):
            return command
        if "--dir" in command:
            if not require_workdir:
                return command
            index = command.index("--dir")
            if index + 1 < len(command):
                return [*command[: index + 1], "{workdir}", *command[index + 2 :]]
            return [*command, "{workdir}"]
        if len(command) >= 2 and command[0] == "opencode" and command[1] == "run":
            return [command[0], command[1], "--dir", "{workdir}", *command[2:]]
        return command

    def _timeout_metadata(self, purpose_key: str) -> dict[str, int]:
        configured = super()._timeout_metadata(purpose_key)
        if configured or purpose_key != "launch_timeout_seconds":
            return configured
        return {"timeout_seconds": OPENCODE_AGENT_LAUNCH_TIMEOUT_SECONDS}


BUILDERS = {
    "claude_code": ClaudeCodeAdapterBuilder,
    "codex": CodexAdapterBuilder,
    "opencode": OpenCodeAdapterBuilder,
}

CURATED_MODEL_DISCOVERY_SOURCES = {
    "claude_code": "foreman_ai_hq_curated_claude_code_models",
    "codex": "foreman_ai_hq_curated_codex_models",
}


def get_adapter_builder(adapter: dict[str, Any]) -> WorkerAdapterBuilder:
    return BUILDERS.get(adapter.get("kind"), WorkerAdapterBuilder)(adapter)


def detect_worker_adapter(adapter: dict[str, Any]) -> dict[str, Any]:
    command_name = _adapter_command_name(adapter)
    executable = shutil.which(command_name) if command_name else None
    if not command_name:
        return {
            "installed": False,
            "callable": False,
            "command": None,
            "executable": None,
            "version": None,
            "failure_reason": "No adapter command is configured.",
        }
    if executable is None:
        return {
            "installed": False,
            "callable": False,
            "command": command_name,
            "executable": None,
            "version": None,
            "failure_reason": f"Command '{command_name}' was not found on PATH.",
        }

    completed = subprocess.run(
        [command_name, "--version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    output = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode != 0:
        return {
            "installed": True,
            "callable": False,
            "command": command_name,
            "executable": executable,
            "version": output or None,
            "failure_reason": f"Command '{command_name} --version' exited with {completed.returncode}.",
        }
    return {
        "installed": True,
        "callable": True,
        "command": command_name,
        "executable": executable,
        "version": output or None,
        "failure_reason": None,
    }


def discover_worker_models(
    database_path: Path | str,
    adapter_id: str,
    *,
    runner: Runner | None = None,
) -> ModelDiscoveryResult:
    adapter = db.get_worker_adapter(database_path, adapter_id)
    curated_source = CURATED_MODEL_DISCOVERY_SOURCES.get(str(adapter.get("kind")))
    if curated_source:
        # Curated providers avoid shelling out for model lists that are unstable or not exposed by CLI.
        return _discover_curated_worker_models(database_path, adapter, source=curated_source)

    plan = _model_discovery_plan(adapter)
    reasons: list[str] = []
    try:
        completed = (runner or subprocess_runner)(plan)
    except Exception as exc:
        completed = subprocess.CompletedProcess(
            plan.command,
            127,
            stdout="",
            stderr=f"Failed to launch command {redact_command_plan(plan)['command'][0]!r}: {type(exc).__name__}",
        )
    stdout = str(_result_field(completed, "stdout", "") or "")
    stderr = str(_result_field(completed, "stderr", "") or "")
    returncode = int(_result_field(completed, "returncode", 0) or 0)
    models = [] if returncode != 0 else _parse_discovered_models(stdout)
    if returncode != 0:
        reasons.append("Model discovery command failed.")
    if not models:
        reasons.append("No Worker Harness models were discovered natively.")
    evidence = {
        "returncode": returncode,
        "stdout": redact_cli_value(stdout.strip()),
        "stderr": redact_cli_value(stderr.strip()),
        "models": models,
        "command_plan": redact_command_plan(plan),
        "tracking_mode": "native",
    }
    config = {**(adapter.get("config") or {}), "model_discovery": evidence}
    db.update_worker_adapter(database_path, adapter_id, config=config)
    return ModelDiscoveryResult(not reasons, adapter_id, models, reasons, evidence)


def _discover_curated_worker_models(
    database_path: Path | str,
    adapter: dict[str, Any],
    *,
    source: str,
) -> ModelDiscoveryResult:
    adapter_id = str(adapter["id"])
    models = selectable_worker_model_ids(adapter)
    config = dict(adapter.get("config") or {})
    approved_models = [model for model in allowed_worker_model_ids(adapter) if model in models]
    evidence = {
        "returncode": 0,
        "stdout": "",
        "stderr": "",
        "models": models,
        "command_plan": None,
        "tracking_mode": "curated",
        "source": source,
    }
    config = {**config, "model_discovery": evidence}
    db.update_worker_adapter(database_path, adapter_id, config=config, supported_models=approved_models)
    return ModelDiscoveryResult(True, adapter_id, models, [], evidence)


def discovered_worker_model_ids(adapter: dict[str, Any]) -> list[str]:
    curated_models = _curated_discovered_model_ids(adapter)
    if curated_models is not None:
        return curated_models

    discovery = (adapter.get("config") or {}).get("model_discovery") or {}
    models = [str(model) for model in discovery.get("models") or []]
    models = [model for model in models if looks_like_model_id(model)]
    if models:
        return models
    return []


def _curated_discovered_model_ids(adapter: dict[str, Any]) -> list[str] | None:
    source = CURATED_MODEL_DISCOVERY_SOURCES.get(str(adapter.get("kind")))
    if not source:
        return None
    seeded_models = selectable_worker_model_ids(adapter)
    # Curated inventories are code-owned, not a durable database cache. If the
    # curated list changes, existing DB rows must immediately expose the new
    # selectable inventory instead of narrowing the UI to stale persisted
    # model_discovery.models evidence from a prior run.
    return seeded_models


def _adapter_command_name(adapter: dict[str, Any]) -> str | None:
    config = adapter.get("config") or {}
    command = config.get("command")
    if command:
        return str(command).split()[0]
    template = config.get("verification_template") or config.get("launch_template") or []
    if template:
        return str(template[0])
    return adapter.get("kind")


def _model_discovery_plan(adapter: dict[str, Any]) -> CommandPlan:
    config = adapter.get("config") or {}
    template = config.get("model_discovery_template") or _default_model_discovery_template(adapter)
    workdir = adapter.get("workdir")
    return CommandPlan(
        command=[str(part) for part in template],
        cwd=Path(workdir) if workdir else None,
        env={},
        metadata={"adapter_id": adapter["id"], "kind": adapter["kind"], "purpose": "native_model_discovery"},
    )


def _default_model_discovery_template(adapter: dict[str, Any]) -> list[str]:
    command = _adapter_command_name(adapter) or str(adapter.get("kind") or "worker")
    return [command, "models"]


def _parse_discovered_models(stdout: str) -> list[str]:
    text = stdout.strip()
    if not text:
        return []
    parsed: Any | None = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    candidates = _models_from_json(parsed) if parsed is not None else []
    if not candidates:
        candidates = [line.strip() for line in text.splitlines() if line.strip() and not line.lower().startswith("model")]
    seen: set[str] = set()
    models: list[str] = []
    for candidate in candidates:
        model = str(candidate).strip()
        if not looks_like_model_id(model) or model in seen:
            continue
        seen.add(model)
        models.append(model)
    return models


def _models_from_json(value: Any) -> list[str]:
    if isinstance(value, list):
        models: list[str] = []
        for item in value:
            if isinstance(item, str):
                models.append(item)
            elif isinstance(item, dict):
                for key in ("id", "model", "name"):
                    if item.get(key):
                        models.append(str(item[key]))
                        break
        return models
    if isinstance(value, dict):
        for key in ("models", "data"):
            if key in value:
                return _models_from_json(value[key])
    return []


def _prompt_argument_indices(command: list[str], prompt: str) -> list[int]:
    if not prompt:
        return []
    return [index for index, part in enumerate(command) if prompt in part]


def redact_command_plan(plan: CommandPlan) -> dict[str, Any]:
    metadata = dict(plan.metadata)
    prompt_indices = {int(index) for index in metadata.pop("prompt_argument_indices", [])}
    if prompt_indices:
        metadata["prompt_redacted"] = True
    return {
        "command": _redact_command(plan.command, prompt_indices=prompt_indices),
        "cwd": str(plan.cwd) if plan.cwd else None,
        "env": {key: ("***REDACTED***" if _is_secret_name(key) else redact_cli_value(value)) for key, value in plan.env.items()},
        "metadata": metadata,
    }


def verify_worker_adapter(
    database_path: Path | str,
    adapter_id: str,
    *,
    model: str,
    proxy_url: str,
    tracking_mode: str = "proxy_governed",
    runner: Runner | None = None,
    token_recorder: Callable[[str], None] | None = None,
) -> VerificationResult:
    adapter = db.get_worker_adapter(database_path, adapter_id)
    session_api_key = f"sk_sess_{secrets.token_urlsafe(24)}"
    session = db.create_session(
        database_path,
        task_description=f"Worker adapter verification: {adapter['name']}",
        model=model,
        session_key_hash=hashlib.sha256(session_api_key.encode("utf-8")).hexdigest(),
        guardrail_overrides={"verification": {"adapter_id": adapter_id, "tracking_mode": tracking_mode}},
        status="running",
    )
    builder = get_adapter_builder(adapter)
    reasons: list[str] = []
    if tracking_mode not in {PROXY_GOVERNED, NATIVE_USAGE, OBSERVED_ONLY}:
        reasons.append("Unsupported adapter verification tracking mode.")
    if not builder.supports_model(model):
        reasons.append("Selected model is not supported by this adapter.")
    if tracking_mode in {NATIVE_USAGE, OBSERVED_ONLY}:
        plan = builder.build_native_verification_command(model=model, prompt=SENTINEL_PROMPT)
    else:
        plan = builder.build_verification_command(
            model=model,
            prompt=SENTINEL_PROMPT,
            proxy_url=proxy_url,
            session_api_key=session_api_key,
        )
    plan = CommandPlan(plan.command, plan.cwd, plan.env, {**plan.metadata, "session_id": session["id"]})
    if reasons:
        evidence = {
            "session_id": session["id"],
            "model": model,
            "tracking_mode": OBSERVED_ONLY,
            "tracking_authoritative": False,
            "preflight_failed": True,
            "reasons": list(reasons),
            "command_plan": redact_command_plan(plan),
        }
        adapter = db.mark_worker_adapter_verification(database_path, adapter_id, verified=False, evidence=evidence)
        db.update_session_status(database_path, session["id"], "failed")
        return VerificationResult(False, adapter_id, session["id"], reasons, adapter["verification_evidence"])

    try:
        completed = (runner or subprocess_runner)(plan)
    except Exception as exc:
        completed = subprocess.CompletedProcess(
            plan.command,
            127,
            stdout="",
            stderr=f"Failed to launch command {redact_command_plan(plan)['command'][0]!r}: {type(exc).__name__}",
        )
    stdout = str(_result_field(completed, "stdout") or "")
    stderr = str(_result_field(completed, "stderr", ""))
    returncode = int(_result_field(completed, "returncode", 0) or 0)
    cli_failure = _native_cli_failure_reason(stdout, stderr) if returncode != 0 else None
    sentinel_matched = native_sentinel_matched(stdout, SENTINEL_RESPONSE) if tracking_mode in {NATIVE_USAGE, OBSERVED_ONLY} else stdout.strip() == SENTINEL_RESPONSE
    if returncode != 0:
        reasons.append("Adapter verification command failed.")
    if cli_failure:
        reasons.append(f"Adapter CLI reported: {cli_failure}")
    if not sentinel_matched:
        reasons.append("Adapter did not return exact verification sentinel.")

    native_usage = parse_native_usage_evidence(stdout, model=model, returncode=returncode) if tracking_mode == NATIVE_USAGE else None
    if tracking_mode == NATIVE_USAGE:
        if native_usage is None:
            reasons.append("No trustworthy native usage evidence was emitted for selected model.")
        else:
            db.record_token_turn(
                database_path,
                session_id=session["id"],
                usage_kind="adapter_verification",
                model=model,
                prompt_tokens=native_usage.prompt_tokens,
                completion_tokens=native_usage.completion_tokens,
                cost=native_usage.cost,
                raw_usage={
                    **native_usage.raw_usage,
                    "total_tokens": native_usage.total_tokens,
                    "usage_source": NATIVE_USAGE,
                    "tracking_mode": NATIVE_USAGE,
                    "worker_harness": adapter.get("kind"),
                },
            )
    elif tracking_mode == PROXY_GOVERNED and token_recorder is not None:
        token_recorder(session["id"])

    token_recorded = db.has_adapter_verification_token(database_path, session_id=session["id"], model=model)
    if tracking_mode != OBSERVED_ONLY and not token_recorded:
        reasons.append("No adapter_verification token row was recorded for selected model.")
    # Without token evidence, a successful sentinel only proves the command ran, not budget tracking.
    resolved_tracking_mode = OBSERVED_ONLY if tracking_mode == OBSERVED_ONLY or not token_recorded else tracking_mode

    evidence = {
        "session_id": session["id"],
        "model": model,
        "tracking_mode": resolved_tracking_mode,
        "tracking_authoritative": resolved_tracking_mode in {PROXY_GOVERNED, NATIVE_USAGE},
        "returncode": returncode,
        "stdout": redact_cli_value(stdout.strip()),
        "stderr": redact_cli_value(stderr),
        "sentinel_matched": sentinel_matched,
        "token_recorded": token_recorded,
        "command_plan": redact_command_plan(plan),
    }
    if reasons:
        diagnostic = native_cli_diagnostic(
            adapter_id=adapter_id,
            adapter_kind=str(adapter.get("kind") or adapter_id),
            stdout=stdout,
            stderr=stderr,
            returncode=returncode,
        )
        if diagnostic:
            evidence["diagnostic"] = diagnostic
    if native_usage is not None:
        evidence["native_usage"] = native_usage.raw_usage
    passed = not reasons
    adapter = db.mark_worker_adapter_verification(database_path, adapter_id, verified=passed, evidence=evidence)
    db.update_session_status(database_path, session["id"], "completed" if passed else "failed")
    return VerificationResult(passed, adapter_id, session["id"], reasons, adapter["verification_evidence"])

def subprocess_runner(plan: CommandPlan) -> subprocess.CompletedProcess[str]:
    timeout_seconds = _timeout_seconds(plan)
    try:
        return subprocess.run(
            plan.command,
            cwd=str(plan.cwd) if plan.cwd else None,
            env={**os.environ, **plan.env},
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stderr = exc.stderr or ""
        timeout_message = f"Command timed out after {timeout_seconds} seconds."
        return subprocess.CompletedProcess(
            plan.command,
            124,
            stdout=exc.output or "",
            stderr=f"{stderr}\n{timeout_message}" if stderr else timeout_message,
        )
    except OSError as exc:
        command_name = redact_cli_value(str(plan.command[0])) if plan.command else "<empty>"
        error_text = getattr(exc, "strerror", None) or str(exc)
        return subprocess.CompletedProcess(
            plan.command,
            127,
            stdout="",
            stderr=f"Failed to launch command {command_name!r}: {type(exc).__name__}: {redact_cli_value(str(error_text))}",
        )


def _timeout_seconds(plan: CommandPlan) -> int:
    candidate = plan.metadata.get("timeout_seconds")
    if candidate is None:
        return SUBPROCESS_RUNNER_TIMEOUT_SECONDS
    try:
        seconds = int(candidate)
    except (TypeError, ValueError):
        return SUBPROCESS_RUNNER_TIMEOUT_SECONDS
    return seconds if seconds > 0 else SUBPROCESS_RUNNER_TIMEOUT_SECONDS


def _result_field(result: Any, field: str, default: Any = "") -> Any:
    if isinstance(result, dict):
        return result.get(field, default)
    return getattr(result, field, default)


def _native_cli_failure_reason(stdout: str, stderr: str) -> str | None:
    for payload in _json_line_payloads(stdout):
        text = _cli_payload_text(payload)
        if text and (payload.get("is_error") or payload.get("type") == "error" or payload.get("error")):
            return redact_cli_value(text)[:500]
    return redact_cli_value(stderr.strip())[:500] if stderr.strip() else None


def _json_line_payloads(text: str) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for line in text.splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _stream_payload(raw_line: str) -> dict[str, Any] | None:
    line = raw_line.strip()
    if line.startswith("data:"):
        line = line[5:].strip()
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _message_stream_event(value: Any, *, title: str) -> CommonEvent | None:
    text = _cli_text(value)
    if not text:
        return None
    return {"kind": "agent_message", "title": title, "detail": {"text": redact_cli_value(text)[:1000]}}


def _tool_stream_event(name: Any, arguments: Any) -> CommonEvent | None:
    if not name:
        return None
    detail = redact_cli_value(json.dumps(arguments or {}, sort_keys=True, default=str))[:1000]
    return {
        "kind": "tool_call",
        "title": f"Tool: {redact_cli_value(str(name))[:200]}",
        "detail": {"arguments": detail},
    }


def _token_stream_event(usage: dict[str, Any]) -> CommonEvent | None:
    values = {
        key: value
        for key, value in usage.items()
        if key in {"input_tokens", "output_tokens", "prompt_tokens", "completion_tokens", "total_tokens"}
        and isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0
    }
    return {"kind": "token", "title": "Provisional usage", "detail": values} if values else None


def _generic_stream_event(payload: dict[str, Any]) -> CommonEvent | None:
    event_type = payload.get("type") or payload.get("event")
    if event_type in {"error", "failed", "status", "started"}:
        return {
            "kind": "status",
            "title": redact_cli_value(str(event_type))[:200],
            "detail": {"status": redact_cli_value(str(payload.get("status") or event_type))[:500]},
        }
    usage = payload.get("usage")
    if isinstance(usage, dict):
        token = _token_stream_event(usage)
        if token is not None:
            return token
    for name_key, arguments_key in (("tool", "input"), ("name", "arguments")):
        if payload.get(name_key) and (payload.get(arguments_key) is not None or payload.get("type") in {"tool", "tool_call", "tool_use"}):
            return _tool_stream_event(payload[name_key], payload.get(arguments_key))
    for key in ("text", "result", "message", "content"):
        event = _message_stream_event(payload.get(key), title="Worker message")
        if event is not None:
            return event
    if event_type:
        return {
            "kind": "status",
            "title": redact_cli_value(str(event_type))[:200],
            "detail": {"status": redact_cli_value(str(payload.get("status") or event_type))[:500]},
        }
    return None


def _cli_payload_text(payload: dict[str, Any]) -> str | None:
    for value in (payload.get("result"), payload.get("message"), payload.get("error")):
        text = _cli_text(value)
        if text:
            return text
    return None


def _cli_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{"):
            try:
                nested = json.loads(stripped)
            except json.JSONDecodeError:
                return stripped
            return _cli_text(nested) or stripped
        return stripped or None
    if isinstance(value, dict):
        error = value.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        content = value.get("content")
        if isinstance(content, list):
            texts = [str(item.get("text")) for item in content if isinstance(item, dict) and item.get("text")]
            if texts:
                return " ".join(texts)
        for key in ("message", "result", "text"):
            if value.get(key):
                return _cli_text(value[key])
    return None


def _is_secret_name(name: str) -> bool:
    return any(term in name.upper() for term in SECRET_ENV_TERMS)


def _redact_command(command: list[str], *, prompt_indices: set[int] | None = None) -> list[str]:
    redacted: list[str] = []
    redact_next = False
    previous_was_header_flag = False
    prompt_indices = prompt_indices or set()
    for index, part in enumerate(command):
        if index in prompt_indices:
            redacted.append(f"***PROMPT_REDACTED:{len(part)} chars***")
            redact_next = False
            previous_was_header_flag = False
            continue

        if redact_next:
            redacted.append("***REDACTED***")
            redact_next = False
            previous_was_header_flag = False
            continue

        if previous_was_header_flag and part.lower().startswith("authorization:"):
            redacted.append("***REDACTED***")
            previous_was_header_flag = False
            continue
        previous_was_header_flag = False

        flag, separator, _value = part.partition("=")
        lowered_flag = flag.lower()
        if separator and lowered_flag in SECRET_COMMAND_FLAGS:
            redacted.append(f"{flag}=***REDACTED***")
            continue
        if lowered_flag in SECRET_COMMAND_FLAGS:
            redacted.append(redact_cli_value(part))
            redact_next = True
            continue
        if part == "-H":
            redacted.append(part)
            previous_was_header_flag = True
            continue
        redacted.append(redact_cli_value(part))
    return redacted
