from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import secrets
import subprocess
import threading
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from foreman_ai_hq import db
from foreman_ai_hq.adapter_readiness import evaluate_adapter_readiness
from foreman_ai_hq.checkpoints import evaluate_and_record_checkpoints
from foreman_ai_hq.guardrails import GuardrailConfig, load_guardrails
from foreman_ai_hq.launch_guardrails import evaluate_launch_guardrails
from foreman_ai_hq.native_cli_diagnostics import native_cli_diagnostic, redact_native_cli_text
from foreman_ai_hq.native_usage import NativeUsageEvidence, parse_native_usage_evidence
from foreman_ai_hq.project_context import project_task_metadata, resolve_task_project
from foreman_ai_hq.repo_context import build_repo_context_brief, repo_context_prompt
from foreman_ai_hq.settings import Settings
from foreman_ai_hq.task_kind import read_task_kind
from foreman_ai_hq.stream_events import streaming_runner
from foreman_ai_hq.tracking_modes import NATIVE_USAGE, PROXY_GOVERNED
from foreman_ai_hq.worker_adapters import (
    Runner,
    get_adapter_builder,
    redact_command_plan,
)


def _harness_port() -> str:
    return os.environ.get("PORT", "8000")


DEFAULT_PROXY_URL = f"http://127.0.0.1:{_harness_port()}/v1"
LAUNCHABLE_TASK_STATUSES = {"Estimated"}
_LAUNCH_START_LOCK = threading.Lock()
SESSION_KEY_PATTERN = re.compile(r"sk_sess_[A-Za-z0-9_\-.]+")
SECRETISH_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"sk_[A-Za-z0-9_\-.]+"),
)


@dataclass
class TaskLaunchBlocked(Exception):
    task: dict[str, Any]
    reasons: list[str]
    status_code: int = 409


@dataclass(frozen=True)
class TaskLaunchResult:
    task: dict[str, Any]
    session: dict[str, Any] | None
    launch_guardrails: dict[str, Any]
    worker_run: dict[str, Any] | None = None

    def as_response(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "session": self.session,
            "launch_guardrails": self.launch_guardrails,
            "worker_run": self.worker_run,
        }


@dataclass(frozen=True)
class WorkerProcessResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class WorkerRunOutcome:
    kind: str
    error_type: str | None = None
    reason: str | None = None
    native_evidence: NativeUsageEvidence | None = None
    workdir_evidence: dict[str, Any] | None = None
    readonly_diff_evidence: dict[str, Any] | None = None
    marker_stdout: str = ""
    marker_stderr: str = ""
    evidence: dict[str, Any] | None = None
    guardrail_reasons: tuple[str, ...] = ()


def launch_task(
    database_path: Path | str,
    task_id: str,
    *,
    adapter_id: str | None,
    model: str | None,
    proxy_url: str | None,
    project_id: str | None = None,
    estimate_tokens: int | None = None,
    budget_override: bool = False,
    native_budget_acknowledged: bool = False,
    budget_since: str | None = None,
    runner: Runner | None = None,
    guardrail_config: GuardrailConfig | None = None,
) -> TaskLaunchResult:
    # Claiming a task and creating its Worker Run must be single-threaded inside this process.
    with _LAUNCH_START_LOCK:
        return _launch_task_unlocked(
            database_path,
            task_id,
            adapter_id=adapter_id,
            model=model,
            proxy_url=proxy_url,
            project_id=project_id,
            estimate_tokens=estimate_tokens,
            budget_override=budget_override,
            native_budget_acknowledged=native_budget_acknowledged,
            budget_since=budget_since,
            runner=runner,
            guardrail_config=guardrail_config,
        )


def _launch_task_unlocked(
    database_path: Path | str,
    task_id: str,
    *,
    adapter_id: str | None,
    model: str | None,
    proxy_url: str | None,
    project_id: str | None = None,
    estimate_tokens: int | None = None,
    budget_override: bool = False,
    native_budget_acknowledged: bool = False,
    budget_since: str | None = None,
    runner: Runner | None = None,
    guardrail_config: GuardrailConfig | None = None,
) -> TaskLaunchResult:
    db.mark_stale_worker_runs_interrupted(database_path)
    task = db.get_task(database_path, task_id)
    if guardrail_config is None:
        # Every request path passes the app's guardrails explicitly, and the background run
        # thread carries them through. This fallback is for direct callers (tests, scripts),
        # which have no app state to read them from.
        guardrail_config = load_guardrails(Settings().guardrails_path)
    manual_estimate_requested = estimate_tokens is not None and bool(model)

    if project_id:
        _, project_reasons = resolve_task_project(database_path, task, expected_project_id=project_id)
        if project_reasons:
            blocked = _mark_launch_status_blocked(database_path, task, project_reasons)
            raise TaskLaunchBlocked(blocked, project_reasons)

    active_run = db.get_active_worker_run_for_task(database_path, task_id)
    if active_run is not None:
        # Rehydrate the existing run instead of starting a duplicate worker for repeated clicks/API calls.
        session = db.get_session(database_path, active_run["session_id"])
        running_task = db.update_task(
            database_path,
            task_id,
            {
                "status": "Running",
                "session_id": active_run["session_id"],
                "metadata": _clear_recoverable_launch_failure_metadata(
                    {**task.get("metadata", {}), "active_worker_run_id": active_run["id"]}
                ),
            },
        )
        return TaskLaunchResult(
            task=running_task,
            session=session,
            worker_run=active_run,
            launch_guardrails={"passed": True, "reasons": [], "duplicate_active_run": True, "worker_run_id": active_run["id"]},
        )

    if task.get("status") not in LAUNCHABLE_TASK_STATUSES:
        if manual_estimate_requested and _is_manual_estimate_required(task):
            task = _apply_manual_estimate(database_path, task, estimate_tokens, str(model))
        else:
            blocked = _mark_launch_status_blocked(
                database_path,
                task,
                ["Only Estimated tasks can launch."],
            )
            raise TaskLaunchBlocked(blocked, ["Only Estimated tasks can launch."])
    elif manual_estimate_requested:
        task = _apply_manual_estimate(database_path, task, estimate_tokens, str(model))

    if task.get("status") not in LAUNCHABLE_TASK_STATUSES:
        blocked = _mark_launch_status_blocked(
            database_path,
            task,
            ["Only Estimated tasks can launch."],
        )
        raise TaskLaunchBlocked(blocked, ["Only Estimated tasks can launch."])

    metadata = task.get("metadata") or {}
    task_kind = read_task_kind(metadata)
    # Launch mode is derived from canonical task kind; stale metadata and client values are ignored.
    # Legacy `scout` rows continue to launch read-only so historical Tasks stay safe.
    write_capable = task_kind == "implementation"
    read_only = task_kind in {"acceptance_verification", "scout"}
    selected_model = model or task.get("recommended_model")
    selected_adapter_id = adapter_id or _default_adapter_id(database_path)
    selected_proxy_url = proxy_url or DEFAULT_PROXY_URL
    session_api_key = f"sk_sess_{secrets.token_urlsafe(24)}"

    if not selected_model:
        routing_constraint = metadata.get("worker_model_constraint") if isinstance(metadata, dict) else None
        setup_required = ""
        if isinstance(routing_constraint, dict):
            setup_required = str(routing_constraint.get("setup_required") or "").strip()
        reason = setup_required or "Selected Worker model is required before launch."
        blocked = _mark_launch_blocked(database_path, task, [reason])
        raise TaskLaunchBlocked(blocked, [reason])
    if not task.get("estimate_tokens"):
        blocked = _mark_launch_blocked(database_path, task, ["Token estimate is required before launch."])
        raise TaskLaunchBlocked(blocked, ["Token estimate is required before launch."])
    if not selected_adapter_id:
        blocked = _mark_launch_blocked(database_path, task, ["No worker adapter is configured for launch."])
        raise TaskLaunchBlocked(blocked, ["No worker adapter is configured for launch."])

    project, project_reasons = resolve_task_project(database_path, task, expected_project_id=project_id)
    if not project:
        blocked = _mark_launch_blocked(database_path, task, project_reasons)
        raise TaskLaunchBlocked(blocked, project_reasons)
    project_root = str(project["root_path"])
    project_metadata = project_task_metadata(project)

    guardrails = evaluate_launch_guardrails(
        database_path,
        adapter_id=selected_adapter_id,
        model=selected_model,
        project_root=project_root,
        session_api_key=session_api_key,
        proxy_url=selected_proxy_url,
        read_only=read_only,
    )
    if not guardrails.passed or guardrails.adapter is None:
        blocked = _mark_launch_blocked(database_path, task, guardrails.reasons)
        raise TaskLaunchBlocked(blocked, guardrails.reasons)

    tracking_mode = (guardrails.adapter.get("verification_evidence") or {}).get("tracking_mode") or PROXY_GOVERNED
    usage_source = NATIVE_USAGE if tracking_mode == NATIVE_USAGE else "harness_proxy"

    budget_check = _evaluate_launch_budget(database_path, task, budget_since=budget_since)
    if not budget_check["passed"] and not budget_override:
        blocked = _mark_budget_launch_blocked(database_path, task, budget_check, tracking_mode=tracking_mode)
        raise TaskLaunchBlocked(blocked, [budget_check["reason"]])
    if not budget_check["passed"] and budget_override and tracking_mode == NATIVE_USAGE and not native_budget_acknowledged:
        # Native CLI runs cannot be throttled mid-request, so budget overrides need explicit acknowledgement.
        blocked = _mark_budget_launch_blocked(
            database_path,
            task,
            budget_check,
            tracking_mode=tracking_mode,
            reason="Native usage budget override requires acknowledgement that runtime request throttling is not available.",
        )
        raise TaskLaunchBlocked(blocked, ["Native usage budget override requires acknowledgement that runtime request throttling is not available."])

    # Read-only launches get a cheap before/after snapshot to prove the worker did not mutate files.
    before_tree = _read_only_tree_snapshot(project_root) if project_root else None
    repo_context = build_repo_context_brief(project_root)
    task_prompt = repo_context_prompt(task["description"], repo_context)
    if read_only:
        task_prompt += (
            "\n\nThis is a read-only acceptance verification task. "
            "Use only file-read and analysis tools. "
            "Do not create, edit, move, delete, commit, or branch anything. "
            "Produce findings, risks, and a concise recommendation."
        )
    task_branch = None
    if write_capable:
        cleanliness_reasons, setup_href = _write_cleanliness_failures(project_root, project.get("profile"))
        if cleanliness_reasons:
            blocked = _mark_write_launch_blocked(database_path, task, cleanliness_reasons, setup_href=setup_href)
            raise TaskLaunchBlocked(blocked, cleanliness_reasons)

    session = db.create_session(
        database_path,
        task_description=task["description"],
        model=selected_model,
        session_key_hash=_hash_key(session_api_key),
        guardrail_overrides={
            "task_launch": {
                "task_id": task_id,
                "adapter_id": selected_adapter_id,
                "tracking_mode": tracking_mode,
                "usage_source": usage_source,
            },
            "budget": _session_budget_overrides(task, budget_check, budget_override),
        },
        status="running",
    )
    if write_capable:
        task_branch, original_branch = _create_task_branch(project_root, task, project.get("profile"))

    builder = get_adapter_builder(guardrails.adapter)
    if tracking_mode == NATIVE_USAGE:
        plan = builder.build_native_launch_command(
            model=selected_model,
            task_prompt=task_prompt,
            project_root=project_root,
            read_only=read_only,
        )
    else:
        plan = builder.build_launch_command(
            model=selected_model,
            task_prompt=task_prompt,
            proxy_url=selected_proxy_url,
            session_api_key=session_api_key,
            project_root=project_root,
            read_only=read_only,
        )
    plan = replace(
        plan,
        metadata={
            **plan.metadata,
            "session_id": session["id"],
            "task_id": task_id,
            "launch_mode": "write_capable" if write_capable else "read_only",
            **({"task_branch": task_branch} if task_branch else {}),
        },
    )
    command_plan = redact_command_plan(plan)
    claimed = db.update_task(
        database_path,
        task_id,
        {
            "status": "Running",
            "session_id": session["id"],
            "metadata": _clear_recoverable_launch_failure_metadata(
                {
                    **task.get("metadata", {}),
                    **project_metadata,
                    "launch_adapter_id": selected_adapter_id,
                    "launch_model": selected_model,
                    "tracking_mode": tracking_mode,
                    "usage_source": usage_source,
                    "launch_command_plan": command_plan,
                    "repo_context_brief": repo_context,
                    "launch_project_root": project_root,
                    "launch_mode": "write_capable" if write_capable else "read_only",
                    "budget_check": budget_check,
                    **({"budget_override": {"approved": True, "reason": "operator_approved_launch"}} if budget_override else {}),
                    **({"task_branch": task_branch, "operator_branch": original_branch} if task_branch else {}),
                }
            ),
        },
    )

    worker_run = db.create_worker_run(
        database_path,
        task_id=task_id,
        session_id=session["id"],
        adapter_id=selected_adapter_id,
        model=selected_model,
        tracking_mode=tracking_mode,
        command_plan=command_plan,
        metadata={
            "usage_source": usage_source,
            "launch_mode": "write_capable" if write_capable else "read_only",
            "launch_project_root": project_root,
            "connected_project_id": project["id"],
            "project_profile": project.get("profile") or {},
            "repo_context_brief": repo_context,
            **({"task_branch": task_branch, "operator_branch": original_branch} if task_branch else {}),
        },
    )
    _record_worker_event(
        database_path,
        worker_run,
        kind="launch",
        title="Launch requested",
        detail={"adapter_id": selected_adapter_id, "model": selected_model, "tracking_mode": tracking_mode},
    )
    _record_worker_event(
        database_path,
        worker_run,
        kind="guardrail",
        title="Launch guardrails passed",
        detail={"adapter_id": selected_adapter_id, "model": selected_model, "tracking_mode": tracking_mode},
    )
    _record_worker_event(
        database_path,
        worker_run,
        kind="context",
        title="Repo Context Brief built",
        detail={
            "documents": [doc["path"] for doc in repo_context.get("documents", [])],
            "manifests": repo_context.get("manifests", []),
            "test_commands": repo_context.get("test_commands", []),
        },
    )
    _record_worker_event(
        database_path,
        worker_run,
        kind="command",
        title="Worker command planned",
        detail={"command_plan": command_plan},
    )
    claimed = db.update_task(
        database_path,
        task_id,
        {
            "status": "Running",
            "session_id": session["id"],
            "metadata": {**claimed.get("metadata", {}), "active_worker_run_id": worker_run["id"]},
        },
    )
    _start_background_worker_run(
        database_path=database_path,
        worker_run_id=worker_run["id"],
        task=task,
        claimed=claimed,
        session=session,
        plan=plan,
        selected_adapter_id=selected_adapter_id,
        selected_model=selected_model,
        tracking_mode=tracking_mode,
        usage_source=usage_source,
        project_root=project_root,
        before_tree=before_tree,
        read_only=read_only,
        write_capable=write_capable,
        runner=runner,
        guardrail_config=guardrail_config,
    )
    return TaskLaunchResult(
        task=claimed,
        session=session,
        worker_run=worker_run,
        launch_guardrails={"passed": True, "reasons": [], "adapter_id": selected_adapter_id, "worker_run_id": worker_run["id"]},
    )


def _record_worker_event(
    database_path: Path | str,
    worker_run: dict[str, Any],
    *,
    kind: str,
    title: str,
    level: str = "info",
    detail: dict[str, Any] | None = None,
) -> None:
    db.record_worker_run_event(
        database_path,
        worker_run_id=worker_run["id"],
        session_id=worker_run["session_id"],
        task_id=worker_run["task_id"],
        kind=kind,
        layer="worker_harness" if kind in {"adapter", "agent_message", "tool_call", "token", "status", "file"} else "control_plane",
        level=level,
        title=title,
        detail=detail,
    )


def _start_background_worker_run(
    *,
    database_path: Path | str,
    worker_run_id: str,
    task: dict[str, Any],
    claimed: dict[str, Any],
    session: dict[str, Any],
    plan: Any,
    selected_adapter_id: str,
    selected_model: str,
    tracking_mode: str,
    usage_source: str,
    project_root: str | None,
    before_tree: str | None,
    read_only: bool,
    write_capable: bool,
    runner: Runner | None,
    guardrail_config: GuardrailConfig,
) -> None:
    thread = threading.Thread(
        target=_execute_worker_run_safe,
        kwargs={
            "database_path": database_path,
            "worker_run_id": worker_run_id,
            "task": task,
            "claimed": claimed,
            "session": session,
            "plan": plan,
            "selected_adapter_id": selected_adapter_id,
            "selected_model": selected_model,
            "tracking_mode": tracking_mode,
            "usage_source": usage_source,
            "project_root": project_root,
            "before_tree": before_tree,
            "read_only": read_only,
            "write_capable": write_capable,
            "runner": runner,
            "guardrail_config": guardrail_config,
        },
        daemon=True,
        name=f"worker-run-{worker_run_id}",
    )
    thread.start()


def _execute_worker_run_safe(
    *,
    database_path: Path | str,
    worker_run_id: str,
    task: dict[str, Any],
    claimed: dict[str, Any],
    session: dict[str, Any],
    plan: Any,
    selected_adapter_id: str,
    selected_model: str,
    tracking_mode: str,
    usage_source: str,
    project_root: str | None,
    before_tree: str | None,
    read_only: bool,
    write_capable: bool,
    runner: Runner | None,
    guardrail_config: GuardrailConfig,
) -> None:
    try:
        _execute_worker_run(
            database_path=database_path,
            worker_run_id=worker_run_id,
            task=task,
            claimed=claimed,
            session=session,
            plan=plan,
            selected_adapter_id=selected_adapter_id,
            selected_model=selected_model,
            tracking_mode=tracking_mode,
            usage_source=usage_source,
            project_root=project_root,
            before_tree=before_tree,
            read_only=read_only,
            write_capable=write_capable,
            runner=runner,
            guardrail_config=guardrail_config,
        )
    except Exception as exc:
        reason = f"Worker Run failed unexpectedly: {type(exc).__name__}"
        try:
            db.update_session_status(database_path, session["id"], "failed")
            failed = _mark_recoverable_launch_failure(
                database_path,
                task=task,
                claimed=claimed,
                session_id=session["id"],
                reason=reason,
                failure_type="worker_run_exception",
                project_root=project_root,
                write_capable=write_capable,
                guardrail_reasons=[reason],
            )
            db.mark_worker_run_failed(
                database_path,
                worker_run_id,
                error_type="worker_run_exception",
                error_message=reason,
                metadata={"task_status": failed["status"]},
            )
        except Exception:
            pass


def _execute_worker_run(
    *,
    database_path: Path | str,
    worker_run_id: str,
    task: dict[str, Any],
    claimed: dict[str, Any],
    session: dict[str, Any],
    plan: Any,
    selected_adapter_id: str,
    selected_model: str,
    tracking_mode: str,
    usage_source: str,
    project_root: str | None,
    before_tree: str | None,
    read_only: bool,
    write_capable: bool,
    runner: Runner | None,
    guardrail_config: GuardrailConfig,
) -> None:
    worker_run = db.mark_worker_run_running(database_path, worker_run_id)
    _record_worker_event(
        database_path,
        worker_run,
        kind="adapter",
        title="Worker adapter started",
        detail={"adapter_id": selected_adapter_id, "model": selected_model, "tracking_mode": tracking_mode},
    )
    builder = get_adapter_builder(db.get_worker_adapter(database_path, selected_adapter_id))

    def on_stream_line(raw_line: str) -> None:
        try:
            event = builder.map_stream_event(_redact_stream_line(plan, raw_line))
            if event is not None:
                event = _redact_stream_event(plan, event)
                _record_worker_event(
                    database_path,
                    worker_run,
                    kind=event["kind"],
                    title=event["title"],
                    detail=event["detail"],
                )
        except Exception:
            # Timeline capture must not change Worker execution semantics.
            pass

    result = _run_worker_adapter(plan, runner, on_stream_line)
    outcome = _classify_worker_run_result(
        database_path=database_path,
        session=session,
        plan=plan,
        selected_model=selected_model,
        tracking_mode=tracking_mode,
        project_root=project_root,
        before_tree=before_tree,
        read_only=read_only,
        write_capable=write_capable,
        result=result,
    )
    _apply_worker_run_outcome(
        database_path=database_path,
        worker_run_id=worker_run_id,
        worker_run=worker_run,
        task=task,
        claimed=claimed,
        session=session,
        selected_model=selected_model,
        tracking_mode=tracking_mode,
        usage_source=usage_source,
        project_root=project_root,
        read_only=read_only,
        write_capable=write_capable,
        result=result,
        outcome=outcome,
        guardrail_config=guardrail_config,
    )


def _run_worker_adapter(
    plan: Any,
    runner: Callable[..., Any] | None,
    on_event: Callable[[str], None] | None = None,
) -> WorkerProcessResult:
    on_event = on_event or (lambda _raw_line: None)
    try:
        if runner is None:
            completed = streaming_runner(plan, on_event)
        elif _runner_accepts_event_callback(runner):
            completed = runner(plan, on_event)
        else:
            completed = runner(plan)
            for raw_line in str(_result_field(completed, "stdout", "")).splitlines(keepends=True):
                on_event(raw_line)
    except Exception as exc:
        completed = subprocess.CompletedProcess(
            plan.command,
            127,
            stdout="",
            stderr=f"Failed to launch adapter runner: {type(exc).__name__}",
        )
    return WorkerProcessResult(
        returncode=int(_result_field(completed, "returncode", 0) or 0),
        stdout=str(_result_field(completed, "stdout", "")),
        stderr=str(_result_field(completed, "stderr", "")),
    )


def _runner_accepts_event_callback(runner: Callable[..., Any]) -> bool:
    try:
        parameters = list(inspect.signature(runner).parameters.values())
    except (TypeError, ValueError):
        return False
    return any(parameter.kind == inspect.Parameter.VAR_POSITIONAL for parameter in parameters) or len(parameters) >= 2


def _redact_stream_event(plan: Any, event: Any) -> Any:
    prompts = _stream_prompts(plan)
    return {
        **event,
        "title": _redact_stream_value(event["title"], prompts),
        "detail": _redact_stream_value(event["detail"], prompts),
    }


def _redact_stream_line(plan: Any, raw_line: str) -> str:
    return _redact_stream_value(raw_line, _stream_prompts(plan))


def _stream_prompts(plan: Any) -> list[str]:
    command = getattr(plan, "command", []) or []
    metadata = getattr(plan, "metadata", {}) or {}
    prompts: list[str] = []
    for index in metadata.get("prompt_argument_indices", []):
        if isinstance(index, int) and 0 <= index < len(command):
            prompt = str(command[index])
            if prompt:
                prompts.append(prompt)
    return prompts


def _redact_stream_value(value: Any, prompts: list[str]) -> Any:
    if isinstance(value, str):
        for prompt in prompts:
            value = value.replace(prompt, "***PROMPT_REDACTED***")
            value = value.replace(json.dumps(prompt)[1:-1], "***PROMPT_REDACTED***")
        return redact_native_cli_text(value)
    if isinstance(value, dict):
        return {key: _redact_stream_value(item, prompts) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_stream_value(item, prompts) for item in value]
    return value


def _classify_worker_run_result(
    *,
    database_path: Path | str,
    session: dict[str, Any],
    plan: Any,
    selected_model: str,
    tracking_mode: str,
    project_root: str | None,
    before_tree: str | None,
    read_only: bool,
    write_capable: bool,
    result: WorkerProcessResult,
) -> WorkerRunOutcome:
    native_evidence = None
    if tracking_mode == NATIVE_USAGE:
        native_evidence = parse_native_usage_evidence(
            result.stdout,
            model=selected_model,
            returncode=result.returncode,
            allow_failed_returncode=result.returncode != 0,
        )
    action_rejections = _worker_action_rejections(result.stdout, result.stderr)
    if action_rejections:
        reason = "Worker action was rejected by the adapter sandbox or approval policy; operator approval or adapter sandbox changes are required."
        return WorkerRunOutcome(
            kind="recoverable_failure",
            error_type="worker_action_rejected",
            reason=reason,
            native_evidence=native_evidence,
            marker_stdout=result.stdout,
            marker_stderr=result.stderr,
            guardrail_reasons=(reason,),
            evidence={"action_rejections": action_rejections},
        )

    if result.returncode != 0:
        diagnostic = native_cli_diagnostic(
            adapter_id=str((getattr(plan, "metadata", {}) or {}).get("adapter_id") or ""),
            adapter_kind=str((getattr(plan, "metadata", {}) or {}).get("kind") or ""),
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
        )
        return WorkerRunOutcome(
            kind="recoverable_failure",
            error_type="worker_adapter_failure",
            reason=diagnostic["summary"] if diagnostic and diagnostic.get("code") != "native_cli_failure" else "Worker adapter launch failed.",
            native_evidence=native_evidence,
            marker_stdout=result.stdout,
            marker_stderr=result.stderr,
            evidence={"launch_diagnostic": diagnostic} if diagnostic else None,
        )

    permission_denials = _permission_denial_tools(result.stdout)
    if tracking_mode == NATIVE_USAGE:
        if native_evidence is None:
            if permission_denials:
                reason = f"Worker was denied required tool permissions: {', '.join(permission_denials)}."
                return WorkerRunOutcome(
                    kind="recoverable_failure",
                    error_type="worker_permission_denied",
                    reason=reason,
                    marker_stdout=result.stdout,
                    guardrail_reasons=(reason,),
                    evidence={"permission_denials": permission_denials},
                )
            reason = "No budget-authoritative native Worker usage evidence was emitted by the adapter."
            return WorkerRunOutcome(
                kind="recoverable_failure",
                error_type="missing_native_usage_evidence",
                reason=reason,
                marker_stdout=result.stdout,
                guardrail_reasons=(reason,),
            )

    if tracking_mode == PROXY_GOVERNED and not _session_has_worker_token_usage(database_path, session["id"]):
        # Proxy-governed runs are only valid if the worker actually called through the harness proxy.
        reason = "No Worker model call was observed through the Harness Proxy."
        return WorkerRunOutcome(
            kind="recoverable_failure",
            error_type="missing_proxy_worker_usage",
            reason=reason,
            native_evidence=native_evidence,
            marker_stdout=result.stdout,
            guardrail_reasons=(reason,),
        )

    if permission_denials:
        reason = f"Worker was denied required tool permissions: {', '.join(permission_denials)}."
        return WorkerRunOutcome(
            kind="recoverable_failure",
            error_type="worker_permission_denied",
            reason=reason,
            native_evidence=native_evidence,
            marker_stdout=result.stdout,
            guardrail_reasons=(reason,),
            evidence={"permission_denials": permission_denials},
        )

    workdir_evidence = _workdir_run_evidence(plan, stdout=result.stdout, stderr=result.stderr)
    workdir_mismatch = _workdir_mismatch_failure(workdir_evidence)
    if workdir_mismatch is not None:
        return WorkerRunOutcome(
            kind="recoverable_failure",
            error_type="workdir_mismatch",
            reason=workdir_mismatch,
            native_evidence=native_evidence,
            workdir_evidence=workdir_evidence,
            marker_stdout=result.stdout,
            marker_stderr=result.stderr,
            guardrail_reasons=(workdir_mismatch,),
            evidence={"workdir_evidence": workdir_evidence},
        )

    if write_capable:
        return WorkerRunOutcome(kind="write_capable", native_evidence=native_evidence, workdir_evidence=workdir_evidence)

    after_tree = _read_only_tree_snapshot(project_root) if project_root else before_tree
    if read_only and before_tree != after_tree:
        # A successful command can still fail launch if it violates the read-only contract.
        return WorkerRunOutcome(
            kind="read_only_mutation",
            error_type="read_only_mutation",
            reason="Read-only Worker session modified the connected project.",
            native_evidence=native_evidence,
            workdir_evidence=workdir_evidence,
            readonly_diff_evidence={"before": before_tree, "after": after_tree},
        )

    # The write-capable path already returned; read-only mutation is checked above.
    # Any adapter reporting success without filesystem changes is covered by the
    # adapter-agnostic diff_summary check in _finalize_write_capable_launch.
    return WorkerRunOutcome(kind="completed", native_evidence=native_evidence, workdir_evidence=workdir_evidence)


def _evaluate_and_record_worker_checkpoints(
    database_path: Path | str,
    *,
    session_id: str,
    task_id: str,
    worker_run_id: str,
    guardrail_config: GuardrailConfig,
) -> None:
    """Evaluate checkpoints once a Worker Run completes and record failures without failing the run."""
    try:
        evaluate_and_record_checkpoints(database_path, session_id, guardrail_config)
    except Exception as exc:
        # Checkpoints are advisory; a failure to evaluate them must not discard run evidence.
        # `record_worker_run_event` sanitizes `detail` on the way in, so it is passed raw here.
        db.record_worker_run_event(
            database_path,
            worker_run_id=worker_run_id,
            session_id=session_id,
            task_id=task_id,
            kind="checkpoint",
            title="Checkpoint evaluation failed",
            level="error",
            detail={"error": str(exc), "error_type": type(exc).__name__},
        )


def _apply_worker_run_outcome(
    *,
    database_path: Path | str,
    worker_run_id: str,
    worker_run: dict[str, Any],
    task: dict[str, Any],
    claimed: dict[str, Any],
    session: dict[str, Any],
    selected_model: str,
    tracking_mode: str,
    usage_source: str,
    project_root: str | None,
    read_only: bool,
    write_capable: bool,
    result: WorkerProcessResult,
    outcome: WorkerRunOutcome,
    guardrail_config: GuardrailConfig,
) -> None:
    if outcome.native_evidence is not None:
        db.record_token_turn(
            database_path,
            session_id=session["id"],
            usage_kind="task_execution",
            model=selected_model,
            prompt_tokens=outcome.native_evidence.prompt_tokens,
            completion_tokens=outcome.native_evidence.completion_tokens,
            cost=outcome.native_evidence.cost,
            raw_usage={
                **outcome.native_evidence.raw_usage,
                "total_tokens": outcome.native_evidence.total_tokens,
                "usage_source": usage_source,
                "tracking_mode": tracking_mode,
            },
        )
        _record_worker_event(
            database_path,
            worker_run,
            kind="token",
            title="Native usage evidence recorded",
            detail={"total_tokens": outcome.native_evidence.total_tokens, "usage_source": usage_source},
        )

    if tracking_mode == PROXY_GOVERNED and outcome.workdir_evidence is not None:
        _record_worker_event(
            database_path,
            worker_run,
            kind="token",
            title="Proxy usage evidence observed",
            detail={"total_tokens": db.session_token_usage(database_path, session["id"]), "usage_source": usage_source},
        )

    if outcome.workdir_evidence is not None:
        _record_worker_event(
            database_path,
            worker_run,
            kind="file",
            title="Workdir evidence captured",
            detail={"workdir_evidence": outcome.workdir_evidence},
        )

    if outcome.kind == "recoverable_failure":
        db.update_session_status(database_path, session["id"], "failed")
        failed = _mark_recoverable_launch_failure(
            database_path,
            task=task,
            claimed=claimed,
            session_id=session["id"],
            reason=str(outcome.reason),
            failure_type=str(outcome.error_type),
            returncode=result.returncode,
            stdout=outcome.marker_stdout,
            stderr=outcome.marker_stderr,
            project_root=project_root,
            write_capable=write_capable,
            guardrail_reasons=list(outcome.guardrail_reasons),
            evidence=outcome.evidence,
        )
        metadata = {"task_status": failed["status"]}
        if outcome.workdir_evidence is not None:
            metadata["workdir_evidence"] = outcome.workdir_evidence
        db.mark_worker_run_failed(
            database_path,
            worker_run_id,
            error_type=str(outcome.error_type),
            error_message=str(outcome.reason),
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            metadata=metadata,
        )
        return

    if outcome.kind == "write_capable":
        try:
            write_result = _finalize_write_capable_launch(
                database_path=database_path,
                task_id=task["id"],
                task=task,
                claimed=claimed,
                session=session,
                project_root=project_root,
                returncode=result.returncode,
                stdout=result.stdout,
            )
        except TaskLaunchBlocked as exc:
            db.mark_worker_run_failed(
                database_path,
                worker_run_id,
                error_type="hard_safety_failure",
                error_message="; ".join(exc.reasons),
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                metadata={"task_status": exc.task["status"]},
            )
            return
        db.mark_worker_run_completed(
            database_path,
            worker_run_id,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            metadata={"task_status": write_result["status"], "workdir_evidence": outcome.workdir_evidence},
        )
        _evaluate_and_record_worker_checkpoints(
            database_path,
            session_id=session["id"],
            task_id=task["id"],
            worker_run_id=worker_run_id,
            guardrail_config=guardrail_config,
        )
        return

    if outcome.kind == "read_only_mutation":
        db.update_session_status(database_path, session["id"], "failed")
        failed = db.update_task(
            database_path,
            task["id"],
            {
                "status": "Review",
                "session_id": session["id"],
                "metadata": {
                    **claimed.get("metadata", {}),
                    "launch_blocked_reason": "Read-only Worker session modified the connected project.",
                    "blocked_condition": _blocked_condition(
                        "Read-only Worker session modified the connected project.",
                        "read_only_mutation",
                    ),
                    "launch_guardrail_reasons": ["Read-only Worker session modified the connected project."],
                    "readonly_diff_evidence": outcome.readonly_diff_evidence,
                    "launch_returncode": result.returncode,
                    "launch_stdout": _safe_text(result.stdout),
                },
            },
        )
        db.mark_worker_run_failed(
            database_path,
            worker_run_id,
            error_type="read_only_mutation",
            error_message="Read-only Worker session modified the connected project.",
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            metadata={"task_status": failed["status"]},
        )
        return

    _record_budget_overrun_if_needed(database_path, session["id"])
    actual_tokens = _worker_execution_token_total(database_path, session["id"])
    db.update_session_status(database_path, session["id"], "completed")
    launched = db.update_task(
        database_path,
        task["id"],
        {
            "status": "Review",
            "session_id": session["id"],
            "actual_tokens": actual_tokens,
            "metadata": {
                **claimed.get("metadata", {}),
                "launch_returncode": result.returncode,
                "launch_stdout": _safe_text(result.stdout),
                "launch_stderr": _safe_text(result.stderr),
                "worker_run_status": "completed",
                "active_worker_run_id": worker_run_id,
                "workdir_evidence": outcome.workdir_evidence,
                **({"diff_summary": _git_diff_summary(project_root)} if project_root else {}),
                **(_read_only_report_metadata(task) if read_only else {}),
            },
        },
    )
    db.mark_worker_run_completed(
        database_path,
        worker_run_id,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        metadata={"task_status": launched["status"], "workdir_evidence": outcome.workdir_evidence},
    )
    _evaluate_and_record_worker_checkpoints(
        database_path,
        session_id=session["id"],
        task_id=task["id"],
        worker_run_id=worker_run_id,
        guardrail_config=guardrail_config,
    )


def _apply_manual_estimate(
    database_path: Path | str, task: dict[str, Any], estimate_tokens: int | None, model: str
) -> dict[str, Any]:
    if estimate_tokens is None:
        return task
    metadata = {**task.get("metadata", {})}
    metadata.pop("blocked_condition", None)
    metadata.pop("blocked_reason", None)
    metadata.pop("requires_manual_estimate", None)
    if not metadata.get("connected_project_id"):
        projects = db.list_connected_projects(database_path)
        if len(projects) == 1:
            metadata = {**project_task_metadata(projects[0]), **metadata}
    return db.update_task(
        database_path,
        task["id"],
        {
            "status": "Estimated",
            "estimate_tokens": estimate_tokens,
            "recommended_model": model,
            "metadata": {**metadata, "estimation_source": "manual"},
        },
    )


def _is_manual_estimate_required(task: dict[str, Any]) -> bool:
    metadata = task.get("metadata", {})
    return task.get("status") == "Estimated" and (
        metadata.get("requires_manual_estimate") is True
        or metadata.get("estimation_source") == "manual_required"
    )



def refresh_task_from_session(database_path: Path | str, task_id: str) -> dict[str, Any]:
    task = db.get_task(database_path, task_id)
    session_id = task.get("session_id")
    if not session_id:
        return task
    artifact = db.build_session_artifact(database_path, session_id)
    session_status = artifact["session"]["status"]
    metadata = dict(task.get("metadata", {}))
    metadata["session_finalized_status"] = session_status
    if session_status == "completed":
        has_issues = bool(artifact["alarms"]) or any(
            not checkpoint["passed"] for checkpoint in artifact["checkpoint_results"]
        )
        return db.update_task(
            database_path,
            task_id,
            {"status": "Review" if has_issues else "Done", "metadata": metadata},
        )
    if session_status in {"failed", "aborted"}:
        reason = f"Session {session_status}."
        metadata.setdefault("blocked_reason", reason)
        metadata["blocked_condition"] = _blocked_condition(reason, "session_completion")
        return db.update_task(database_path, task_id, {"status": "Review", "metadata": metadata})
    return task


def _mark_launch_blocked(database_path: Path | str, task: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    has_estimate = task.get("estimate_tokens") is not None and bool(task.get("recommended_model"))
    status = "Estimated"
    reason = reasons[0] if reasons else "Launch guardrails failed."
    metadata = {
        **task.get("metadata", {}),
        "launch_blocked_reason": reason,
        "launch_guardrail_reasons": list(reasons),
    }
    if not has_estimate:
        metadata.setdefault("blocked_reason", reason)
        metadata.setdefault("requires_manual_estimate", True)
    metadata["blocked_condition"] = _blocked_condition(reason, "launch_guardrail")
    return db.update_task(database_path, task["id"], {"status": status, "metadata": metadata})


def _mark_write_launch_blocked(
    database_path: Path | str,
    task: dict[str, Any],
    reasons: list[str],
    setup_href: str | None = None,
) -> dict[str, Any]:
    reason = reasons[0] if reasons else "Write-capable launch guardrails failed."
    metadata: dict[str, Any] = {
        **task.get("metadata", {}),
        "launch_blocked_reason": reason,
        "launch_guardrail_reasons": list(reasons),
        "blocked_reason": reason,
        "blocked_condition": _blocked_condition(reason, "write_launch_guardrail"),
    }
    if setup_href:
        metadata["launch_diagnostic"] = {"setup_href": setup_href}
    return db.update_task(
        database_path,
        task["id"],
        {
            "status": "Estimated",
            "metadata": metadata,
        },
    )


def _mark_launch_status_blocked(database_path: Path | str, task: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    reason = reasons[0] if reasons else "Launch is not allowed for this task status."
    return db.update_task(
        database_path,
        task["id"],
        {
            "metadata": {
                **task.get("metadata", {}),
                "launch_blocked_reason": reason,
                "launch_guardrail_reasons": list(reasons),
            }
        },
    )


def _mark_recoverable_launch_failure(
    database_path: Path | str,
    *,
    task: dict[str, Any],
    claimed: dict[str, Any],
    session_id: str,
    reason: str,
    failure_type: str,
    returncode: int,
    stderr: str = "",
    stdout: str = "",
    project_root: str | None = None,
    write_capable: bool = False,
    guardrail_reasons: list[str] | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    failure: dict[str, Any] = {
        "type": failure_type,
        "retryable": True,
        "returncode": returncode,
    }
    if stderr:
        failure["stderr"] = _safe_text(stderr)
    if stdout:
        failure["stdout"] = _safe_text(stdout)
    metadata = {
        **claimed.get("metadata", {}),
        "last_launch_failure": failure,
        "launch_error": reason,
        "launch_failure_type": failure_type,
        "launch_retryable": True,
        "launch_guardrail_reasons": list(guardrail_reasons or []),
        "launch_returncode": returncode,
        **({"launch_stderr": _safe_text(stderr)} if stderr else {}),
        **({"launch_stdout": _safe_text(stdout)} if stdout else {}),
        **({"diff_summary": _git_diff_summary(project_root)} if write_capable else {}),
        **(evidence or {}),
    }
    metadata.pop("launch_blocked_reason", None)
    metadata.pop("blocked_reason", None)
    return db.update_task(
        database_path,
        task["id"],
        {"status": task["status"], "session_id": session_id, "metadata": metadata},
    )


def _clear_recoverable_launch_failure_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    cleared = dict(metadata)
    for key in (
        "last_launch_failure",
        "launch_error",
        "launch_failure_type",
        "launch_retryable",
        "launch_guardrail_reasons",
        "launch_stderr",
        "launch_stdout",
        "launch_diagnostic",
        "launch_blocked_reason",
        "blocked_reason",
        "blocked_condition",
        "requires_manual_estimate",
        "budget_override_available",
        "budget_override_reason",
        "budget_override_tracking_mode",
        "native_usage_override_ack_required",
        "native_usage_override_ack_text",
    ):
        cleared.pop(key, None)
    return cleared


def _default_adapter_id(database_path: Path | str) -> str | None:
    adapters = db.list_worker_adapters(database_path)
    for adapter in adapters:
        if adapter.get("is_default") and evaluate_adapter_readiness(adapter).launchable_tracking:
            return str(adapter["id"])
    for adapter in adapters:
        if evaluate_adapter_readiness(adapter).launchable_tracking:
            return str(adapter["id"])
    return adapters[0]["id"] if adapters else None


def _hash_key(session_api_key: str) -> str:
    return hashlib.sha256(session_api_key.encode("utf-8")).hexdigest()


def _result_field(result: Any, field: str, default: Any = "") -> Any:
    if isinstance(result, dict):
        return result.get(field, default)
    return getattr(result, field, default)




def abort_worker_session(database_path: Path | str, session_id: str, *, reason: str) -> dict[str, Any]:
    session = db.update_session_status(database_path, session_id, "aborted")
    affected_tasks = []
    for task in db.list_tasks(database_path):
        if task.get("session_id") != session_id:
            continue
        blocked_reason = f"Session aborted: {reason}"
        metadata = {
            **task.get("metadata", {}),
            "abort_reason": reason,
            "blocked_reason": blocked_reason,
            "blocked_condition": _blocked_condition(blocked_reason, "session_abort"),
        }
        affected_tasks.append(
            db.update_task(database_path, task["id"], {"status": "Review", "metadata": metadata})
        )
    return {"session": session, "tasks": affected_tasks}


def _evaluate_launch_budget(database_path: Path | str, task: dict[str, Any], *, budget_since: str | None = None) -> dict[str, Any]:
    budget = dict(db.get_token_budget_settings(database_path))
    budget.update((task.get("metadata") or {}).get("budget") or {})
    budget_since = budget_since or str(
        budget.get("budget_since") or db.effective_daily_budget_window_start(database_path, timezone="local")
    )
    daily_cap = _optional_int(budget.get("daily_cap_tokens"))
    session_cap = _optional_int(budget.get("session_cap_tokens"))
    daily_used = _optional_int(budget.get("daily_used_tokens")) or 0
    if daily_cap is None:
        return {
            "passed": True,
            "reason": None,
            "estimate_tokens": task.get("estimate_tokens"),
            "remaining_tokens": None,
            "budget_since": budget_since,
        }
    current_breakdown = db.token_usage_breakdown(database_path, since=budget_since)
    current_used = int(current_breakdown["total_tokens"])
    current_worker_used = int(current_breakdown["by_category"]["worker_execution"])
    remaining = max(daily_cap - daily_used - current_used, 0)
    estimate = int(task.get("estimate_tokens") or 0)
    passed = estimate <= remaining
    return {
        "passed": passed,
        "reason": None if passed else "Task estimate exceeds remaining launch budget.",
        "estimate_tokens": estimate,
        "daily_cap_tokens": daily_cap,
        "session_cap_tokens": session_cap,
        "daily_used_tokens": daily_used,
        "current_recorded_tokens": current_used,
        "current_worker_execution_tokens": current_worker_used,
        "current_token_breakdown": current_breakdown["by_category"],
        "budget_since": budget_since,
        "remaining_tokens": remaining,
    }


def _mark_budget_launch_blocked(
    database_path: Path | str,
    task: dict[str, Any],
    budget_check: dict[str, Any],
    *,
    tracking_mode: str,
    reason: str | None = None,
) -> dict[str, Any]:
    blocked_reason = reason or budget_check.get("reason") or "Launch budget guardrail failed."
    status = "Estimated"
    metadata = {
        **task.get("metadata", {}),
        "launch_blocked_reason": blocked_reason,
        "launch_guardrail_reasons": [blocked_reason],
        "budget_check": budget_check,
        "budget_override_available": True,
        "budget_override_tracking_mode": tracking_mode,
        "blocked_condition": _blocked_condition(blocked_reason, "budget_guardrail"),
    }
    if tracking_mode == NATIVE_USAGE:
        metadata["native_usage_override_ack_required"] = True
        metadata["native_usage_override_ack_text"] = "I understand native usage cannot be request-throttled during the run."
    return db.update_task(
        database_path,
        task["id"],
        {
            "status": status,
            "metadata": metadata,
        },
    )


def _session_budget_overrides(task: dict[str, Any], budget_check: dict[str, Any], budget_override: bool) -> dict[str, Any]:
    budget = dict((task.get("metadata") or {}).get("budget") or {})
    for key in ("daily_cap_tokens", "session_cap_tokens", "daily_used_tokens", "budget_since"):
        if budget_check.get(key) is not None:
            budget.setdefault(key, budget_check[key])
    budget["launch_budget_check"] = budget_check
    if budget_override:
        budget["budget_override"] = True
        budget["budget_override_reason"] = "operator_approved_launch"
    return budget


def _record_budget_overrun_if_needed(database_path: Path | str, session_id: str) -> None:
    session = db.get_session(database_path, session_id)
    budget = session.get("guardrail_overrides", {}).get("budget", {})
    session_cap = _optional_int(budget.get("session_cap_tokens"))
    daily_cap = _optional_int(budget.get("daily_cap_tokens"))
    daily_used = _optional_int(budget.get("daily_used_tokens")) or 0
    budget_since = _latest_budget_window_start(
        budget.get("budget_since"),
        db.effective_daily_budget_window_start(database_path, timezone="local"),
    )
    daily_budgeted_tokens = db.budgeted_token_usage(database_path, since=budget_since)
    session_used = db.session_token_breakdown(database_path, session_id)["by_category"]["worker_execution"]
    daily_total = daily_used + daily_budgeted_tokens
    overrun = None
    if session_cap is not None and session_used > session_cap:
        overrun = {"scope": "session", "used_tokens": session_used, "cap_tokens": session_cap}
    elif daily_cap is not None and daily_total > daily_cap:
        overrun = {"scope": "daily", "used_tokens": daily_total, "cap_tokens": daily_cap}
    if overrun is None:
        return
    existing = db.list_alarms(database_path, session_id=session_id, alarm_type="BUDGET_OVERRUN")
    if existing:
        # One budget-overrun alarm per session is enough; later reports use the same session artifact.
        return
    db.record_alarm(
        database_path,
        session_id=session_id,
        alarm={
            "id": f"alarm_{secrets.token_hex(8)}",
            "type": "BUDGET_OVERRUN",
            "severity": "high",
            "context": overrun,
            "recommended_action": "Review budget overrun; session was not automatically killed.",
        },
    )


def _current_day_start_iso(timezone: str) -> str:
    return db.current_day_start_iso(timezone)


def _latest_budget_window_start(*values: Any) -> str:
    parsed_values: list[datetime] = []
    for value in values:
        if not value:
            continue
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        parsed_values.append(parsed.astimezone(UTC))
    if not parsed_values:
        return datetime.now(UTC).isoformat()
    return max(parsed_values).isoformat()


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def detect_pr_capability(root_path: Path | str) -> dict[str, Any]:
    root = Path(root_path)
    remotes = _git_lines(root, ["remote", "-v"])
    github_remote = any("github.com" in line for line in remotes)
    if not github_remote:
        return {"available": False, "github_remote": False, "gh_authenticated": False, "reason": "GitHub remote is not configured."}
    gh_exists = subprocess.run(["which", "gh"], capture_output=True, text=True, check=False).returncode == 0
    if not gh_exists:
        return {"available": False, "github_remote": True, "gh_authenticated": False, "reason": "gh CLI is not installed."}
    auth = subprocess.run(["gh", "auth", "status"], cwd=str(root), capture_output=True, text=True, check=False, timeout=10)
    authenticated = auth.returncode == 0
    return {
        "available": authenticated,
        "github_remote": True,
        "gh_authenticated": authenticated,
        "reason": None if authenticated else "gh CLI is not authenticated.",
    }


def _write_cleanliness_failures(root_path: str | None, project_profile: dict[str, Any] | None = None) -> tuple[list[str], str | None]:
    if not root_path:
        return (["Connected project path is required for write-capable launch."], None)
    root = Path(root_path)
    if not (root / ".git").exists():
        return (["Write-capable launch requires a git repository."], None)
    branch = _current_branch(root)
    if not branch:
        return (["Write-capable launch requires a visible current git branch."], None)
    status = _git_porcelain(str(root))
    if status:
        lines = [line.strip() for line in status.splitlines() if line.strip()]
        paths = [line[3:].strip() if len(line) > 3 else line for line in lines]
        return (
            [
                "Write-capable launch requires a clean working tree before launch.",
                f"Offending paths: {', '.join(paths[:20])}",
            ],
            None,
        )
    profile = project_profile or {}
    if profile.get("test_command_suggested") and not profile.get("test_command_confirmed"):
        return (
            [
                "Write-capable launch is blocked until the suggested verification command is confirmed.",
                f"Suggested command: {profile['test_command_suggested']}",
            ],
            "/settings/project",
        )
    if profile.get("base_branch_suggested") and not profile.get("base_branch_confirmed"):
        return (
            [
                "Write-capable launch is blocked until the suggested base branch is confirmed.",
                f"Suggested base branch: {profile['base_branch_suggested']}",
            ],
            "/settings/project",
        )
    if profile.get("base_branch") and not _branch_exists(root, str(profile["base_branch"])):
        return (
            [f"Write-capable launch requires the configured base branch '{profile['base_branch']}' to exist."],
            "/settings/project",
        )
    # Legacy profiles created before the base-branch confirm flow must confirm it.
    if not profile.get("base_branch_confirmed"):
        return (
            [
                "Write-capable launch requires a confirmed base branch.",
                "Open Project Settings to confirm.",
            ],
            "/settings/project",
        )
    return ([], None)


def _create_task_branch(
    root_path: str | None,
    task: dict[str, Any],
    project_profile: dict[str, Any] | None = None,
) -> tuple[str, str]:
    root = Path(str(root_path))
    branch = f"foremanctl/task-{task['id'].replace('task_', '')[:8]}-{_slug(task['description'])}"
    profile = project_profile or {}
    base_branch = profile.get("base_branch") or profile.get("base_branch_suggested")
    if not base_branch:
        raise RuntimeError("failed to determine base branch for task branch")
    if not _branch_exists(root, base_branch):
        raise TaskLaunchBlocked(
            task,
            [f"Write-capable launch requires the configured base branch '{base_branch}' to exist."],
        )
    original_branch = _current_branch(root)
    # `-B` so relaunching a Task whose earlier run failed resets its branch to the base
    # instead of failing on the leftover branch. A Task that already committed is in
    # Review and cannot launch, so nothing committed is ever discarded here.
    result = subprocess.run(
        ["git", "checkout", "-B", branch, base_branch],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"failed to create task branch: {_safe_text(result.stderr or result.stdout)}")
    return branch, original_branch or base_branch


def _finalize_write_capable_launch(
    *,
    database_path: Path | str,
    task_id: str,
    task: dict[str, Any],
    claimed: dict[str, Any],
    session: dict[str, Any],
    project_root: str | None,
    returncode: int,
    stdout: str,
) -> dict[str, Any]:
    project, _ = resolve_task_project(database_path, claimed)
    profile = (project or {}).get("profile") or {}
    # Only operator-confirmed configuration is used for verification.
    test_command = profile.get("test_command") if profile.get("test_command_confirmed") else None
    diff_summary = _git_diff_summary(project_root)
    _record_budget_overrun_if_needed(database_path, session["id"])
    base_metadata = {
        **claimed.get("metadata", {}),
        "launch_returncode": returncode,
        "launch_stdout": _safe_text(stdout),
        "diff_summary": diff_summary,
        "pr_capability": detect_pr_capability(project_root) if project_root else {"available": False, "reason": "No project root."},
    }
    actual_tokens = _worker_execution_token_total(database_path, session["id"])
    if not diff_summary["has_changes"]:
        reason = "Worker completed but produced no code changes."
        db.update_session_status(database_path, session["id"], "failed")
        failed = db.update_task(
            database_path,
            task_id,
            {
                "status": "Review",
                "session_id": session["id"],
                "actual_tokens": actual_tokens,
                "metadata": {
                    **base_metadata,
                    "launch_blocked_reason": reason,
                    "launch_guardrail_reasons": [reason],
                    "blocked_reason": reason,
                    "blocked_condition": _blocked_condition(reason, "write_completion"),
                },
            },
        )
        raise TaskLaunchBlocked(failed, [reason])
    if not test_command:
        db.update_session_status(database_path, session["id"], "completed")
        return db.update_task(
            database_path,
            task_id,
            {
                "status": "Review",
                "session_id": session["id"],
                "actual_tokens": actual_tokens,
                "metadata": {
                    **base_metadata,
                    "post_run_verification": {"passed": False, "reason": "No test command confirmed."},
                    "review_disposition_state": {
                        "pending_decision": True,
                        "reason": "verification_command_missing",
                        "available_actions": ["approve_commit"],
                    },
                },
            },
        )

    verification = _run_test_command(project_root, str(test_command))
    if not verification["passed"]:
        db.update_session_status(database_path, session["id"], "failed")
        return db.update_task(
            database_path,
            task_id,
            {
                "status": "Review",
                "session_id": session["id"],
                "metadata": {
                    **base_metadata,
                    "post_run_verification": verification,
                    "review_disposition_state": {
                        "pending_decision": True,
                        "reason": "verification_failed",
                        "available_actions": ["approve_commit", "block"],
                    },
                },
            },
        )

    commit = _create_harness_commit(project_root, task, session, verification_result=verification)
    _restore_operator_branch(project_root, claimed.get("metadata", {}).get("operator_branch"))
    db.update_session_status(database_path, session["id"], "completed")
    updated = db.update_task(
        database_path,
        task_id,
        {
            "status": "Review",
            "session_id": session["id"],
            "actual_tokens": actual_tokens,
            "metadata": {
                **base_metadata,
                "post_run_verification": verification,
                **({"harness_commit": commit} if commit else {}),
                "review_disposition_state": _review_disposition_state_after_commit(commit, base_metadata["pr_capability"]),
            },
        },
    )
    return updated


def _review_disposition_state_after_commit(commit: dict[str, Any] | None, pr_capability: dict[str, Any]) -> dict[str, Any]:
    actions: list[str] = []
    reason = None
    if not pr_capability.get("available"):
        reason = pr_capability.get("reason") or "Pull request capability is not available."
    elif commit is not None:
        actions.append("open_pr")
    return {
        "pending_decision": False,
        "available_actions": actions,
        "pr_unavailable_reason": reason,
    }


def _run_test_command(root_path: str | None, command: str) -> dict[str, Any]:
    result = subprocess.run(command, cwd=str(root_path), shell=True, capture_output=True, text=True, check=False, timeout=120)
    return {
        "command": command,
        "passed": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": _safe_text(result.stdout, limit=1000),
        "stderr": _safe_text(result.stderr, limit=1000),
    }


def _restore_operator_branch(project_root: str | None, operator_branch: str | None) -> None:
    if not project_root or not operator_branch:
        return
    subprocess.run(
        ["git", "checkout", operator_branch],
        cwd=str(project_root),
        capture_output=True,
        check=False,
        timeout=10,
    )


def _git_diff_summary(root_path: str | None) -> dict[str, Any]:
    if not root_path:
        return {"has_changes": False, "files_changed": [], "stat": ""}
    root = Path(root_path)
    porcelain = _git_porcelain(str(root)) or ""
    files = []
    for line in porcelain.splitlines():
        if not line:
            continue
        files.append(line[3:] if len(line) > 3 else line)
    stat = subprocess.run(["git", "diff", "--stat"], cwd=str(root), capture_output=True, text=True, check=False, timeout=10).stdout.strip()
    if not stat and files:
        stat = "\n".join(files)
    return {"has_changes": bool(files), "files_changed": files, "stat": stat, "porcelain": porcelain}


def _create_harness_commit(
    root_path: str | None,
    task: dict[str, Any],
    session: dict[str, Any],
    *,
    verification_result: dict[str, Any] | None = None,
    authorization: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    root = Path(str(root_path))
    # A second approval on an already-committed task must not create an empty commit.
    status = subprocess.run(["git", "status", "--porcelain"], cwd=str(root), capture_output=True, text=True, check=False, timeout=10).stdout.strip()
    if not status:
        return None
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True, timeout=10)
    message = f"harness: complete {task['id']}\n\nSession: {session['id']}\nTask: {task['description']}"
    subprocess.run(
        ["git", "-c", "user.email=harness@example.invalid", "-c", "user.name=Foreman AI HQ Harness", "commit", "-m", message],
        cwd=str(root),
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(root), check=True, capture_output=True, text=True, timeout=10).stdout.strip()
    return {
        "sha": sha,
        "message": message,
        "verification_result": verification_result,
        "authorization": authorization,
    }


def _current_branch(root: Path) -> str | None:
    result = subprocess.run(["git", "branch", "--show-current"], cwd=str(root), capture_output=True, text=True, check=False, timeout=10)
    branch = result.stdout.strip()
    return branch or None


def _branch_exists(root: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", branch],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    return result.returncode == 0


def _git_lines(root: Path, args: list[str]) -> list[str]:
    result = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True, check=False, timeout=10)
    return result.stdout.splitlines()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug or "task")[:32]


def _session_has_worker_token_usage(database_path: Path | str, session_id: str) -> bool:
    artifact = db.build_session_artifact(database_path, session_id)
    return any(turn.get("usage_kind") in {"task_execution", "worker"} for turn in artifact["token_log"])


def _worker_execution_token_total(database_path: Path | str, session_id: str) -> int:
    breakdown = db.session_token_breakdown(database_path, session_id)
    return int((breakdown.get("by_category") or {}).get("worker_execution") or 0)


def _permission_denial_tools(stdout: str) -> list[str]:
    tools: list[str] = []
    seen: set[str] = set()
    for line in stdout.splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        denials = payload.get("permission_denials") if isinstance(payload, dict) else None
        if not isinstance(denials, list):
            continue
        for denial in denials:
            if not isinstance(denial, dict):
                continue
            tool = _safe_text(str(denial.get("tool_name") or ""), limit=100)
            if tool and tool not in seen:
                seen.add(tool)
                tools.append(tool)
    return tools[:20]


def _worker_action_rejections(stdout: str, stderr: str) -> list[str]:
    rejections: list[str] = []
    seen: set[str] = set()
    for line in (stdout + "\n" + stderr).splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            candidates = [line]
        else:
            candidates = _json_string_values(payload)
        for candidate in candidates:
            text = " ".join(str(candidate).split())
            if not text or not _looks_like_action_rejection(text):
                continue
            safe = _safe_text(text, limit=500)
            if safe not in seen:
                seen.add(safe)
                rejections.append(safe)
    return rejections[:10]


def _json_string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for nested in value.values():
            strings.extend(_json_string_values(nested))
        return strings
    if isinstance(value, list):
        strings = []
        for nested in value:
            strings.extend(_json_string_values(nested))
        return strings
    return []


def _looks_like_action_rejection(text: str) -> bool:
    lowered = text.lower()
    if "createprocess" in lowered and "reject" in lowered:
        return True
    if "sandbox" in lowered and any(term in lowered for term in ("reject", "blocked", "denied", "not permitted")):
        return True
    if "requires approval" in lowered or "approval required" in lowered:
        return True
    return False


def _workdir_run_evidence(plan: Any, *, stdout: str, stderr: str) -> dict[str, Any]:
    configured = Path(plan.cwd).resolve() if getattr(plan, "cwd", None) else None
    top_level_entries: list[str] = []
    exists = False
    if configured is not None:
        exists = configured.exists()
        if exists and configured.is_dir():
            top_level_entries = sorted(entry.name for entry in configured.iterdir())[:50]
    outside_paths = _outside_workdir_paths(stdout + "\n" + stderr, configured)
    return {
        "configured_workdir": str(configured) if configured else None,
        "command_cwd": str(getattr(plan, "cwd", None)) if getattr(plan, "cwd", None) else None,
        "exists": exists,
        "top_level_entries": top_level_entries,
        "has_filesystem_evidence": bool(top_level_entries),
        "outside_paths": outside_paths,
    }


def _workdir_mismatch_failure(evidence: dict[str, Any]) -> str | None:
    if not evidence.get("configured_workdir"):
        return None
    if evidence.get("has_filesystem_evidence"):
        return None
    if not evidence.get("outside_paths"):
        return None
    return "Worker completed but produced evidence outside the configured workdir."


def _outside_workdir_paths(text: str, configured_workdir: Path | None) -> list[str]:
    if configured_workdir is None:
        return []
    paths: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"/(?:Users|private|tmp|var|Volumes)/[^\s'\"`<>),\\]+", text):
        raw = match.group(0).rstrip(".:;]")
        try:
            candidate = Path(raw).resolve()
        except OSError:
            continue
        try:
            candidate.relative_to(configured_workdir)
            continue
        except ValueError:
            pass
        value = _safe_text(str(candidate), limit=500)
        if value not in seen:
            seen.add(value)
            paths.append(value)
    return paths[:20]


def _blocked_condition(reason: str, origin: str) -> dict[str, str]:
    return {"reason": reason, "origin": origin, "timestamp": datetime.now(UTC).isoformat()}


def _git_porcelain(root_path: str | None) -> str | None:
    if not root_path:
        return None
    root = Path(root_path)
    if not (root / ".git").exists():
        return ""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    return result.stdout.strip()


def _read_only_tree_snapshot(root_path: str | None) -> str | None:
    if not root_path:
        return None
    root = Path(root_path)
    if not root.exists():
        return None
    if (root / ".git").exists():
        # Git metadata provides a compact mutation proof without hashing every tracked file.
        return _git_worktree_snapshot(root)

    entries: list[str] = []
    for path in sorted(root.rglob("*")):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if ".git" in relative.parts or path.is_dir():
            continue
        entries.append(_tree_snapshot_entry(path, relative))
    return "\n".join(entries)


def _git_worktree_snapshot(root: Path) -> str:
    parts = [
        "status\n" + (_git_porcelain(str(root)) or ""),
        "diff\n" + _git_output(root, ["diff", "--no-ext-diff", "--binary"]),
        "cached\n" + _git_output(root, ["diff", "--cached", "--no-ext-diff", "--binary"]),
    ]
    untracked = _git_output(root, ["ls-files", "--others", "--exclude-standard", "-z"])
    entries = []
    for name in sorted(path for path in untracked.split("\0") if path):
        path = root / name
        if path.is_file():
            entries.append(_tree_snapshot_entry(path, Path(name)))
    if entries:
        parts.append("untracked\n" + "\n".join(entries))
    return "\n".join(parts)


def _git_output(root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    return result.stdout if result.returncode == 0 else ""


def _tree_snapshot_entry(path: Path, relative: Path) -> str:
    try:
        stat = path.stat()
    except OSError:
        return f"{relative.as_posix()} <missing>"
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        digest.update(b"<unreadable>")
    return f"{relative.as_posix()} {stat.st_size} {digest.hexdigest()}"


def _read_only_report_metadata(task: dict[str, Any]) -> dict[str, Any]:
    profile = (task.get("metadata") or {}).get("project_profile") or {}
    return {
        "session_report": {
            "language": profile.get("language_hints", []),
            # Descriptive project context, so the detected command still shows before
            # the operator has confirmed it for execution.
            "test_command": profile.get("test_command") or profile.get("test_command_suggested"),
            "run_command": profile.get("run_command"),
            "top_level_structure": profile.get("top_level_folders", []),
            "relevant_docs": profile.get("relevant_docs", []),
        }
    }


def _git_rev(root: Path, ref: str) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", ref],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _git_merge_base(root: Path, a: str, b: str) -> str | None:
    result = subprocess.run(
        ["git", "merge-base", a, b],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _fast_forward_base(root: Path, base_branch: str, commit_sha: str) -> tuple[bool, str | None]:
    base_sha = _git_rev(root, base_branch)
    if base_sha is None:
        return False, f"base branch '{base_branch}' does not exist"
    merge_base = _git_merge_base(root, base_branch, commit_sha)
    if merge_base != base_sha:
        return False, f"base branch '{base_branch}' has diverged; manual integration required"
    result = subprocess.run(
        ["git", "checkout", base_branch],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if result.returncode != 0:
        return False, _safe_text(result.stderr or result.stdout)
    result = subprocess.run(
        ["git", "merge", "--ff-only", commit_sha],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if result.returncode != 0:
        # Restore the commit on the task branch and leave the task branch intact.
        subprocess.run(["git", "checkout", commit_sha], cwd=str(root), capture_output=True, check=False, timeout=10)
        return False, f"base branch '{base_branch}' could not fast-forward: {_safe_text(result.stderr or result.stdout)}"
    return True, None


def _safe_text(value: str, *, limit: int = 500) -> str:
    safe = redact_native_cli_text(SESSION_KEY_PATTERN.sub("***REDACTED***", value))
    for pattern in SECRETISH_PATTERNS:
        safe = pattern.sub("***REDACTED***", safe)
    return safe[:limit]
