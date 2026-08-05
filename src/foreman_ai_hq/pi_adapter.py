from __future__ import annotations

import asyncio
import contextlib
import json
import os
import queue
import shutil
import signal
import sqlite3
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterator

from foreman_ai_hq import db
from foreman_ai_hq.model_identity import MODEL_ID_PATTERN, looks_like_model_id
from foreman_ai_hq.native_cli_diagnostics import redact_cli_value
from foreman_ai_hq.native_usage import (
    NativeUsageEvidence,
    extract_pi_assistant_text,
    extract_pi_successful_tool_calls,
    native_sentinel_matched,
    parse_pi_usage_stream,
)
# The orchestrator proves itself against the same sentinel a Worker Adapter does,
# so the two verification bars stay literally the same string.
from foreman_ai_hq.worker_adapters import SENTINEL_PROMPT, SENTINEL_RESPONSE

PI_ACP_PI_COMMAND_ENV = "PI_ACP_PI_COMMAND"
PI_ACP_PERSONA_PATH_ENV = "PI_ACP_PERSONA_PATH"
PI_ACP_ALLOWED_TOOLS_ENV = "PI_ACP_ALLOWED_TOOLS"
PI_ACP_PROVIDER_ENV = "PI_ACP_PROVIDER"
PI_ACP_MODEL_ENV = "PI_ACP_MODEL"
PI_ACP_SESSION_DIR_ENV = "PI_ACP_SESSION_DIR"

PI_ORCHESTRATOR_ALLOWED_TOOLS = ("read", "grep", "find", "ls")
PI_STRUCTURED_JOB_ALLOWED_READ_TOOLS = ("read_curated_input",)
DEFAULT_PROFILE_DIR = Path(__file__).resolve().parent / "orchestrator" / "pi" / "profile"
DEFAULT_EXTENSIONS_DIR = Path(__file__).resolve().parent / "orchestrator" / "pi" / "extensions"
DEFAULT_BRIDGE_DIR = Path(__file__).resolve().parent / "orchestrator" / "pi" / "bridge"
PI_ACP_PACKAGE = "pi-acp"

PI_LIST_MODELS_COMMAND = ("pi", "--list-models")
PI_LIST_MODELS_TIMEOUT_SECONDS = 30
# A verification turn is a real model call, so it gets the launch budget a governed
# turn gets rather than the short budget a local inventory listing needs.
ORCHESTRATOR_VERIFICATION_TIMEOUT_SECONDS = 120
# Legacy internal naming, deliberately not renamed: this is the `execution_backend_status`
# row id for the Orchestrator Model, invisible to operators and referenced across src/.
ORCHESTRATOR_STATUS_RECORD_ID = "control_plane_model"
ORCHESTRATOR_STATUS_RECORD_NAME = "Orchestrator Model"

DISCOVERY_READY = "ready"
DISCOVERY_NEEDS_AUTHENTICATION = "needs_authentication"
DISCOVERY_FAILED = "failed"


class PiAuthRequired(RuntimeError):
    """Raised when pi cannot run because the operator has not authenticated with the provider."""

    def __init__(self, message: str, *, session_id: str | None = None) -> None:
        super().__init__(message)
        self.session_id = session_id


class AcpRuntimeError(RuntimeError):
    """Raised when the ACP stdio conversation with pi fails."""


class PiStructuredJobError(RuntimeError):
    """Raised when a structured pi job cannot run successfully."""

    def __init__(self, message: str, *, session_id: str | None = None) -> None:
        super().__init__(message)
        self.session_id = session_id


class PiStructuredOutputError(PiStructuredJobError):
    """Raised when a structured pi job does not submit exactly one valid result."""


def _persona_path(profile_dir: Path, filename: str = "orchestrator.md") -> Path:
    """Return a tracked persona path under the pi profile."""
    return profile_dir / filename


def _default_pi_agent_dir() -> Path:
    return Path.home() / ".pi" / "agent"


def is_provider_qualified_model(model: str | None) -> bool:
    """True only for an exact ``provider/model`` pi id.

    pi's ``--model`` accepts glob and fuzzy patterns as well as ids, so a looser
    value would make the configured model and the model that actually ran two
    different things, knowable only after the turn.  The model column carries the
    id shape, which is also what rejects a table header or sign-in guidance line.
    """
    if not model:
        return False
    provider, separator, model_id = model.partition("/")
    if not separator or not provider or not model_id:
        return False
    return bool(MODEL_ID_PATTERN.fullmatch(provider)) and looks_like_model_id(model_id)


def recorded_model_from_usage(
    raw_usage: dict[str, Any] | None,
    configured_model: str | None = None,
) -> str | None:
    """Return the provider-qualified model string to record for a pi turn.

    pi messages may report only the model id without a provider, or the
    configured fallback may be the only full ``provider/model`` string available.
    The caller's configured model is the authority for the full id, so a bare id
    is never auto-qualified by guessing a provider.
    """
    usage = raw_usage or {}
    model = usage.get("model")
    if is_provider_qualified_model(model):
        return str(model)
    provider = usage.get("provider")
    if provider and model:
        candidate = f"{provider}/{model}"
        if is_provider_qualified_model(candidate):
            return candidate
    if is_provider_qualified_model(configured_model):
        return str(configured_model)
    return configured_model


def _resolve_pi_provider_model(model: str) -> tuple[str | None, str]:
    """Split a provider-qualified pi id into (provider, model_id).

    An unqualified value reaching here is a bug: guessing a provider is what let
    a bare id resolve to a working launch against the wrong provider entirely.
    Qualification is enforced at validation time, before launch.
    """
    provider, _, model_id = model.partition("/")
    return (provider, model_id) if model_id else (None, provider)


def _pi_acp_command(bridge_dir: Path) -> list[str]:
    """Return the Node command for the pi ACP bridge, preferring the local install."""
    package_json = bridge_dir / "package.json"
    version = "0.0.31"
    if package_json.is_file():
        try:
            version = json.loads(package_json.read_text(encoding="utf-8")).get(
                "dependencies", {}
            ).get(PI_ACP_PACKAGE, version)
        except (json.JSONDecodeError, OSError):
            pass
    local_main = bridge_dir / "node_modules" / PI_ACP_PACKAGE / "dist" / "index.js"
    if local_main.is_file():
        return ["node", str(local_main)]
    return ["npx", "-y", f"{PI_ACP_PACKAGE}@{version}"]


def _prepare_pi_env(
    sessions_dir: Path,
    *,
    agent_dir: Path | None = None,
) -> dict[str, str]:
    """Build the environment for a pi launch.

    pi reads the operator's real auth from ``PI_CODING_AGENT_DIR`` and writes
    transient session files to ``PI_CODING_AGENT_SESSION_DIR``.  No provider
    credentials are written to the repo or a retained tmp dir.
    """
    selected_agent_dir = agent_dir or _default_pi_agent_dir()
    selected_agent_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return {
        **os.environ,
        "PI_CODING_AGENT_DIR": str(selected_agent_dir),
        "PI_CODING_AGENT_SESSION_DIR": str(sessions_dir),
    }


@dataclass(frozen=True)
class OrchestratorModelDiscoveryResult:
    """Outcome of one ``pi --list-models`` inventory refresh.

    ``state`` keeps an empty-but-successful run distinct from a failed one: pi's
    inventory is auth-filtered, so no models means "sign in to a provider", which
    needs the opposite operator action from "discovery broke".
    """

    state: str
    models: list[str]
    reasons: list[str]
    evidence: dict[str, Any]

    @property
    def passed(self) -> bool:
        return self.state == DISCOVERY_READY

    @property
    def needs_authentication(self) -> bool:
        return self.state == DISCOVERY_NEEDS_AUTHENTICATION


PiCommandRunner = Callable[[list[str], dict[str, str]], "subprocess.CompletedProcess[str]"]


def _run_pi_command(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        timeout=PI_LIST_MODELS_TIMEOUT_SECONDS,
        check=False,
    )


def _parse_pi_model_inventory(stdout: str) -> list[str]:
    """Join the provider and model columns of ``pi --list-models`` into pi ids.

    The output is a fixed-width table behind a ``provider model context ...``
    header.  Guarding the *model* column is what rejects both non-model lines:
    the header's column reads ``model`` and the empty-auth line reads
    ``No models available. Use /login ...``.
    """
    models: list[str] = []
    seen: set[str] = set()
    for line in stdout.splitlines():
        columns = line.split()
        if len(columns) < 2:
            continue
        model = f"{columns[0]}/{columns[1]}"
        if not is_provider_qualified_model(model) or model in seen:
            continue
        seen.add(model)
        models.append(model)
    return models


def discover_orchestrator_models(
    database_path: Path | str,
    *,
    agent_dir: Path | str | None = None,
    runner: PiCommandRunner | None = None,
) -> OrchestratorModelDiscoveryResult:
    """Refresh the Orchestrator Model inventory from pi and persist the evidence.

    Evidence is persisted rather than re-derived on demand because readiness must
    be answerable from the database alone; shelling out to pi on every check would
    make a Recorded Demo Run impossible without real provider auth.
    """
    command = list(PI_LIST_MODELS_COMMAND)
    with tempfile.TemporaryDirectory(prefix="pi-list-models-") as tmpdir:
        env = _prepare_pi_env(
            Path(tmpdir) / "sessions",
            agent_dir=Path(agent_dir) if agent_dir else None,
        )
        try:
            completed = (runner or _run_pi_command)(command, env)
        except Exception as exc:
            # A missing or unlaunchable pi is a discovery failure, not an empty inventory.
            completed = subprocess.CompletedProcess(
                command,
                127,
                stdout="",
                stderr=f"Failed to launch command {command[0]!r}: {type(exc).__name__}",
            )

    returncode = int(completed.returncode or 0)
    stdout = str(completed.stdout or "")
    stderr = str(completed.stderr or "")
    models = _parse_pi_model_inventory(stdout) if returncode == 0 else []
    if returncode != 0:
        state = DISCOVERY_FAILED
        reasons = [f"`{' '.join(command)}` exited with {returncode}."]
    elif not models:
        state = DISCOVERY_NEEDS_AUTHENTICATION
        reasons = ["pi reported no models. Run `pi /login` to authenticate a provider."]
    else:
        state = DISCOVERY_READY
        reasons = []

    evidence = {
        "state": state,
        "models": models,
        "discovered_at": datetime.now(UTC).isoformat(),
        "returncode": returncode,
        "stdout": redact_cli_value(stdout.strip()),
        "stderr": redact_cli_value(stderr.strip()),
        "command": command,
        "reasons": reasons,
    }
    _persist_orchestrator_discovery(database_path, evidence)
    return OrchestratorModelDiscoveryResult(
        state=state, models=models, reasons=reasons, evidence=evidence
    )


def _persist_orchestrator_discovery(
    database_path: Path | str, evidence: dict[str, Any]
) -> dict[str, Any]:
    """Merge inventory evidence into the orchestrator status row's details blob."""
    try:
        existing = db.get_execution_backend_status(database_path, ORCHESTRATOR_STATUS_RECORD_ID)
        details = dict(existing.get("details") or {})
        # Discovery is not verification: listing the inventory must neither claim
        # nor revoke the online state that a verification turn establishes.
        online = bool(existing.get("online"))
    except KeyError:
        details, online = {}, False
    details["model_discovery"] = evidence
    return db.upsert_execution_backend_status(
        database_path,
        ORCHESTRATOR_STATUS_RECORD_ID,
        name=ORCHESTRATOR_STATUS_RECORD_NAME,
        online=online,
        details=details,
    )


def persisted_orchestrator_discovery(database_path: Path | str) -> dict[str, Any]:
    """Return the persisted inventory evidence, or an empty blob when there is none.

    An un-migrated database has no evidence rather than a broken read, so callers
    that run before `init_db` — `htb check` against a fresh root — see *not
    configured* instead of a sqlite error.
    """
    try:
        status = db.get_execution_backend_status(database_path, ORCHESTRATOR_STATUS_RECORD_ID)
    except (KeyError, sqlite3.OperationalError):
        return {}
    discovery = (status.get("details") or {}).get("model_discovery")
    return dict(discovery) if isinstance(discovery, dict) else {}


def discovered_orchestrator_models(database_path: Path | str) -> list[str]:
    """Return the provider-qualified ids pi last reported."""
    models = persisted_orchestrator_discovery(database_path).get("models") or []
    return [str(model) for model in models if is_provider_qualified_model(str(model))]


def resolve_orchestrator_model(database_path: Path | str, model: str | None) -> str | None:
    """Return the configured model only when pi's inventory still offers it.

    An absent, unqualified, or pattern-shaped value is *not configured*.  It is
    deliberately not repaired by inferring a provider: that would make the harness
    a second authority over pi's own inventory.
    """
    if not is_provider_qualified_model(model):
        return None
    return model if model in discovered_orchestrator_models(database_path) else None


@dataclass(frozen=True)
class OrchestratorVerificationResult:
    """Outcome of one sentinel turn proving the configured Orchestrator Model runs."""

    passed: bool
    model: str
    session_id: str | None
    reasons: list[str]
    evidence: dict[str, Any]


def _persist_orchestrator_verification(
    database_path: Path | str, evidence: dict[str, Any], *, passed: bool
) -> dict[str, Any]:
    """Merge verification evidence into the orchestrator status row.

    Unlike discovery, verification owns the ``online`` flag: it is the only check
    that proves a turn ran and was metered.
    """
    try:
        existing = db.get_execution_backend_status(database_path, ORCHESTRATOR_STATUS_RECORD_ID)
        details = dict(existing.get("details") or {})
    except KeyError:
        details = {}
    details["verification"] = evidence
    return db.upsert_execution_backend_status(
        database_path,
        ORCHESTRATOR_STATUS_RECORD_ID,
        name=ORCHESTRATOR_STATUS_RECORD_NAME,
        online=passed,
        details=details,
    )


def persisted_orchestrator_verification(database_path: Path | str) -> dict[str, Any]:
    """Return the persisted verification evidence, or an empty blob when there is none."""
    try:
        status = db.get_execution_backend_status(database_path, ORCHESTRATOR_STATUS_RECORD_ID)
    except (KeyError, sqlite3.OperationalError):
        return {}
    verification = (status.get("details") or {}).get("verification")
    return dict(verification) if isinstance(verification, dict) else {}


def orchestrator_verification_is_stale(evidence: dict[str, Any], model: str | None) -> bool:
    """True when evidence exists but proves a different model than the configured one.

    Derived by comparison rather than written as a flag on save, so a stale marker
    cannot drift out of step with the value it describes.
    """
    if not evidence:
        return False
    return str(evidence.get("model") or "") != str(model or "")


def verify_orchestrator_model(
    database_path: Path | str,
    model: str | None,
    *,
    agent_dir: Path | str | None = None,
    timeout: float = ORCHESTRATOR_VERIFICATION_TIMEOUT_SECONDS,
    launcher: Callable[..., tuple[dict[str, Any], "PiOnceResult"]] | None = None,
) -> OrchestratorVerificationResult:
    """Run one sentinel turn through the governed launch path and prove it was metered.

    A matched sentinel alone only proves the command ran; without a recorded token
    turn there is no evidence spend is accounted, which is the bar Worker Adapter
    verification already clears.
    """
    reasons: list[str] = []
    if not is_provider_qualified_model(model):
        # No turn is started for a value the launcher would have to guess at.
        evidence = {
            "model": model,
            "passed": False,
            "verified_at": datetime.now(UTC).isoformat(),
            "reasons": ["Orchestrator Model is not a provider-qualified id from pi's inventory."],
        }
        _persist_orchestrator_verification(database_path, evidence, passed=False)
        return OrchestratorVerificationResult(
            passed=False, model=str(model or ""), session_id=None, reasons=list(evidence["reasons"]), evidence=evidence
        )

    selected_model = str(model)
    _, model_id = _resolve_pi_provider_model(selected_model)
    try:
        session, result = (launcher or launch_pi_once)(
            database_path,
            SENTINEL_PROMPT,
            model=selected_model,
            agent_dir=agent_dir,
            timeout=timeout,
            usage_kind="adapter_verification",
        )
    except PiAuthRequired as exc:
        evidence = {
            "model": selected_model,
            "passed": False,
            "verified_at": datetime.now(UTC).isoformat(),
            "reasons": [str(exc)],
            "needs_authentication": True,
        }
        _persist_orchestrator_verification(database_path, evidence, passed=False)
        return OrchestratorVerificationResult(
            passed=False, model=selected_model, session_id=None, reasons=list(evidence["reasons"]), evidence=evidence
        )
    except Exception as exc:
        evidence = {
            "model": selected_model,
            "passed": False,
            "verified_at": datetime.now(UTC).isoformat(),
            "reasons": [f"Verification turn failed to launch: {type(exc).__name__}"],
        }
        _persist_orchestrator_verification(database_path, evidence, passed=False)
        return OrchestratorVerificationResult(
            passed=False, model=selected_model, session_id=None, reasons=list(evidence["reasons"]), evidence=evidence
        )

    sentinel_matched = native_sentinel_matched(result.stdout, SENTINEL_RESPONSE)
    token_recorded = db.has_adapter_verification_token(
        database_path, session_id=session["id"], model=selected_model
    )
    if result.returncode != 0:
        reasons.append("Orchestrator verification turn exited non-zero.")
    if not sentinel_matched:
        reasons.append("Orchestrator did not return the exact verification sentinel.")
    if not token_recorded:
        reasons.append("No adapter_verification token turn was recorded for the Orchestrator Model.")

    passed = sentinel_matched and token_recorded
    evidence = {
        "model": selected_model,
        "passed": passed,
        "verified_at": datetime.now(UTC).isoformat(),
        "session_id": session["id"],
        "sentinel_matched": sentinel_matched,
        "token_recorded": token_recorded,
        "returncode": result.returncode,
        "stdout": redact_cli_value(result.stdout.strip()),
        "stderr": redact_cli_value(result.stderr.strip()),
        "reasons": reasons,
    }
    _persist_orchestrator_verification(database_path, evidence, passed=passed)
    return OrchestratorVerificationResult(
        passed=passed, model=selected_model, session_id=session["id"], reasons=reasons, evidence=evidence
    )


def _write_pi_acp_wrapper(
    tmpdir: Path,
    persona_path: Path,
    sessions_dir: Path,
    provider: str | None,
    model: str,
) -> Path:
    """Write a generated POSIX wrapper that execs pi with provider/model/persona/tools.

    The wrapper is content-free of policy text and secrets; it reads the persona
    path, allowlist, provider, model, and session dir from environment variables
    set by the adapter.
    """
    wrapper = tmpdir / "pi-wrapper.sh"
    provider_block = (
        'if [ -n "$PI_ACP_PROVIDER" ]; then\n  set -- --provider "$PI_ACP_PROVIDER" "$@"\nfi\n'
        if provider
        else ""
    )
    wrapper.write_text(
        "#!/bin/sh\n"
        f'{provider_block}'
        'exec pi --model "$PI_ACP_MODEL" --append-system-prompt "$PI_ACP_PERSONA_PATH" '
        '--tools "$PI_ACP_ALLOWED_TOOLS" --session-dir "$PI_ACP_SESSION_DIR" --no-approve "$@"\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    return wrapper


# Markers pi actually emits when the configured provider has no usable credentials.
# Deliberately narrow: an unrecognized failure must surface as itself, not as a
# misleading sign-in prompt.
PI_AUTH_ERROR_MARKERS = (
    "authentication required",  # ACP session/new with no provider auth configured
    "no api key found",  # `pi -p` against a provider with no key
    "use /login",  # pi's own sign-in guidance
    "invalid api key",
    "unauthorized",
)


def _is_auth_error(message: str) -> bool:
    lowered = message.lower()
    return any(marker in lowered for marker in PI_AUTH_ERROR_MARKERS)


def _raise_for_auth_error(exc: AcpRuntimeError) -> None:
    message = str(exc)
    if _is_auth_error(message):
        raise PiAuthRequired(
            "Provider authentication required; run `pi /login` or add an API key in pi."
        ) from exc


@dataclass
class PiOnceResult:
    """Result of a one-shot pi launch."""

    stdout: str
    stderr: str
    returncode: int
    args: list[str]


@dataclass(frozen=True)
class PiStructuredJobResult:
    """Validated submit arguments plus native-usage session evidence."""

    arguments: dict[str, Any]
    validated: Any
    session: dict[str, Any]
    args: list[str]


def launch_pi_once(
    database_path: Path | str,
    prompt: str,
    *,
    profile_dir: Path | str | None = None,
    model: str,
    agent_dir: Path | str | None = None,
    timeout: float = 60,
    usage_kind: str = "planning",
) -> tuple[dict[str, Any], PiOnceResult]:
    """Mint a planning session and run pi once on its native provider.

    The planning session is anchored in the ledger, but no planning bearer is
    minted or injected: pi authenticates with the operator's existing provider
    credentials.  Usage evidence from pi's ``--mode json`` output is parsed and
    recorded as a ``planning`` token turn.
    """
    provider, model_id = _resolve_pi_provider_model(model)
    session, _bearer_key = db.create_planning_session(
        database_path,
        task_description="pi orchestrator launch",
        model=model,
        tracking_mode="native_usage",
    )
    selected_profile_dir = Path(profile_dir) if profile_dir else DEFAULT_PROFILE_DIR
    selected_agent_dir = Path(agent_dir) if agent_dir else None
    persona_path = _persona_path(selected_profile_dir)

    with tempfile.TemporaryDirectory(prefix="pi-orchestrator-") as tmpdir:
        sessions_dir = Path(tmpdir) / "sessions"
        env = _prepare_pi_env(sessions_dir, agent_dir=selected_agent_dir)
        command: list[str] = ["pi", "-p", "--mode", "json", "--no-session"]
        if provider:
            command.extend(["--provider", provider])
        command.extend(["--model", model_id])
        command.extend(["--append-system-prompt", str(persona_path)])
        command.extend(["--tools", ",".join(PI_ORCHESTRATOR_ALLOWED_TOOLS)])
        command.extend(["--no-approve", prompt])

        result = subprocess.run(
            command,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    if result.returncode != 0 and _is_auth_error(result.stderr):
        raise PiAuthRequired(
            "Provider authentication required; run `pi /login` or add an API key in pi."
        )

    evidence = parse_pi_usage_stream(result.stdout, model=model)
    if evidence is not None:
        db.record_token_turn(
            database_path,
            session_id=session["id"],
            usage_kind=usage_kind,
            model=recorded_model_from_usage(evidence.raw_usage, configured_model=model),
            prompt_tokens=evidence.prompt_tokens,
            completion_tokens=evidence.completion_tokens,
            cost=evidence.cost,
            raw_usage=evidence.raw_usage,
        )

    stdout_text = extract_pi_assistant_text(result.stdout)
    if not stdout_text.strip():
        stdout_text = result.stdout.strip()

    return session, PiOnceResult(
        stdout=stdout_text,
        stderr=result.stderr,
        returncode=result.returncode,
        args=command,
    )


async def run_pi_structured_job(
    database_path: Path | str,
    *,
    instructions: str,
    input_payload: dict[str, Any],
    model: str,
    persona_filename: str,
    extension_filename: str,
    submit_tool: str,
    usage_kind: str,
    task_description: str,
    timeout: float = 120,
    profile_dir: Path | str | None = None,
    extensions_dir: Path | str | None = None,
    agent_dir: Path | str | None = None,
    session_id: str | None = None,
    result_validator: Callable[[dict[str, Any]], Any] | None = None,
) -> PiStructuredJobResult:
    """Run one bounded pi agent turn and accept only its successful submit tool call."""
    provider, model_id = _resolve_pi_provider_model(model)
    if session_id:
        session = db.get_session(database_path, session_id)
    else:
        session, _ = db.create_planning_session(
            database_path,
            task_description=task_description,
            model=model,
            tracking_mode="native_usage",
        )

    selected_profile_dir = Path(profile_dir) if profile_dir else DEFAULT_PROFILE_DIR
    selected_extensions_dir = Path(extensions_dir) if extensions_dir else DEFAULT_EXTENSIONS_DIR
    selected_agent_dir = Path(agent_dir) if agent_dir else None
    persona_path = _persona_path(selected_profile_dir, persona_filename)
    extension_path = selected_extensions_dir / extension_filename
    allowed_tools = (*PI_STRUCTURED_JOB_ALLOWED_READ_TOOLS, submit_tool)

    with tempfile.TemporaryDirectory(prefix=f"pi-{usage_kind}-") as tmpdir:
        root = Path(tmpdir)
        workdir = root / "input"
        sessions_dir = root / "sessions"
        workdir.mkdir()
        (workdir / "job-input.json").write_text(
            json.dumps(
                {"instructions": instructions, "input": input_payload},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        env = _prepare_pi_env(sessions_dir, agent_dir=selected_agent_dir)
        command: list[str] = [
            "pi",
            "-p",
            "--mode",
            "json",
            "--no-session",
            "--no-extensions",
            "--extension",
            str(extension_path),
            "--no-skills",
            "--no-prompt-templates",
            "--no-themes",
            "--no-context-files",
            "--no-approve",
        ]
        if provider:
            command.extend(["--provider", provider])
        command.extend(["--model", model_id])
        command.extend(["--append-system-prompt", str(persona_path)])
        command.extend(["--tools", ",".join(allowed_tools)])
        command.append(
            f"Call read_curated_input once. Use only that curated input. Call {submit_tool} exactly once as your final action."
        )

        proc = None
        communication = None
        timed_out = False
        started_at = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(workdir),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
            communication = asyncio.create_task(proc.communicate())
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    asyncio.shield(communication), timeout=timeout
                )
            except TimeoutError:
                # Keep communicate alive so already-emitted native usage remains accountable.
                timed_out = True
                _kill_async_process(proc)
                await proc.wait()
                stdout_bytes, stderr_bytes = await communication
        except BaseException as exc:
            if proc is not None and proc.returncode is None:
                _kill_async_process(proc)
                await proc.wait()
            if communication is not None and not communication.done():
                communication.cancel()
            db.update_session_status(database_path, session["id"], "failed")
            if isinstance(exc, asyncio.CancelledError):
                raise
            raise PiStructuredJobError(
                f"pi {usage_kind} job could not run: {exc}", session_id=session["id"]
            ) from exc

    elapsed = time.monotonic() - started_at
    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")
    evidence = parse_pi_usage_stream(stdout, model=model)
    if evidence is not None:
        db.record_token_turn(
            database_path,
            session_id=session["id"],
            usage_kind=usage_kind,
            model=recorded_model_from_usage(evidence.raw_usage, configured_model=model),
            prompt_tokens=evidence.prompt_tokens,
            completion_tokens=evidence.completion_tokens,
            cost=evidence.cost,
            raw_usage=evidence.raw_usage,
        )

    if timed_out:
        db.update_session_status(database_path, session["id"], "failed")
        # A hung run is only diagnosable after the fact if the error carries how long
        # it ran and what pi last said; a bare "timed out" leaves nothing to act on.
        raise PiStructuredJobError(
            f"pi {usage_kind} job timed out after {elapsed:.1f}s (limit {timeout:.0f}s); "
            f"pi stderr tail: {_stderr_tail(stderr)}",
            session_id=session["id"],
        )
    if proc.returncode != 0:
        db.update_session_status(database_path, session["id"], "failed")
        if _is_auth_error(stderr):
            raise PiAuthRequired(
                "Provider authentication required; run `pi /login` or add an API key in pi.",
                session_id=session["id"],
            )
        raise PiStructuredJobError(
            f"pi {usage_kind} job failed with exit code {proc.returncode} after {elapsed:.1f}s; "
            f"pi stderr tail: {_stderr_tail(stderr)}",
            session_id=session["id"],
        )
    if evidence is None:
        db.update_session_status(database_path, session["id"], "failed")
        raise PiStructuredJobError(
            f"pi {usage_kind} job emitted no native usage evidence", session_id=session["id"]
        )

    try:
        submissions = extract_pi_successful_tool_calls(stdout, tool_name=submit_tool)
    except ValueError as exc:
        db.update_session_status(database_path, session["id"], "failed")
        raise PiStructuredOutputError(str(exc), session_id=session["id"]) from exc
    if len(submissions) != 1:
        db.update_session_status(database_path, session["id"], "failed")
        raise PiStructuredOutputError(
            f"pi {usage_kind} job must call {submit_tool} exactly once; got {len(submissions)}",
            session_id=session["id"],
        )
    try:
        validated = result_validator(submissions[0]) if result_validator else submissions[0]
    except Exception as exc:
        db.update_session_status(database_path, session["id"], "failed")
        raise PiStructuredOutputError(str(exc), session_id=session["id"]) from exc

    session = db.update_session_status(database_path, session["id"], "completed")
    return PiStructuredJobResult(
        arguments=submissions[0], validated=validated, session=session, args=command
    )


def _stderr_tail(stderr: str, limit: int = 300) -> str:
    """Return a bounded single-line tail of pi's stderr for failure diagnostics."""
    collapsed = " ".join(stderr.split())
    if not collapsed:
        return "<empty>"
    return collapsed[-limit:]


def _kill_async_process(proc: asyncio.subprocess.Process) -> None:
    """Terminate a pi process group without leaving provider/tool children behind."""
    try:
        if hasattr(os, "killpg"):
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except ProcessLookupError:
        pass


class _AcpJsonRpcTransport:
    """Minimal JSON-RPC 2.0 client over a subprocess stdio pipe.

    pi-acp speaks newline-delimited JSON-RPC over stdin/stdout.  This transport
    sends requests, correlates responses by id, and queues non-response messages
    (notifications such as ``session/update``) for the caller to drain.
    """

    def __init__(self, proc: subprocess.Popen) -> None:
        self.proc = proc
        self._next_id = 1
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._write_lock = threading.Lock()

    def _read_loop(self) -> None:
        stdout = self.proc.stdout
        if stdout is None:
            return
        for line in stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            self._queue.put(msg)

    def _send_frame(self, payload: dict[str, Any]) -> None:
        if self.proc.stdin is None:
            raise AcpRuntimeError("ACP bridge stdin is closed")
        with self._write_lock:
            self.proc.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
            self.proc.stdin.flush()

    def _write(self, method: str, params: dict[str, Any]) -> int:
        req_id = self._next_id
        self._next_id += 1
        payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        self._send_frame(payload)
        return req_id

    def notify(self, method: str, params: dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no id, no response)."""
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        self._send_frame(payload)

    def call(
        self, method: str, params: dict[str, Any], *, timeout: float = 30
    ) -> tuple[Any, list[dict[str, Any]]]:
        """Send a JSON-RPC request and return (result, notifications captured before the response)."""
        req_id = self._write(method, params)
        notifications: list[dict[str, Any]] = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                msg = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if msg.get("id") == req_id:
                if "error" in msg:
                    raise AcpRuntimeError(f"ACP {method} failed: {msg['error']}")
                return msg.get("result"), notifications
            notifications.append(msg)
        raise AcpRuntimeError(f"ACP {method} timed out")

    def drain(self, *, timeout: float = 0.5) -> list[dict[str, Any]]:
        """Drain remaining notifications, waiting up to ``timeout`` for the queue to empty."""
        items: list[dict[str, Any]] = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                items.append(self._queue.get(timeout=0.1))
            except queue.Empty:
                break
        return items


def _extract_text_chunks(notifications: list[dict[str, Any]]) -> str:
    """Concatenate ``agent_message_chunk`` text notifications."""
    chunks: list[str] = []
    for msg in notifications:
        update = msg.get("params", {}).get("update", {})
        if update.get("sessionUpdate") == "agent_message_chunk":
            content = update.get("content", {})
            if content.get("type") == "text" and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "".join(chunks)


class PiConversation:
    """Handle for an active ACP pi conversation."""

    def __init__(
        self,
        session: dict[str, Any],
        proc: subprocess.Popen,
        transport: _AcpJsonRpcTransport,
        session_id: str,
        default_timeout: float,
        workdir: Path | None,
        database_path: Path | str,
        model: str,
        sessions_dir: Path,
    ) -> None:
        self.session = session
        self.proc = proc
        self.responses: list[str] = []
        self._transport = transport
        self._session_id = session_id
        self._default_timeout = default_timeout
        self._workdir = workdir
        self._database_path = database_path
        self._model = model
        self._sessions_dir = sessions_dir
        self._session_file_path: Path | None = None
        self._seen_response_ids: set[str] = set()

    def prompt(self, text: str, *, timeout: float | None = None) -> tuple[str, str]:
        """Drive one turn and return (text, stop_reason)."""
        deadline = timeout if timeout is not None else self._default_timeout
        try:
            result, notifications = self._transport.call(
                "session/prompt",
                {"sessionId": self._session_id, "prompt": [{"type": "text", "text": text}]},
                timeout=deadline,
            )
        except AcpRuntimeError as exc:
            # Provider auth can expire mid-conversation; the operator needs the
            # sign-in state, not a generic runtime failure.
            _raise_for_auth_error(exc)
            raise
        # Trailing ``agent_message_chunk`` notifications may arrive after the
        # prompt response; give them a moment to land.
        notifications.extend(self._transport.drain(timeout=0.5))
        stop_reason = result.get("stopReason", "end_turn") if isinstance(result, dict) else "end_turn"
        text = _extract_text_chunks(notifications)
        self.responses.append(text)
        self._record_usage()
        return text, stop_reason

    def _session_file(self) -> Path | None:
        if self._session_file_path is not None:
            return self._session_file_path
        files = sorted(
            self._sessions_dir.glob("*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if files:
            self._session_file_path = files[0]
            return files[0]
        return None

    def _record_usage(self) -> None:
        """Record any new native usage from the pi session file as a planning turn."""
        session_file = self._session_file()
        if session_file is None:
            return
        evidence = parse_pi_usage_stream(
            session_file.read_text(encoding="utf-8"),
            model=self._model,
            exclude_response_ids=self._seen_response_ids,
        )
        if evidence is None:
            return
        self._seen_response_ids.update(evidence.raw_usage.get("response_ids", []))
        db.record_token_turn(
            self._database_path,
            session_id=self.session["id"],
            usage_kind="planning",
            model=recorded_model_from_usage(evidence.raw_usage, configured_model=self._model),
            prompt_tokens=evidence.prompt_tokens,
            completion_tokens=evidence.completion_tokens,
            cost=evidence.cost,
            raw_usage=evidence.raw_usage,
        )

    def cancel(self) -> None:
        """Send a ``session/cancel`` notification for the active session."""
        self._transport.notify("session/cancel", {"sessionId": self._session_id})

    def close(self) -> None:
        """Terminate the subprocess and clean up the temporary workdir."""
        _terminate_process_group(self.proc)
        if self._workdir is not None:
            shutil.rmtree(self._workdir, ignore_errors=True)


def _terminate_process_group(proc: subprocess.Popen) -> None:
    """Terminate the bridge and any child processes it spawned (e.g. pi)."""
    if proc.poll() is not None:
        return
    try:
        if hasattr(os, "killpg"):
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
        else:
            proc.terminate()
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            if hasattr(os, "killpg"):
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            else:
                proc.kill()
        except ProcessLookupError:
            pass
        proc.wait(timeout=2)
    finally:
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass


def open_pi_conversation(
    database_path: Path | str,
    *,
    profile_dir: Path | str | None = None,
    model: str,
    cwd: Path | str | None = None,
    timeout: float = 60,
    agent_dir: Path | str | None = None,
) -> PiConversation:
    """Open a governed pi conversation and return a long-lived handle.

    The conversation runs on pi's native provider using the operator's existing
    pi authentication.  The returned ``PiConversation`` handle exposes
    ``prompt(text)``, ``cancel()``, ``close()``, ``session``, and ``proc``.
    The caller is responsible for calling ``close()`` to terminate the subprocess
    and remove the temporary workdir.
    """
    provider, model_id = _resolve_pi_provider_model(model)
    session, _bearer_key = db.create_planning_session(
        database_path,
        task_description="pi orchestrator ACP conversation",
        model=model,
        tracking_mode="native_usage",
    )
    selected_profile_dir = Path(profile_dir) if profile_dir else DEFAULT_PROFILE_DIR
    selected_cwd = Path(cwd) if cwd else Path.cwd()
    selected_agent_dir = Path(agent_dir) if agent_dir else None
    bridge_dir = DEFAULT_BRIDGE_DIR

    tmpdir = tempfile.mkdtemp(prefix="pi-orchestrator-acp-")
    try:
        sessions_dir = Path(tmpdir) / "sessions"
        env = _prepare_pi_env(sessions_dir, agent_dir=selected_agent_dir)
        persona_path = _persona_path(selected_profile_dir)
        wrapper = _write_pi_acp_wrapper(
            Path(tmpdir), persona_path, sessions_dir, provider, model_id
        )
        env[PI_ACP_PI_COMMAND_ENV] = str(wrapper)
        env[PI_ACP_PERSONA_PATH_ENV] = str(persona_path)
        env[PI_ACP_ALLOWED_TOOLS_ENV] = ",".join(PI_ORCHESTRATOR_ALLOWED_TOOLS)
        if provider:
            env[PI_ACP_PROVIDER_ENV] = provider
        env[PI_ACP_MODEL_ENV] = model_id
        env[PI_ACP_SESSION_DIR_ENV] = str(sessions_dir)

        command = _pi_acp_command(bridge_dir)
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=str(bridge_dir),
            start_new_session=True,
        )
        transport = _AcpJsonRpcTransport(proc)
        try:
            transport.call(
                "initialize",
                {
                    "protocolVersion": 1,
                    "clientInfo": {"name": "foreman-ai-hq", "version": "0.1.0"},
                },
                timeout=timeout,
            )
            new_result, _ = transport.call(
                "session/new",
                {"cwd": str(selected_cwd), "mcpServers": []},
                timeout=timeout,
            )
        except AcpRuntimeError as exc:
            _raise_for_auth_error(exc)
            _terminate_process_group(proc)
            raise
        session_id = new_result["sessionId"]
        # Discard pi startup info / available-commands notifications so they
        # do not mix into the first prompt response.
        transport.drain(timeout=1.0)

        return PiConversation(
            session,
            proc,
            transport,
            session_id,
            timeout,
            workdir=Path(tmpdir),
            database_path=database_path,
            model=model,
            sessions_dir=sessions_dir,
        )
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise


@contextlib.contextmanager
def launch_pi_conversation(
    database_path: Path | str,
    prompts: list[str] | None = None,
    *,
    profile_dir: Path | str | None = None,
    model: str,
    cwd: Path | str | None = None,
    agent_dir: Path | str | None = None,
    timeout: float = 60,
) -> Iterator[PiConversation]:
    """Mint one planning session and yield a handle inside a ``with`` block.

    This is the existing context-managed API; it is implemented on top of
    ``open_pi_conversation`` and ``PiConversation.close`` so the spawn/teardown
    logic is not duplicated.
    """
    conv = open_pi_conversation(
        database_path,
        profile_dir=profile_dir,
        model=model,
        cwd=cwd,
        timeout=timeout,
        agent_dir=Path(agent_dir) if agent_dir else None,
    )
    try:
        if prompts:
            for prompt in prompts:
                conv.prompt(prompt)
        yield conv
    finally:
        conv.close()
