from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from foreman_ai_hq.adapter_readiness import evaluate_adapter_readiness
from foreman_ai_hq.native_usage import token_usage_components
from foreman_ai_hq.task_kind import read_task_kind
from foreman_ai_hq.worker_model_allowlist import SEEDED_WORKER_ADAPTER_MODELS

SCHEMA = """
create table if not exists sessions (
    id text primary key,
    task_description text not null,
    model text not null,
    session_key_hash text not null,
    started_at text not null,
    status text not null,
    guardrail_overrides_json text not null
);

create table if not exists tasks (
    id text primary key,
    description text not null,
    status text not null,
    estimate_tokens integer,
    recommended_model text,
    actual_tokens integer,
    session_id text references sessions(id) on delete set null,
    metadata_json text not null default '{}',
    created_at text not null
);

create table if not exists worker_runs (
    id text primary key,
    task_id text not null references tasks(id) on delete cascade,
    session_id text not null references sessions(id) on delete cascade,
    adapter_id text not null,
    model text not null,
    tracking_mode text not null,
    status text not null,
    command_plan_json text not null,
    metadata_json text not null default '{}',
    stdout text not null default '',
    stderr text not null default '',
    returncode integer,
    error_type text,
    error_message text,
    created_at text not null,
    started_at text,
    completed_at text
);

create index if not exists idx_worker_runs_task_status on worker_runs(task_id, status);
create index if not exists idx_worker_runs_session on worker_runs(session_id);

create table if not exists worker_run_events (
    id integer primary key autoincrement,
    worker_run_id text not null references worker_runs(id) on delete cascade,
    session_id text not null references sessions(id) on delete cascade,
    task_id text not null references tasks(id) on delete cascade,
    layer text not null default 'control_plane',
    kind text not null,
    level text not null,
    title text not null,
    detail_json text not null default '{}',
    created_at text not null
);
create index if not exists idx_worker_run_events_run on worker_run_events(worker_run_id, created_at, id);
create index if not exists idx_worker_run_events_session on worker_run_events(session_id, created_at, id);

create table if not exists token_turns (
    id integer primary key autoincrement,
    session_id text not null references sessions(id) on delete cascade,
    usage_kind text not null default 'worker',
    model text not null,
    prompt_tokens integer not null,
    completion_tokens integer not null,
    total_tokens integer not null,
    cost real,
    raw_usage_json text not null,
    created_at text not null
);

create table if not exists tool_traces (
    id integer primary key autoincrement,
    session_id text not null references sessions(id) on delete cascade,
    tool_name text not null,
    input_hash text not null,
    duration_ms integer,
    metadata_json text not null default '{}',
    created_at text not null
);

create table if not exists alarms (
    id text primary key,
    session_id text not null references sessions(id) on delete cascade,
    type text not null,
    severity text not null,
    context_json text not null,
    recommended_action text not null,
    resolved_at text,
    created_at text not null
);

create table if not exists guardrail_snapshots (
    id integer primary key autoincrement,
    session_id text not null references sessions(id) on delete cascade,
    zone text not null,
    decision_json text not null,
    created_at text not null
);

create table if not exists checkpoint_results (
    id integer primary key autoincrement,
    session_id text not null references sessions(id) on delete cascade,
    name text not null,
    passed integer not null,
    details_json text not null,
    created_at text not null
);

create table if not exists action_history (
    id integer primary key autoincrement,
    session_id text references sessions(id) on delete cascade,
    alarm_id text references alarms(id) on delete set null,
    action text not null,
    payload_json text not null default '{}',
    created_at text not null
);

create table if not exists worker_adapters (
    id text primary key,
    kind text not null,
    name text not null,
    workdir text,
    config_json text not null default '{}',
    supported_models_json text not null default '[]',
    is_default integer not null default 0,
    verification_status text not null default 'unverified',
    verification_evidence_json text not null default '{}',
    verified_at text,
    created_at text not null,
    updated_at text not null
);

create table if not exists connected_projects (
    id text primary key,
    name text not null,
    root_path text not null unique,
    profile_json text not null default '{}',
    capability_json text not null default '{}',
    backend_id text not null default 'local_runner',
    archived_at text,
    archived_by text,
    created_at text not null,
    updated_at text not null
);

create table if not exists execution_backend_status (
    id text primary key,
    name text not null,
    online integer not null default 0,
    details_json text not null default '{}',
    checked_at text not null
);

create table if not exists portal_settings (
    key text primary key,
    value_json text not null,
    updated_at text not null
);
"""

WORKER_ADAPTER_PRESETS = [
    {
        "id": "claude_code",
        "kind": "claude_code",
        "name": "Claude Code",
        "config": {"verification_template": ["claude", "-p", "{prompt}"], "launch_template": ["claude"]},
        "supported_models": list(SEEDED_WORKER_ADAPTER_MODELS["claude_code"]),
    },
    {
        "id": "codex",
        "kind": "codex",
        "name": "Codex",
        "config": {"verification_template": ["codex", "--prompt", "{prompt}"], "launch_template": ["codex"]},
        "supported_models": list(SEEDED_WORKER_ADAPTER_MODELS["codex"]),
    },
    {
        "id": "opencode",
        "kind": "opencode",
        "name": "OpenCode",
        "config": {
            "verification_template": ["opencode", "run", "--model", "{model}", "--format", "json", "{prompt}"],
            "launch_template": ["opencode", "run", "--model", "{model}", "--format", "json", "{prompt}"],
            "launch_timeout_seconds": 600,
        },
        "supported_models": list(SEEDED_WORKER_ADAPTER_MODELS["opencode"]),
    },
]


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma foreign_keys = on")
    return conn


def init_db(path: Path | str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        _migrate_schema(conn)
        _seed_worker_adapters(conn)


def _migrate_schema(conn: sqlite3.Connection) -> None:
    # Preserve existing local harness history while bringing older tables to the current schema.
    token_turn_columns = {
        row["name"]: row for row in conn.execute("pragma table_info(token_turns)").fetchall()
    }
    if "usage_kind" not in token_turn_columns:
        conn.execute("alter table token_turns add column usage_kind text not null default 'worker'")
        token_turn_columns = {
            row["name"]: row for row in conn.execute("pragma table_info(token_turns)").fetchall()
        }
    if token_turn_columns["cost"]["notnull"]:
        conn.execute("alter table token_turns rename to token_turns_cost_not_null")
        conn.execute(
            """
            create table token_turns (
                id integer primary key autoincrement,
                session_id text not null references sessions(id) on delete cascade,
                usage_kind text not null default 'worker',
                model text not null,
                prompt_tokens integer not null,
                completion_tokens integer not null,
                total_tokens integer not null,
                cost real,
                raw_usage_json text not null,
                created_at text not null
            )
            """
        )
        conn.execute(
            """
            insert into token_turns (
                id, session_id, usage_kind, model, prompt_tokens, completion_tokens,
                total_tokens, cost, raw_usage_json, created_at
            )
            select
                id, session_id, usage_kind, model, prompt_tokens, completion_tokens,
                total_tokens, cost, raw_usage_json, created_at
            from token_turns_cost_not_null
            """
        )
        conn.execute("drop table token_turns_cost_not_null")

    worker_adapter_tables = {
        row["name"]
        for row in conn.execute(
            "select name from sqlite_master where type = 'table' and name = 'worker_adapters'"
        ).fetchall()
    }
    if "worker_adapters" not in worker_adapter_tables:
        conn.execute(
            """
            create table worker_adapters (
                id text primary key,
                kind text not null,
                name text not null,
                workdir text,
                config_json text not null default '{}',
                supported_models_json text not null default '[]',
                is_default integer not null default 0,
                verification_status text not null default 'unverified',
                verification_evidence_json text not null default '{}',
                verified_at text,
                created_at text not null,
                updated_at text not null
            )
            """
        )

    existing_tables = {
        row["name"]
        for row in conn.execute("select name from sqlite_master where type = 'table'").fetchall()
    }
    if "worker_run_events" in existing_tables:
        worker_run_event_columns = {
            row["name"] for row in conn.execute("pragma table_info(worker_run_events)").fetchall()
        }
        if "layer" not in worker_run_event_columns:
            conn.execute("alter table worker_run_events add column layer text not null default 'control_plane'")
    if "connected_projects" not in existing_tables:
        conn.execute(
            """
            create table connected_projects (
                id text primary key,
                name text not null,
                root_path text not null unique,
                profile_json text not null default '{}',
                capability_json text not null default '{}',
                backend_id text not null default 'local_runner',
                archived_at text,
                archived_by text,
                created_at text not null,
                updated_at text not null
            )
            """
        )
    else:
        connected_project_columns = {
            row["name"] for row in conn.execute("pragma table_info(connected_projects)").fetchall()
        }
        if "archived_at" not in connected_project_columns:
            conn.execute("alter table connected_projects add column archived_at text")
        if "archived_by" not in connected_project_columns:
            conn.execute("alter table connected_projects add column archived_by text")
    if "execution_backend_status" not in existing_tables:
        conn.execute(
            """
            create table execution_backend_status (
                id text primary key,
                name text not null,
                online integer not null default 0,
                details_json text not null default '{}',
                checked_at text not null
            )
            """
        )
    if "portal_settings" not in existing_tables:
        conn.execute(
            """
            create table portal_settings (
                key text primary key,
                value_json text not null,
                updated_at text not null
            )
            """
        )
    if "worker_runs" not in existing_tables:
        conn.execute(
            """
            create table worker_runs (
                id text primary key,
                task_id text not null references tasks(id) on delete cascade,
                session_id text not null references sessions(id) on delete cascade,
                adapter_id text not null,
                model text not null,
                tracking_mode text not null,
                status text not null,
                command_plan_json text not null,
                metadata_json text not null default '{}',
                stdout text not null default '',
                stderr text not null default '',
                returncode integer,
                error_type text,
                error_message text,
                created_at text not null,
                started_at text,
                completed_at text
            )
            """
        )
    if "task_breakdowns" not in existing_tables:
        conn.execute(
            """
            create table task_breakdowns (
                id text primary key,
                source_text text not null,
                source_sha256 text not null,
                intake_metadata_json text not null default '{}',
                status text not null,
                decision text not null,
                model text not null,
                session_id text references sessions(id) on delete set null,
                candidates_json text not null default '[]',
                rejected_items_json text not null default '[]',
                global_contract_summary text not null default '',
                global_constraints_json text not null default '[]',
                verification_json text not null default '[]',
                non_goals_json text not null default '[]',
                recommended_sequence_json text not null default '[]',
                repo_context_evidence_json text not null default '{}',
                confidence real,
                rationale text not null default '',
                failure_type text,
                failure_message text,
                created_task_ids_json text not null default '[]',
                revision integer not null default 0,
                created_at text not null,
                updated_at text not null
            )
            """
        )
    else:
        task_breakdown_columns = {
            row["name"] for row in conn.execute("pragma table_info(task_breakdowns)").fetchall()
        }
        if "global_contract_summary" not in task_breakdown_columns:
            conn.execute("alter table task_breakdowns add column global_contract_summary text not null default ''")
        if "repo_context_evidence_json" not in task_breakdown_columns:
            conn.execute("alter table task_breakdowns add column repo_context_evidence_json text not null default '{}'")
        if "revision" not in task_breakdown_columns:
            conn.execute("alter table task_breakdowns add column revision integer not null default 0")
    conn.execute("create index if not exists idx_worker_runs_task_status on worker_runs(task_id, status)")
    conn.execute("create index if not exists idx_worker_runs_session on worker_runs(session_id)")
    conn.execute("create index if not exists idx_task_breakdowns_status on task_breakdowns(status, created_at)")
    # "Ready" was renamed to "Estimated"; normalize old rows at startup instead of branching everywhere.
    conn.execute("update tasks set status = 'Estimated' where status = 'Ready'")
    # Blocked is a condition on a lifecycle state, not a lifecycle state itself.
    for row in conn.execute(
        "select id, estimate_tokens, metadata_json from tasks where status = 'Blocked'"
    ).fetchall():
        metadata = _from_json(row["metadata_json"])
        reason = (
            "manual estimate required"
            if row["estimate_tokens"] is None
            else metadata.get("blocked_reason")
            or metadata.get("launch_blocked_reason")
            or "Task requires operator attention."
        )
        metadata = _with_blocked_condition(metadata, reason=reason, origin="migration")
        if row["estimate_tokens"] is None:
            metadata["requires_manual_estimate"] = True
        conn.execute(
            "update tasks set status = 'Estimated', metadata_json = ? where id = ?",
            (_to_json(metadata), row["id"]),
        )
    if conn.execute("select 1 from tasks where status = 'Blocked' limit 1").fetchone():
        raise RuntimeError("Blocked task status migration failed")


def _seed_worker_adapters(conn: sqlite3.Connection) -> None:
    now = _now_iso()
    # The deprecated Hermes adapter is removed while user edits to supported presets are preserved.
    conn.execute("delete from worker_adapters where id = ?", ("hermes",))
    for preset in WORKER_ADAPTER_PRESETS:
        conn.execute(
            """
            insert into worker_adapters (
                id, kind, name, config_json, supported_models_json, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?)
            on conflict(id) do update set
                kind = excluded.kind,
                name = excluded.name
            """,
            (
                preset["id"],
                preset["kind"],
                preset["name"],
                _to_json(preset["config"]),
                json.dumps(preset["supported_models"], sort_keys=True, separators=(",", ":")),
                now,
                now,
            ),
        )


def create_session(
    path: Path | str,
    *,
    task_description: str,
    model: str,
    session_key_hash: str,
    guardrail_overrides: dict[str, Any],
    status: str = "running",
    session_kind: str | None = None,
) -> dict[str, Any]:
    session_id = f"sess_{uuid.uuid4().hex}"
    started_at = _now_iso()
    guardrail_overrides = dict(guardrail_overrides)
    if session_kind is not None:
        guardrail_overrides["session_kind"] = session_kind
    with connect(path) as conn:
        conn.execute(
            """
            insert into sessions (
                id, task_description, model, session_key_hash, started_at, status, guardrail_overrides_json
            ) values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                task_description,
                model,
                session_key_hash,
                started_at,
                status,
                _to_json(guardrail_overrides),
            ),
        )
    return get_session(path, session_id)


def create_planning_session(
    path: Path | str,
    *,
    task_description: str,
    model: str,
) -> tuple[dict[str, Any], str]:
    """Create a planning-kind metering-anchor session and return (session, bearer_key)."""
    bearer_key = f"sk_plan_{uuid.uuid4().hex}"
    session = create_session(
        path,
        task_description=task_description,
        model=model,
        session_key_hash=hashlib.sha256(bearer_key.encode("utf-8")).hexdigest(),
        guardrail_overrides={},
        status="running",
        session_kind="planning",
    )
    return session, bearer_key


def get_session(path: Path | str, session_id: str) -> dict[str, Any]:
    with connect(path) as conn:
        row = conn.execute("select * from sessions where id = ?", (session_id,)).fetchone()
    if row is None:
        raise KeyError(f"session not found: {session_id}")
    return _session_from_row(row)


def get_session_by_key_hash(path: Path | str, session_key_hash: str) -> dict[str, Any]:
    with connect(path) as conn:
        row = conn.execute(
            "select * from sessions where session_key_hash = ?", (session_key_hash,)
        ).fetchone()
    if row is None:
        raise KeyError("session not found for key")
    return _session_from_row(row)


def update_session_status(path: Path | str, session_id: str, status: str) -> dict[str, Any]:
    with connect(path) as conn:
        cursor = conn.execute("update sessions set status = ? where id = ?", (status, session_id))
        if cursor.rowcount == 0:
            raise KeyError(f"session not found: {session_id}")
    return get_session(path, session_id)


def record_token_turn(
    path: Path | str,
    *,
    session_id: str,
    usage_kind: str = "worker",
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost: float | None,
    raw_usage: dict[str, Any],
) -> None:
    raw_usage = _classified_raw_usage(usage_kind, raw_usage)
    total_tokens = int(raw_usage.get("total_tokens", prompt_tokens + completion_tokens))
    with connect(path) as conn:
        conn.execute(
            """
            insert into token_turns (
                session_id, usage_kind, model, prompt_tokens, completion_tokens,
                total_tokens, cost, raw_usage_json, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                usage_kind,
                model,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                cost,
                _to_json(raw_usage),
                _now_iso(),
            ),
        )


def record_tool_trace(
    path: Path | str,
    *,
    session_id: str,
    tool_name: str,
    input_hash: str,
    duration_ms: int | None,
    metadata: dict[str, Any],
) -> None:
    with connect(path) as conn:
        conn.execute(
            """
            insert into tool_traces (session_id, tool_name, input_hash, duration_ms, metadata_json, created_at)
            values (?, ?, ?, ?, ?, ?)
            """,
            (session_id, tool_name, input_hash, duration_ms, _to_json(metadata), _now_iso()),
        )


def record_guardrail_snapshot(
    path: Path | str,
    *,
    session_id: str,
    zone: str,
    decision: dict[str, Any],
) -> None:
    with connect(path) as conn:
        conn.execute(
            """
            insert into guardrail_snapshots (session_id, zone, decision_json, created_at)
            values (?, ?, ?, ?)
            """,
            (session_id, zone, _to_json(decision), _now_iso()),
        )


def record_alarm(path: Path | str, *, session_id: str, alarm: dict[str, Any]) -> None:
    with connect(path) as conn:
        conn.execute(
            """
            insert into alarms (id, session_id, type, severity, context_json, recommended_action, created_at)
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alarm["id"],
                session_id,
                alarm["type"],
                alarm["severity"],
                _to_json(alarm.get("context", {})),
                alarm["recommended_action"],
                _now_iso(),
            ),
        )


def record_checkpoint_result(
    path: Path | str,
    *,
    session_id: str,
    checkpoint: dict[str, Any],
) -> None:
    with connect(path) as conn:
        conn.execute(
            """
            insert into checkpoint_results (session_id, name, passed, details_json, created_at)
            values (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                checkpoint["name"],
                1 if checkpoint["passed"] else 0,
                _to_json(checkpoint.get("details", {})),
                _now_iso(),
            ),
        )


def create_task(
    path: Path | str,
    *,
    task_id: str | None = None,
    description: str,
    status: str = "Blocked",
    estimate_tokens: int | None = None,
    recommended_model: str | None = None,
    actual_tokens: int | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    idempotent = task_id is not None
    task_id = task_id or f"task_{uuid.uuid4().hex}"
    metadata = dict(metadata or {})
    if status == "Ready":
        status = "Estimated"
    if status == "Blocked":
        status = "Estimated"
        metadata = _with_blocked_condition(
            metadata,
            reason=metadata.get("blocked_reason")
            or metadata.get("launch_blocked_reason")
            or "manual estimate required",
            origin="task_create",
        )
        if estimate_tokens is None:
            metadata.setdefault("requires_manual_estimate", True)
    with connect(path) as conn:
        statement = """
            insert into tasks (
                id, description, status, estimate_tokens, recommended_model,
                actual_tokens, session_id, metadata_json, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        if idempotent:
            statement = statement.replace("insert into", "insert or ignore into", 1)
        conn.execute(
            statement,
            (
                task_id,
                description,
                status,
                estimate_tokens,
                recommended_model,
                actual_tokens,
                session_id,
                _to_json(metadata),
                _now_iso(),
            ),
        )
    return get_task(path, task_id)


def create_task_breakdown(
    path: Path | str,
    *,
    source_text: str,
    source_sha256: str,
    intake_metadata: dict[str, Any],
    status: str,
    decision: str,
    model: str,
    session_id: str | None = None,
    candidates: list[dict[str, Any]] | None = None,
    rejected_items: list[dict[str, Any]] | None = None,
    global_contract_summary: str = "",
    global_constraints: list[str] | None = None,
    verification: list[str] | None = None,
    non_goals: list[str] | None = None,
    recommended_sequence: list[str] | None = None,
    repo_context_evidence: dict[str, Any] | None = None,
    confidence: float | None = None,
    rationale: str = "",
    failure_type: str | None = None,
    failure_message: str | None = None,
) -> dict[str, Any]:
    breakdown_id = f"bd_{uuid.uuid4().hex}"
    now = _now_iso()
    with connect(path) as conn:
        conn.execute(
            """
            insert into task_breakdowns (
                id, source_text, source_sha256, intake_metadata_json, status, decision, model, session_id,
                candidates_json, rejected_items_json, global_contract_summary, global_constraints_json, verification_json,
                non_goals_json, recommended_sequence_json, repo_context_evidence_json, confidence, rationale, failure_type,
                failure_message, created_task_ids_json, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                breakdown_id,
                source_text,
                source_sha256,
                _to_json(intake_metadata),
                status,
                decision,
                model,
                session_id,
                _to_json_list(candidates or []),
                _to_json_list(rejected_items or []),
                global_contract_summary,
                _to_json_list(global_constraints or []),
                _to_json_list(verification or []),
                _to_json_list(non_goals or []),
                _to_json_list(recommended_sequence or []),
                _to_json(repo_context_evidence or {}),
                confidence,
                rationale,
                failure_type,
                failure_message,
                _to_json_list([]),
                now,
                now,
            ),
        )
    return get_task_breakdown(path, breakdown_id)


def get_task_breakdown(path: Path | str, breakdown_id: str) -> dict[str, Any]:
    with connect(path) as conn:
        row = conn.execute("select * from task_breakdowns where id = ?", (breakdown_id,)).fetchone()
    if row is None:
        raise KeyError(f"task breakdown not found: {breakdown_id}")
    return _task_breakdown_from_row(row)


def list_task_breakdowns_for_project(
    path: Path | str, project_id: str
) -> list[dict[str, Any]]:
    with connect(path) as conn:
        rows = conn.execute(
            """
            select * from task_breakdowns
            where status in ('proposed', 'pending_review', 'failed')
            order by created_at desc, id desc
            """
        ).fetchall()
    return [
        breakdown
        for row in rows
        if (breakdown := _task_breakdown_from_row(row)).get("intake_metadata", {}).get(
            "connected_project_id"
        )
        == project_id
    ]


def update_task_breakdown(
    path: Path | str,
    breakdown_id: str,
    updates: dict[str, Any],
    *,
    expected_statuses: set[str] | None = None,
    expected_revision: int | None = None,
) -> dict[str, Any] | None:
    # Whitelist updateable fields before building SQL column assignments.
    allowed = {
        "status": "status",
        "decision": "decision",
        "model": "model",
        "session_id": "session_id",
        "candidates": "candidates_json",
        "rejected_items": "rejected_items_json",
        "global_contract_summary": "global_contract_summary",
        "global_constraints": "global_constraints_json",
        "verification": "verification_json",
        "non_goals": "non_goals_json",
        "recommended_sequence": "recommended_sequence_json",
        "repo_context_evidence": "repo_context_evidence_json",
        "confidence": "confidence",
        "rationale": "rationale",
        "failure_type": "failure_type",
        "failure_message": "failure_message",
        "created_task_ids": "created_task_ids_json",
    }
    json_list_fields = {
        "candidates",
        "rejected_items",
        "global_constraints",
        "verification",
        "non_goals",
        "recommended_sequence",
        "created_task_ids",
    }
    json_object_fields = {"repo_context_evidence"}
    assignments: list[str] = []
    values: list[Any] = []
    for key, value in updates.items():
        if key not in allowed:
            continue
        assignments.append(f"{allowed[key]} = ?")
        if key in json_list_fields:
            values.append(_to_json_list(value))
        elif key in json_object_fields:
            values.append(_to_json(value or {}))
        else:
            values.append(value)
    if not assignments:
        return get_task_breakdown(path, breakdown_id)
    assignments.extend(["revision = revision + 1", "updated_at = ?"])
    values.append(_now_iso())
    predicates = ["id = ?"]
    predicate_values: list[Any] = [breakdown_id]
    if expected_statuses is not None:
        if not expected_statuses:
            return None
        placeholders = ", ".join("?" for _ in expected_statuses)
        predicates.append(f"status in ({placeholders})")
        predicate_values.extend(sorted(expected_statuses))
    if expected_revision is not None:
        predicates.append("revision = ?")
        predicate_values.append(expected_revision)
    with connect(path) as conn:
        cursor = conn.execute(
            f"update task_breakdowns set {', '.join(assignments)} where {' and '.join(predicates)}",
            (*values, *predicate_values),
        )
        if cursor.rowcount == 0:
            if expected_statuses is not None or expected_revision is not None:
                return None
            raise KeyError(f"task breakdown not found: {breakdown_id}")
    return get_task_breakdown(path, breakdown_id)


def get_task(path: Path | str, task_id: str) -> dict[str, Any]:
    with connect(path) as conn:
        row = conn.execute("select * from tasks where id = ?", (task_id,)).fetchone()
    if row is None:
        raise KeyError(f"task not found: {task_id}")
    return _task_from_row(row)


def update_task(path: Path | str, task_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    updates = dict(updates)
    if updates.get("status") == "Blocked":
        current = get_task(path, task_id)
        metadata = {**current.get("metadata", {}), **dict(updates.get("metadata") or {})}
        updates["status"] = (
            "Review" if current.get("status") in {"Running", "Review"} else "Estimated"
        )
        updates["metadata"] = _with_blocked_condition(
            metadata,
            reason=metadata.get("blocked_reason")
            or metadata.get("launch_blocked_reason")
            or "Task requires operator attention.",
            origin="task_update",
        )
    allowed = {
        "description": "description",
        "status": "status",
        "estimate_tokens": "estimate_tokens",
        "recommended_model": "recommended_model",
        "actual_tokens": "actual_tokens",
        "session_id": "session_id",
        "metadata": "metadata_json",
    }
    assignments: list[str] = []
    values: list[Any] = []
    for key, value in updates.items():
        if key not in allowed or value is None:
            continue
        if key == "status" and value == "Ready":
            value = "Estimated"
        assignments.append(f"{allowed[key]} = ?")
        values.append(_to_json(value) if key == "metadata" else value)
    if not assignments:
        return get_task(path, task_id)

    with connect(path) as conn:
        cursor = conn.execute(
            f"update tasks set {', '.join(assignments)} where id = ?",
            (*values, task_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(f"task not found: {task_id}")
    return get_task(path, task_id)


def _with_blocked_condition(
    metadata: dict[str, Any],
    *,
    reason: str,
    origin: str,
    timestamp: str | None = None,
) -> dict[str, Any]:
    updated = dict(metadata)
    existing = updated.get("blocked_condition")
    condition = dict(existing) if isinstance(existing, dict) else {}
    condition.update(
        {
            "reason": str(reason),
            "origin": str(condition.get("origin") or origin),
            "timestamp": str(condition.get("timestamp") or timestamp or _now_iso()),
        }
    )
    updated["blocked_condition"] = condition
    return updated


def update_task_metadata(
    path: Path | str,
    task_id: str,
    updater: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    with connect(path) as conn:
        # Serialize task metadata read-modify-write updates so background Worker
        # completion and queue-event recording cannot clobber each other.
        conn.execute("begin immediate")
        row = conn.execute("select metadata_json from tasks where id = ?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(f"task not found: {task_id}")
        current = _from_json(row["metadata_json"])
        updated = updater(dict(current or {}))
        conn.execute(
            "update tasks set metadata_json = ? where id = ?",
            (_to_json(updated), task_id),
        )
    return get_task(path, task_id)


def task_is_archived(task: dict[str, Any]) -> bool:
    return bool((task.get("metadata") or {}).get("archived_at"))


def _task_is_dismissible(task: dict[str, Any]) -> bool:
    """Whether a task can be archived/dismissed off the board.

    Done and Estimated tasks are terminal or pre-launch and always dismissible.
    A failed/aborted/guardrail-blocked run now lands in Review carrying a
    ``blocked_condition`` (Blocked is a condition, not a lifecycle state); that
    condition has no other disposition path, so it must be dismissible too —
    otherwise the task is stranded in Review with no controls.
    """
    status = task.get("status")
    if status in {"Done", "Estimated"}:
        return True
    return status == "Review" and bool((task.get("metadata") or {}).get("blocked_condition"))


def archive_task(path: Path | str, task_id: str) -> dict[str, Any]:
    task = get_task(path, task_id)
    if not _task_is_dismissible(task):
        raise ValueError(
            "Only Done, Estimated, or blocked Review tasks can be archived or dismissed."
        )
    metadata = {**task.get("metadata", {})}
    if metadata.get("archived_at"):
        return task
    metadata["archived_at"] = _now_iso()
    metadata["archived_by"] = "operator"
    return update_task(path, task_id, {"metadata": metadata})


def unarchive_task(path: Path | str, task_id: str) -> dict[str, Any]:
    task = get_task(path, task_id)
    metadata = {**task.get("metadata", {})}
    metadata.pop("archived_at", None)
    metadata.pop("archived_by", None)
    return update_task(path, task_id, {"metadata": metadata})


def archive_done_tasks_for_project(path: Path | str, project_id: str) -> list[dict[str, Any]]:
    now = _now_iso()
    archived_ids: list[str] = []
    with connect(path) as conn:
        rows = conn.execute("select * from tasks where status = 'Done' order by created_at, id").fetchall()
        for row in rows:
            task = _task_from_row(row)
            metadata = {**task.get("metadata", {})}
            if str(metadata.get("connected_project_id") or "") != str(project_id):
                continue
            if metadata.get("archived_at"):
                continue
            metadata["archived_at"] = now
            metadata["archived_by"] = "operator"
            conn.execute(
                "update tasks set metadata_json = ? where id = ?",
                (_to_json(metadata), task["id"]),
            )
            archived_ids.append(task["id"])
    return [get_task(path, task_id) for task_id in archived_ids]


def claim_task_agent_review(path: Path | str, task_id: str, claim: dict[str, Any]) -> dict[str, Any] | None:
    """Atomically set an in-progress Agent Review marker if none exists.

    Returns the claimed task, or None when another request already claimed or
    completed review metadata for the task.
    """
    with connect(path) as conn:
        row = conn.execute("select * from tasks where id = ?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(f"task not found: {task_id}")
        task = _task_from_row(row)
        metadata = {**task.get("metadata", {})}
        if metadata.get("agent_review"):
            return None
        metadata["agent_review"] = _sanitize_evidence(claim)
        cursor = conn.execute(
            "update tasks set metadata_json = ? where id = ? and status = 'Review' and metadata_json = ?",
            (_to_json(metadata), task_id, row["metadata_json"]),
        )
        if cursor.rowcount == 0:
            return None
    return get_task(path, task_id)


def mark_stale_worker_runs_interrupted(path: Path | str) -> list[dict[str, Any]]:
    now = _now_iso()
    interrupted: list[dict[str, Any]] = []
    current_pid = os.getpid()
    with connect(path) as conn:
        rows = conn.execute(
            "select * from worker_runs where status in ('queued', 'running') order by created_at, id"
        ).fetchall()
        for row in rows:
            run = _worker_run_from_row(row)
            metadata = run.get("metadata", {})
            owner_pid = metadata.get("executor_pid")
            # A missing/dead owner PID means the previous process died while the UI still showed Running.
            if owner_pid == current_pid or _pid_is_alive(owner_pid):
                continue
            metadata = {**metadata, "interrupted_reason": "Worker Run was interrupted before completion."}
            conn.execute(
                """
                update worker_runs
                set status = 'failed', error_type = 'interrupted', error_message = ?, metadata_json = ?, completed_at = ?
                where id = ?
                """,
                ("Worker Run was interrupted before completion.", _to_json(metadata), now, run["id"]),
            )
            conn.execute("update sessions set status = 'failed' where id = ?", (run["session_id"],))
            task_row = conn.execute("select * from tasks where id = ?", (run["task_id"],)).fetchone()
            if task_row is not None:
                task = _task_from_row(task_row)
                task_metadata = {
                    **task.get("metadata", {}),
                    "launch_error_type": "interrupted",
                    "launch_blocked_reason": "Worker Run was interrupted before completion.",
                    "launch_retryable": True,
                    "active_worker_run_id": run["id"],
                }
                if task.get("status") == "Running":
                    conn.execute(
                        "update tasks set status = 'Estimated', metadata_json = ? where id = ?",
                        (_to_json(task_metadata), run["task_id"]),
                    )
            interrupted.append({**run, "status": "failed", "error_type": "interrupted", "completed_at": now})
    return interrupted


def _pid_is_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def create_worker_run(
    path: Path | str,
    *,
    task_id: str,
    session_id: str,
    adapter_id: str,
    model: str,
    tracking_mode: str,
    command_plan: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    status: str = "running",
) -> dict[str, Any]:
    run_id = f"run_{uuid.uuid4().hex}"
    now = _now_iso()
    with connect(path) as conn:
        conn.execute(
            """
            insert into worker_runs (
                id, task_id, session_id, adapter_id, model, tracking_mode, status,
                command_plan_json, metadata_json, created_at, started_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                task_id,
                session_id,
                adapter_id,
                model,
                tracking_mode,
                status,
                _to_json(command_plan),
                _to_json({**(metadata or {}), "executor_pid": os.getpid()}),
                now,
                now if status == "running" else None,
            ),
        )
    return get_worker_run(path, run_id)


def get_worker_run(path: Path | str, run_id: str) -> dict[str, Any]:
    with connect(path) as conn:
        row = conn.execute("select * from worker_runs where id = ?", (run_id,)).fetchone()
    if row is None:
        raise KeyError(f"worker run not found: {run_id}")
    return _worker_run_from_row(row)


def update_worker_run_metadata(
    path: Path | str,
    run_id: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    existing = get_worker_run(path, run_id)
    merged_metadata = {**existing.get("metadata", {}), **metadata}
    with connect(path) as conn:
        cursor = conn.execute(
            "update worker_runs set metadata_json = ? where id = ?",
            (_to_json(_sanitize_evidence(merged_metadata)), run_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(f"worker run not found: {run_id}")
    return get_worker_run(path, run_id)


def get_active_worker_run_for_task(path: Path | str, task_id: str) -> dict[str, Any] | None:
    with connect(path) as conn:
        row = conn.execute(
            """
            select * from worker_runs
            where task_id = ? and status in ('queued', 'running')
            order by created_at desc, id desc
            limit 1
            """,
            (task_id,),
        ).fetchone()
    return _worker_run_from_row(row) if row is not None else None


def list_worker_runs(
    path: Path | str,
    *,
    task_id: str | None = None,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if task_id is not None:
        clauses.append("task_id = ?")
        params.append(task_id)
    if session_id is not None:
        clauses.append("session_id = ?")
        params.append(session_id)
    where = f" where {' and '.join(clauses)}" if clauses else ""
    with connect(path) as conn:
        rows = conn.execute("select * from worker_runs" + where + " order by created_at, id", params).fetchall()
    return [_worker_run_from_row(row) for row in rows]


def record_worker_run_event(
    path: Path | str,
    *,
    worker_run_id: str,
    session_id: str,
    task_id: str,
    kind: str,
    title: str,
    layer: str = "control_plane",
    level: str = "info",
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = _now_iso()
    with connect(path) as conn:
        cursor = conn.execute(
            """
            insert into worker_run_events (
                worker_run_id, session_id, task_id, layer, kind, level, title, detail_json, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                worker_run_id,
                session_id,
                task_id,
                layer,
                kind,
                level,
                title,
                _to_json(_sanitize_evidence(detail or {})),
                now,
            ),
        )
        row = conn.execute("select * from worker_run_events where id = ?", (cursor.lastrowid,)).fetchone()
    return _worker_run_event_from_row(row)


def list_worker_run_events(
    path: Path | str,
    *,
    worker_run_id: str | None = None,
    session_id: str | None = None,
    task_id: str | None = None,
    since_id: int | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if worker_run_id is not None:
        clauses.append("worker_run_id = ?")
        params.append(worker_run_id)
    if session_id is not None:
        clauses.append("session_id = ?")
        params.append(session_id)
    if task_id is not None:
        clauses.append("task_id = ?")
        params.append(task_id)
    if since_id is not None:
        clauses.append("id > ?")
        params.append(since_id)
    where = f" where {' and '.join(clauses)}" if clauses else ""
    query = "select * from worker_run_events" + where + " order by id"
    if limit is not None:
        query += " limit ?"
        params.append(limit)
    with connect(path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_worker_run_event_from_row(row) for row in rows]


def mark_worker_run_running(path: Path | str, run_id: str) -> dict[str, Any]:
    now = _now_iso()
    with connect(path) as conn:
        conn.execute(
            "update worker_runs set status = ?, started_at = coalesce(started_at, ?) where id = ?",
            ("running", now, run_id),
        )
    return get_worker_run(path, run_id)


def mark_worker_run_completed(
    path: Path | str,
    run_id: str,
    *,
    returncode: int,
    stdout: str = "",
    stderr: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _finish_worker_run(path, run_id, status="completed", returncode=returncode, stdout=stdout, stderr=stderr, metadata=metadata)


def mark_worker_run_failed(
    path: Path | str,
    run_id: str,
    *,
    error_type: str,
    error_message: str,
    returncode: int | None = None,
    stdout: str = "",
    stderr: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _finish_worker_run(
        path,
        run_id,
        status="failed",
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        error_type=error_type,
        error_message=error_message,
        metadata=metadata,
    )


def mark_worker_run_interrupted(
    path: Path | str,
    run_id: str,
    *,
    error_message: str = "Worker Run was interrupted before completion.",
) -> dict[str, Any]:
    return mark_worker_run_failed(path, run_id, error_type="interrupted", error_message=error_message)


def _finish_worker_run(
    path: Path | str,
    run_id: str,
    *,
    status: str,
    returncode: int | None,
    stdout: str,
    stderr: str,
    error_type: str | None = None,
    error_message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = _now_iso()
    existing = get_worker_run(path, run_id)
    merged_metadata = {**existing.get("metadata", {}), **(metadata or {})}
    with connect(path) as conn:
        conn.execute(
            """
            update worker_runs
            set status = ?, returncode = ?, stdout = ?, stderr = ?, error_type = ?,
                error_message = ?, metadata_json = ?, completed_at = ?
            where id = ?
            """,
            (
                status,
                returncode,
                _sanitize_evidence(stdout),
                _sanitize_evidence(stderr),
                error_type,
                error_message,
                _to_json(merged_metadata),
                now,
                run_id,
            ),
        )
        conn.execute(
            """
            insert into worker_run_events (
                worker_run_id, session_id, task_id, layer, kind, level, title, detail_json, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                existing["session_id"],
                existing["task_id"],
                "worker_harness",
                "adapter" if status == "completed" else "guardrail",
                "info" if status == "completed" else "error",
                "Worker Run completed" if status == "completed" else "Worker Run failed",
                _to_json(
                    _sanitize_evidence(
                        {
                            "status": status,
                            "returncode": returncode,
                            **({"error_type": error_type} if error_type else {}),
                            **({"error_message": error_message} if error_message else {}),
                        }
                    )
                ),
                now,
            ),
        )
    return get_worker_run(path, run_id)


def list_tasks(path: Path | str) -> list[dict[str, Any]]:
    with connect(path) as conn:
        rows = conn.execute("select * from tasks order by created_at, id").fetchall()
    return [_task_from_row(row) for row in rows]


def list_task_ids_for_breakdown(path: Path | str, breakdown_id: str) -> list[str]:
    return [
        task["id"]
        for task in list_tasks(path)
        if str((task.get("metadata") or {}).get("task_breakdown_id") or "") == breakdown_id
    ]


def read_session_kind(session: dict[str, Any]) -> str:
    """Canonical session-kind reader. Legacy and Worker sessions default to 'worker'."""
    return str((session.get("guardrail_overrides") or {}).get("session_kind") or "worker")


def list_sessions(path: Path | str, *, kind: str | None = "worker") -> list[dict[str, Any]]:
    with connect(path) as conn:
        rows = conn.execute("select * from sessions order by started_at, id").fetchall()
    sessions = [_session_from_row(row) for row in rows]
    if kind is not None:
        sessions = [session for session in sessions if read_session_kind(session) == kind]
    return sessions


def list_worker_adapters(path: Path | str) -> list[dict[str, Any]]:
    with connect(path) as conn:
        rows = conn.execute("select * from worker_adapters order by id").fetchall()
    return [_worker_adapter_from_row(row) for row in rows]


def get_worker_adapter(path: Path | str, adapter_id: str) -> dict[str, Any]:
    with connect(path) as conn:
        row = conn.execute("select * from worker_adapters where id = ?", (adapter_id,)).fetchone()
    if row is None:
        raise KeyError(f"worker adapter not found: {adapter_id}")
    return _worker_adapter_from_row(row)


def update_worker_adapter(
    path: Path | str,
    adapter_id: str,
    *,
    workdir: str | None = None,
    config: dict[str, Any] | None = None,
    supported_models: list[str] | None = None,
    is_default: bool | None = None,
) -> dict[str, Any]:
    updates: list[str] = []
    values: list[Any] = []
    if workdir is not None:
        updates.append("workdir = ?")
        values.append(workdir)
    if config is not None:
        updates.append("config_json = ?")
        values.append(_to_json(config))
    if supported_models is not None:
        updates.append("supported_models_json = ?")
        values.append(json.dumps(supported_models, sort_keys=True, separators=(",", ":")))
    if is_default is not None:
        updates.append("is_default = ?")
        values.append(1 if is_default else 0)
    updates.append("updated_at = ?")
    values.append(_now_iso())

    with connect(path) as conn:
        if is_default:
            conn.execute("update worker_adapters set is_default = 0 where id != ?", (adapter_id,))
        cursor = conn.execute(
            f"update worker_adapters set {', '.join(updates)} where id = ?", (*values, adapter_id)
        )
        if cursor.rowcount == 0:
            raise KeyError(f"worker adapter not found: {adapter_id}")
    return get_worker_adapter(path, adapter_id)


def mark_worker_adapter_verification(
    path: Path | str,
    adapter_id: str,
    *,
    verified: bool,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    now = _now_iso()
    sanitized_evidence = _sanitize_evidence(evidence)
    if verified:
        sanitized_evidence.setdefault("tracking_mode", "proxy_governed")
        sanitized_evidence.setdefault("tracking_authoritative", True)
    with connect(path) as conn:
        cursor = conn.execute(
            """
            update worker_adapters
            set verification_status = ?, verification_evidence_json = ?, verified_at = ?, updated_at = ?
            where id = ?
            """,
            (
                "verified" if verified else "failed",
                _to_json(sanitized_evidence),
                now if verified else None,
                now,
                adapter_id,
            ),
        )
        if cursor.rowcount == 0:
            raise KeyError(f"worker adapter not found: {adapter_id}")
    return get_worker_adapter(path, adapter_id)


def has_verified_worker_adapter(path: Path | str) -> bool:
    with connect(path) as conn:
        row = conn.execute(
            "select 1 from worker_adapters where verification_status = 'verified' limit 1"
        ).fetchone()
    return row is not None


def has_launchable_worker_adapter(path: Path | str) -> bool:
    return any(
        evaluate_adapter_readiness(adapter).launchable_tracking for adapter in list_worker_adapters(path)
    )


def has_adapter_verification_token(path: Path | str, *, session_id: str, model: str) -> bool:
    with connect(path) as conn:
        row = conn.execute(
            """
            select 1 from token_turns
            where session_id = ? and usage_kind = 'adapter_verification' and model = ?
            limit 1
            """,
            (session_id, model),
        ).fetchone()
    return row is not None


def upsert_connected_project(
    path: Path | str,
    *,
    name: str,
    root_path: str,
    profile: dict[str, Any],
    capability: dict[str, Any],
    backend_id: str = "local_runner",
) -> dict[str, Any]:
    now = _now_iso()
    project_id = f"proj_{uuid.uuid4().hex}"
    with connect(path) as conn:
        conn.execute(
            """
            insert into connected_projects (
                id, name, root_path, profile_json, capability_json, backend_id, archived_at, archived_by, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(root_path) do update set
                name = excluded.name,
                profile_json = excluded.profile_json,
                capability_json = excluded.capability_json,
                backend_id = excluded.backend_id,
                archived_at = null,
                archived_by = null,
                updated_at = excluded.updated_at
            """,
            (
                project_id,
                name,
                root_path,
                _to_json(profile),
                _to_json(capability),
                backend_id,
                None,
                None,
                now,
                now,
            ),
        )
    return get_connected_project_by_path(path, root_path)


def list_connected_projects(path: Path | str, *, include_archived: bool = False) -> list[dict[str, Any]]:
    with connect(path) as conn:
        where = "" if include_archived else "where archived_at is null"
        rows = conn.execute(f"select * from connected_projects {where} order by updated_at desc, id").fetchall()
    return [_connected_project_from_row(row) for row in rows]


def list_archived_connected_projects(path: Path | str) -> list[dict[str, Any]]:
    with connect(path) as conn:
        rows = conn.execute(
            "select * from connected_projects where archived_at is not null order by archived_at desc, updated_at desc, id"
        ).fetchall()
    return [_connected_project_from_row(row) for row in rows]


def project_is_archived(project: dict[str, Any]) -> bool:
    return bool(project.get("archived_at"))


def archive_connected_project(path: Path | str, project_id: str, *, archived_by: str = "operator") -> dict[str, Any]:
    now = _now_iso()
    with connect(path) as conn:
        cursor = conn.execute(
            """
            update connected_projects
            set archived_at = coalesce(archived_at, ?),
                archived_by = coalesce(archived_by, ?),
                updated_at = ?
            where id = ?
            """,
            (now, archived_by, now, project_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(f"connected project not found: {project_id}")
    return get_connected_project(path, project_id)


def restore_connected_project(path: Path | str, project_id: str) -> dict[str, Any]:
    now = _now_iso()
    with connect(path) as conn:
        cursor = conn.execute(
            """
            update connected_projects
            set archived_at = null,
                archived_by = null,
                updated_at = ?
            where id = ?
            """,
            (now, project_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(f"connected project not found: {project_id}")
    return get_connected_project(path, project_id)


def get_connected_project(path: Path | str, project_id: str) -> dict[str, Any]:
    with connect(path) as conn:
        row = conn.execute("select * from connected_projects where id = ?", (project_id,)).fetchone()
    if row is None:
        raise KeyError(f"connected project not found: {project_id}")
    return _connected_project_from_row(row)


def get_connected_project_by_path(path: Path | str, root_path: str) -> dict[str, Any]:
    with connect(path) as conn:
        row = conn.execute("select * from connected_projects where root_path = ?", (root_path,)).fetchone()
    if row is None:
        raise KeyError(f"connected project not found: {root_path}")
    return _connected_project_from_row(row)


def upsert_execution_backend_status(
    path: Path | str,
    backend_id: str,
    *,
    name: str,
    online: bool,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checked_at = _now_iso()
    with connect(path) as conn:
        conn.execute(
            """
            insert into execution_backend_status (id, name, online, details_json, checked_at)
            values (?, ?, ?, ?, ?)
            on conflict(id) do update set
                name = excluded.name,
                online = excluded.online,
                details_json = excluded.details_json,
                checked_at = excluded.checked_at
            """,
            (backend_id, name, 1 if online else 0, _to_json(details or {}), checked_at),
        )
    return get_execution_backend_status(path, backend_id)


def get_portal_setting(path: Path | str, key: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
    with connect(path) as conn:
        row = conn.execute("select value_json from portal_settings where key = ?", (key,)).fetchone()
    if row is None:
        return dict(default or {})
    return _from_json(row["value_json"])


def set_portal_setting(path: Path | str, key: str, value: dict[str, Any]) -> dict[str, Any]:
    now = _now_iso()
    with connect(path) as conn:
        conn.execute(
            """
            insert into portal_settings (key, value_json, updated_at)
            values (?, ?, ?)
            on conflict(key) do update set
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """,
            (key, _to_json(value), now),
        )
    return get_portal_setting(path, key)


def update_portal_setting(
    path: Path | str,
    key: str,
    default: dict[str, Any] | None,
    updater: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    now = _now_iso()
    with connect(path) as conn:
        # Serialize read-modify-write updates so two UI actions cannot lose each other's setting changes.
        conn.execute("begin immediate")
        row = conn.execute("select value_json from portal_settings where key = ?", (key,)).fetchone()
        current = _from_json(row["value_json"]) if row is not None else dict(default or {})
        updated = updater(current)
        conn.execute(
            """
            insert into portal_settings (key, value_json, updated_at)
            values (?, ?, ?)
            on conflict(key) do update set
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """,
            (key, _to_json(updated), now),
        )
        row = conn.execute("select value_json from portal_settings where key = ?", (key,)).fetchone()
    return _from_json(row["value_json"])


def get_token_budget_settings(path: Path | str) -> dict[str, Any]:
    return get_portal_setting(path, "token_budget", {})


def set_token_budget_settings(
    path: Path | str,
    *,
    daily_cap_tokens: int,
    session_cap_tokens: int,
) -> dict[str, Any]:
    existing = dict(get_token_budget_settings(path))
    existing.update(
        {
            "daily_cap_tokens": int(daily_cap_tokens),
            "session_cap_tokens": int(session_cap_tokens),
            "confirmed": True,
        }
    )
    return set_portal_setting(
        path,
        "token_budget",
        existing,
    )


def reset_daily_budget_counter(path: Path | str, *, reset_at: str | None = None) -> dict[str, Any]:
    reset_at_iso = _normalize_utc_iso(reset_at or _now_iso())

    def update(current: dict[str, Any]) -> dict[str, Any]:
        updated = dict(current or {})
        updated["daily_usage_reset_at"] = reset_at_iso
        return updated

    return update_portal_setting(path, "token_budget", {}, update)


def current_day_start_iso(timezone: str, *, now: datetime | None = None) -> str:
    if timezone == "local":
        current = (now or datetime.now().astimezone()).astimezone()
    else:
        try:
            zone = ZoneInfo(timezone)
        except Exception:
            zone = UTC
        current = (now or datetime.now(zone)).astimezone(zone)
    start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(UTC).isoformat()


def effective_daily_budget_window_start(
    path: Path | str,
    *,
    timezone: str = "local",
    now: datetime | None = None,
) -> str:
    day_start = _parse_iso_datetime(current_day_start_iso(timezone, now=now))
    reset_at = _parse_iso_datetime(get_token_budget_settings(path).get("daily_usage_reset_at"))
    # Manual resets later than midnight define the active daily budget window.
    if reset_at is not None and day_start is not None and reset_at >= day_start:
        return reset_at.isoformat()
    if day_start is None:  # defensive fallback; current_day_start_iso should always parse
        return current_day_start_iso(timezone, now=now)
    return day_start.isoformat()


def get_execution_backend_status(path: Path | str, backend_id: str) -> dict[str, Any]:
    with connect(path) as conn:
        row = conn.execute("select * from execution_backend_status where id = ?", (backend_id,)).fetchone()
    if row is None:
        raise KeyError(f"execution backend not found: {backend_id}")
    return _execution_backend_status_from_row(row)


def list_alarms(
    path: Path | str,
    *,
    session_id: str | None = None,
    alarm_type: str | None = None,
    severity: str | None = None,
    resolved: bool | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    if session_id is not None:
        clauses.append("session_id = ?")
        values.append(session_id)
    if alarm_type is not None:
        clauses.append("type = ?")
        values.append(alarm_type)
    if severity is not None:
        clauses.append("severity = ?")
        values.append(severity)
    if resolved is True:
        clauses.append("resolved_at is not null")
    elif resolved is False:
        clauses.append("resolved_at is null")
    where = f" where {' and '.join(clauses)}" if clauses else ""
    query = "select * from alarms" + where + " order by created_at, id"
    with connect(path) as conn:
        rows = conn.execute(query, values).fetchall()
    return [_alarm_from_row(row) for row in rows]


_BUDGET_ALARM_CAP_KEYS = {
    "DAILY_CAP_EXCEEDED": "daily_cap_tokens",
    "SESSION_CAP_EXCEEDED": "session_cap_tokens",
}


def available_actions_for_alarm(alarm: dict[str, Any]) -> list[dict[str, Any]]:
    """Backend-computed actions for an alarm; React never infers eligibility."""
    if alarm.get("resolved_at"):
        return []
    actions = [{"action": "continue"}]
    cap_key = _BUDGET_ALARM_CAP_KEYS.get(alarm.get("type", ""))
    if cap_key:
        context = alarm.get("context") or {}
        current_cap = context.get(cap_key)
        actions.append({"action": "raise_budget", "cap_key": cap_key, "current_cap": current_cap})
    return actions


def _validate_raise_budget(
    conn: sqlite3.Connection,
    session_id: str,
    payload: dict[str, Any],
) -> None:
    """Reject raise_budget values that are not strictly greater than current caps."""
    if not payload:
        raise ValueError("raise_budget requires a cap payload")
    row = conn.execute(
        "select guardrail_overrides_json from sessions where id = ?", (session_id,)
    ).fetchone()
    overrides = _from_json(row["guardrail_overrides_json"]) if row else {}
    current_budget = overrides.get("budget", {})
    for key, new_value in payload.items():
        if key not in ("daily_cap_tokens", "session_cap_tokens"):
            raise ValueError(f"{key} is not a raise_budget cap key")
        try:
            new_value = float(new_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"cap value for {key} must be numeric") from exc
        current_value = current_budget.get(key)
        try:
            current_value = float(current_value) if current_value is not None else 0
        except (TypeError, ValueError) as exc:
            raise ValueError(f"current cap for {key} is not numeric") from exc
        if new_value <= current_value:
            raise ValueError(
                f"raise_budget for {key} must be strictly greater than current cap {current_value}"
            )


def resolve_alarm(
    path: Path | str,
    *,
    alarm_id: str,
    action: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_at = _now_iso()
    with connect(path) as conn:
        alarm_row = conn.execute("select * from alarms where id = ?", (alarm_id,)).fetchone()
        if alarm_row is None:
            raise KeyError(f"alarm not found: {alarm_id}")
        if action == "raise_budget":
            _validate_raise_budget(conn, alarm_row["session_id"], payload or {})
        conn.execute("update alarms set resolved_at = ? where id = ?", (resolved_at, alarm_id))
        cursor = conn.execute(
            """
            insert into action_history (session_id, alarm_id, action, payload_json, created_at)
            values (?, ?, ?, ?, ?)
            """,
            (alarm_row["session_id"], alarm_id, action, _to_json(payload or {}), resolved_at),
        )
        _apply_alarm_action(conn, alarm_row["session_id"], action, payload or {})
        action_row = conn.execute(
            "select * from action_history where id = ?", (cursor.lastrowid,)
        ).fetchone()
        updated_alarm = conn.execute("select * from alarms where id = ?", (alarm_id,)).fetchone()
    return {"alarm": _alarm_from_row(updated_alarm), "action": _action_from_row(action_row)}


def latest_actions_for_alarms(
    path: Path | str, alarm_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Most recent action_history record per alarm, fetched in one query."""
    if not alarm_ids:
        return {}
    placeholders = ",".join("?" for _ in alarm_ids)
    with connect(path) as conn:
        rows = conn.execute(
            f"select * from action_history where alarm_id in ({placeholders}) order by id",
            tuple(alarm_ids),
        ).fetchall()
    # Rows ascend by id, so the last write per alarm_id is the most recent action.
    return {row["alarm_id"]: _action_from_row(row) for row in rows}


def _apply_alarm_action(
    conn: sqlite3.Connection,
    session_id: str,
    action: str,
    payload: dict[str, Any],
) -> None:
    if action == "abort_session":
        conn.execute("update sessions set status = ? where id = ?", ("aborted", session_id))
        return
    if action not in {"raise_budget", "adjust_guardrail"}:
        return

    row = conn.execute("select guardrail_overrides_json from sessions where id = ?", (session_id,)).fetchone()
    if row is None:
        return
    overrides = _from_json(row["guardrail_overrides_json"])
    if action == "raise_budget":
        budget = dict(overrides.get("budget", {}))
        budget.update(payload)
        overrides["budget"] = budget
    else:
        _deep_merge(overrides, payload)
    conn.execute(
        "update sessions set guardrail_overrides_json = ? where id = ?",
        (_to_json(overrides), session_id),
    )


def _deep_merge(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value


def build_session_artifact(path: Path | str, session_id: str) -> dict[str, Any]:
    with connect(path) as conn:
        session_row = conn.execute("select * from sessions where id = ?", (session_id,)).fetchone()
        if session_row is None:
            raise KeyError(f"session not found: {session_id}")
        token_rows = conn.execute(
            "select * from token_turns where session_id = ? order by id", (session_id,)
        ).fetchall()
        tool_trace_rows = conn.execute(
            "select * from tool_traces where session_id = ? order by id", (session_id,)
        ).fetchall()
        snapshot_rows = conn.execute(
            "select * from guardrail_snapshots where session_id = ? order by id", (session_id,)
        ).fetchall()
        alarm_rows = conn.execute(
            "select * from alarms where session_id = ? order by created_at, id", (session_id,)
        ).fetchall()
        checkpoint_rows = conn.execute(
            "select * from checkpoint_results where session_id = ? order by id", (session_id,)
        ).fetchall()
        worker_run_rows = conn.execute(
            "select * from worker_runs where session_id = ? order by created_at, id", (session_id,)
        ).fetchall()
        worker_run_event_rows = conn.execute(
            "select * from worker_run_events where session_id = ? order by created_at, id", (session_id,)
        ).fetchall()

    return {
        "session": _session_from_row(session_row),
        "token_log": [_token_turn_from_row(row) for row in token_rows],
        "tool_trace": [_tool_trace_from_row(row) for row in tool_trace_rows],
        "alarms": [_alarm_from_row(row) for row in alarm_rows],
        "guardrail_snapshots": [_snapshot_from_row(row) for row in snapshot_rows],
        "checkpoint_results": [_checkpoint_from_row(row) for row in checkpoint_rows],
        "worker_runs": [_worker_run_from_row(row) for row in worker_run_rows],
        "worker_run_events": [_worker_run_event_from_row(row) for row in worker_run_event_rows],
    }


def total_token_usage(path: Path | str, *, since: str | None = None) -> int:
    with connect(path) as conn:
        if since is None:
            row = conn.execute("select coalesce(sum(total_tokens), 0) as total from token_turns").fetchone()
        else:
            row = conn.execute(
                "select coalesce(sum(total_tokens), 0) as total from token_turns where created_at >= ?",
                (since,),
            ).fetchone()
    return int(row["total"])


def budgeted_token_usage(path: Path | str, *, since: str | None = None) -> int:
    """Total governed model-spend tokens from the token ledger."""
    return int(token_usage_breakdown(path, since=since)["total_tokens"])


def estimation_accuracy(path: Path | str) -> dict[str, Any]:
    """Compute estimation accuracy from completed implementation tasks.

    Returns completed_count, median_error_ratio, within_2x_pct.
    All values null when no completed implementation tasks with both estimate
    and actual exist. Scout actuals are excluded from implementation aggregates.
    Error ratio = actual_tokens / estimate_tokens.
    """
    with connect(path) as conn:
        rows = conn.execute(
            """
            select estimate_tokens, actual_tokens, metadata_json
            from tasks
            where status = 'Done'
              and estimate_tokens is not null
              and actual_tokens is not null
              and actual_tokens > 0
            """
        ).fetchall()
    rows = [row for row in rows if read_task_kind(_from_json(row["metadata_json"])) == "implementation"]
    if not rows:
        return {
            "completed_count": None,
            "median_error_ratio": None,
            "within_2x_pct": None,
        }
    ratios = sorted(row["actual_tokens"] / row["estimate_tokens"] for row in rows)
    n = len(ratios)
    if n % 2 == 0:
        median = (ratios[n // 2 - 1] + ratios[n // 2]) / 2
    else:
        median = ratios[n // 2]
    within_2x = sum(1 for r in ratios if 0.5 <= r <= 2.0) / n * 100
    return {
        "completed_count": n,
        "median_error_ratio": round(median, 2),
        "within_2x_pct": round(within_2x, 1),
    }


def token_usage_breakdown(path: Path | str, *, since: str | None = None) -> dict[str, Any]:
    turns = _token_turns_for_breakdown(path, since=since)
    return _summarize_token_turns(turns)


def worker_execution_token_summary(path: Path | str, *, since: str | None = None) -> dict[str, Any]:
    turns = _worker_execution_turns(_token_turns_with_session_ids(path, since=since))
    status_split = {"completed": 0, "failed_retry": 0, "unknown": 0}
    session_statuses = _worker_session_statuses(path)
    for turn in turns:
        tokens = _normalized_token_total_from_turn(turn)
        status_split[session_statuses.get(str(turn.get("session_id") or ""), "unknown")] += tokens
    return {"components": _summarize_token_components(turns), "status_split": status_split}


def session_token_usage(path: Path | str, session_id: str) -> int:
    with connect(path) as conn:
        row = conn.execute(
            "select coalesce(sum(total_tokens), 0) as total from token_turns where session_id = ?",
            (session_id,),
        ).fetchone()
    return int(row["total"])


def session_token_breakdown(path: Path | str, session_id: str) -> dict[str, Any]:
    turns = _token_turns_for_breakdown(path, session_id=session_id)
    return _summarize_token_turns(turns)


def _classified_raw_usage(usage_kind: str, raw_usage: dict[str, Any]) -> dict[str, Any]:
    usage = dict(raw_usage or {})
    usage.setdefault("spend_category", _spend_category_for_usage_kind(usage_kind))
    usage.setdefault("usage_source", _usage_source_for_usage_kind(usage_kind, usage["spend_category"]))
    return usage


def _spend_category_for_usage_kind(usage_kind: str) -> str:
    if usage_kind == "task_breakdown":
        return "task_breakdown"
    if usage_kind == "estimation":
        return "control_plane"
    if usage_kind in {"worker", "task_execution"}:
        return "worker_execution"
    if usage_kind == "adapter_verification":
        return "adapter_verification"
    if usage_kind in {"reporting", "summary"}:
        return "reporting_summary"
    if usage_kind == "planning":
        return "planning"
    return "other"


def _usage_source_for_usage_kind(usage_kind: str, spend_category: str) -> str:
    if spend_category in {"control_plane", "task_breakdown", "agent_review"}:
        return "control_plane"
    if spend_category == "adapter_verification":
        return "harness_proxy"
    if usage_kind in {"worker", "task_execution"}:
        return "harness_proxy"
    if usage_kind == "planning" or spend_category == "planning":
        return "harness_proxy"
    return "unspecified"


def _token_turns_for_breakdown(
    path: Path | str,
    *,
    since: str | None = None,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    query = "select * from token_turns"
    clauses: list[str] = []
    params: list[str] = []
    if since is not None:
        clauses.append("created_at >= ?")
        params.append(since)
    if session_id is not None:
        clauses.append("session_id = ?")
        params.append(session_id)
    if clauses:
        query += " where " + " and ".join(clauses)
    with connect(path) as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [_token_turn_from_row(row) for row in rows]


def _token_turns_with_session_ids(path: Path | str, *, since: str | None = None) -> list[dict[str, Any]]:
    query = "select * from token_turns"
    params: list[str] = []
    if since is not None:
        query += " where created_at >= ?"
        params.append(since)
    with connect(path) as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    turns = []
    for row in rows:
        turn = _token_turn_from_row(row)
        turn["session_id"] = row["session_id"]
        turns.append(turn)
    return turns


def _summarize_token_turns(turns: list[dict[str, Any]]) -> dict[str, Any]:
    by_category = {
        "control_plane": 0,
        "task_breakdown": 0,
        "worker_execution": 0,
        "adapter_verification": 0,
        "reporting_summary": 0,
        "other": 0,
    }
    cost_by_category = {cat: 0.0 for cat in by_category}
    cost_seen = {cat: False for cat in by_category}
    by_source: dict[str, int] = {}
    total = 0
    total_cost = 0.0
    any_cost = False
    priced_tokens = 0
    unpriced_tokens = 0
    for turn in turns:
        tokens = _normalized_token_total_from_turn(turn)
        cost = turn.get("cost")
        raw_usage = turn.get("raw_usage") or {}
        category = str(raw_usage.get("spend_category") or _spend_category_for_usage_kind(str(turn.get("usage_kind") or "")))
        source = str(raw_usage.get("usage_source") or _usage_source_for_usage_kind(str(turn.get("usage_kind") or ""), category))
        # Agent Review used to be its own category; report it with other control-plane summaries.
        if category == "agent_review":
            category = "reporting_summary"
            if source == "unspecified":
                source = "control_plane"
        if category not in by_category:
            category = "other"
        by_category[category] += tokens
        by_source[source] = by_source.get(source, 0) + tokens
        total += tokens
        if cost is not None:
            cost_value = float(cost)
            cost_by_category[category] += cost_value
            total_cost += cost_value
            priced_tokens += tokens
            cost_seen[category] = True
            any_cost = True
        else:
            unpriced_tokens += tokens
    for cat in by_category:
        if not cost_seen[cat]:
            cost_by_category[cat] = None if by_category[cat] > 0 else 0.0
    if not any_cost:
        total_cost = 0.0 if total == 0 else None
    return {
        "total_tokens": total,
        "by_category": by_category,
        "by_source": by_source,
        "cost_by_category": cost_by_category,
        "total_cost": total_cost,
        "priced_tokens": priced_tokens,
        "unpriced_tokens": unpriced_tokens,
    }


def _worker_execution_turns(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [turn for turn in turns if _turn_spend_category(turn) == "worker_execution"]


def _turn_spend_category(turn: dict[str, Any]) -> str:
    raw_usage = turn.get("raw_usage") or {}
    category = str(raw_usage.get("spend_category") or _spend_category_for_usage_kind(str(turn.get("usage_kind") or "")))
    return "reporting_summary" if category == "agent_review" else category


def _normalized_token_total_from_turn(turn: dict[str, Any]) -> int:
    components = token_usage_components(
        turn.get("raw_usage") or {},
        prompt_tokens=turn.get("prompt_tokens"),
        completion_tokens=turn.get("completion_tokens"),
        total_tokens=turn.get("total_tokens"),
        cost=turn.get("cost"),
    )
    if components.get("normalized_actual") is not None:
        return int(components["normalized_actual"])
    return int(turn.get("total_tokens") or 0)


def _summarize_token_components(turns: list[dict[str, Any]]) -> dict[str, Any]:
    labels = {
        "normalized_actual": "normalized actual/task budget",
        "provider_raw_total": "provider raw total/evidence",
        "fresh_input": "fresh input/new prompt text",
        "cache_read": "cache read/reused context",
        "cache_write": "cache write/create",
        "output": "output",
        "reasoning": "reasoning",
        "unclassified": "unclassified/provider-total-only",
    }
    totals = dict.fromkeys(labels, 0)
    cost = 0.0
    saw_cost = False
    for turn in turns:
        components = token_usage_components(
            turn.get("raw_usage") or {},
            prompt_tokens=turn.get("prompt_tokens"),
            completion_tokens=turn.get("completion_tokens"),
            total_tokens=turn.get("total_tokens"),
            cost=turn.get("cost"),
        )
        for key in totals:
            if components.get(key) is not None:
                totals[key] += int(components[key])
        if components.get("cost") not in (None, 0):
            saw_cost = True
            cost += float(components["cost"])
    items = [{"key": key, "label": labels[key], "value": value} for key, value in totals.items() if value]
    return {"available": bool(items or saw_cost), "items": items, "cost": cost if saw_cost else None}


def _worker_session_statuses(path: Path | str) -> dict[str, str]:
    with connect(path) as conn:
        rows = conn.execute(
            """
            select worker_runs.session_id, worker_runs.status as run_status, tasks.status as task_status
            from worker_runs
            left join tasks on tasks.id = worker_runs.task_id
            """
        ).fetchall()
    statuses: dict[str, str] = {}
    for row in rows:
        session_id = str(row["session_id"])
        run_status = str(row["run_status"] or "")
        task_status = str(row["task_status"] or "")
        if run_status == "completed" or task_status in {"Review", "Done"}:
            statuses[session_id] = "completed"
        elif run_status in {"failed", "interrupted"} and statuses.get(session_id) != "completed":
            statuses[session_id] = "failed_retry"
        else:
            statuses.setdefault(session_id, "unknown")
    return statuses


def _session_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "task_description": row["task_description"],
        "model": row["model"],
        "session_key_hash": row["session_key_hash"],
        "started_at": row["started_at"],
        "status": row["status"],
        "guardrail_overrides": _from_json(row["guardrail_overrides_json"]),
    }


def _task_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "description": row["description"],
        "status": "Estimated" if row["status"] == "Ready" else row["status"],
        "estimate_tokens": row["estimate_tokens"],
        "recommended_model": row["recommended_model"],
        "actual_tokens": row["actual_tokens"],
        "session_id": row["session_id"],
        "metadata": _from_json(row["metadata_json"]),
        "created_at": row["created_at"],
    }


def _task_breakdown_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "source_text": row["source_text"],
        "source_sha256": row["source_sha256"],
        "intake_metadata": _from_json(row["intake_metadata_json"]),
        "status": row["status"],
        "decision": row["decision"],
        "model": row["model"],
        "session_id": row["session_id"],
        "candidates": _from_json_list(row["candidates_json"]),
        "rejected_items": _from_json_list(row["rejected_items_json"]),
        "global_contract_summary": row["global_contract_summary"],
        "global_constraints": _from_json_list(row["global_constraints_json"]),
        "verification": _from_json_list(row["verification_json"]),
        "non_goals": _from_json_list(row["non_goals_json"]),
        "recommended_sequence": _from_json_list(row["recommended_sequence_json"]),
        "repo_context_evidence": _from_json(row["repo_context_evidence_json"]),
        "confidence": row["confidence"],
        "rationale": row["rationale"],
        "failure_type": row["failure_type"],
        "failure_message": row["failure_message"],
        "created_task_ids": _from_json_list(row["created_task_ids_json"]),
        "revision": row["revision"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _worker_run_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "task_id": row["task_id"],
        "session_id": row["session_id"],
        "adapter_id": row["adapter_id"],
        "model": row["model"],
        "tracking_mode": row["tracking_mode"],
        "status": row["status"],
        "command_plan": _from_json(row["command_plan_json"]),
        "metadata": _from_json(row["metadata_json"]),
        "stdout": row["stdout"],
        "stderr": row["stderr"],
        "returncode": row["returncode"],
        "error_type": row["error_type"],
        "error_message": row["error_message"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
    }


def _worker_run_event_from_row(row: sqlite3.Row) -> dict[str, Any]:
    detail = _from_json(row["detail_json"])
    return {
        "id": row["id"],
        "worker_run_id": row["worker_run_id"],
        "session_id": row["session_id"],
        "task_id": row["task_id"],
        "layer": row["layer"],
        "kind": row["kind"],
        "level": row["level"],
        "title": row["title"],
        "detail": detail,
        "detail_summary": _worker_run_event_detail_summary(detail),
        "created_at": row["created_at"],
    }


def _worker_run_event_detail_summary(detail: Any) -> str:
    if not isinstance(detail, dict):
        return ""
    parts: list[str] = []

    # Streamed Worker Run events (worker_harness layer)
    text = detail.get("text")
    if text:
        parts.append(str(text)[:400])

    arguments = detail.get("arguments")
    if arguments:
        parts.append(f"arguments={str(arguments)[:200]}")

    token_parts = []
    for key in ("input_tokens", "output_tokens", "prompt_tokens", "completion_tokens", "total_tokens"):
        value = detail.get(key)
        if value not in (None, ""):
            token_parts.append(f"{key}={value}")
    if token_parts:
        parts.append("; ".join(token_parts))

    # Existing control-plane / status fields
    for key in ("error_type", "returncode", "retryable", "status", "usage_source"):
        if key in detail and detail[key] not in (None, ""):
            parts.append(f"{key}={detail[key]}")

    workdir = detail.get("workdir_evidence")
    if isinstance(workdir, dict):
        if workdir.get("configured_workdir"):
            parts.append(f"workdir={workdir['configured_workdir']}")
        if workdir.get("expected_marker"):
            parts.append(f"marker={workdir['expected_marker']}")

    if not parts:
        parts = _scalar_detail_parts(detail)

    if not parts:
        return ""
    return "; ".join(str(part) for part in parts)[:500]


def _scalar_detail_parts(detail: dict[str, Any]) -> list[str]:
    """Summarize an unrecognized detail shape as compact `key=value` pairs.

    Control-plane events (launch, guardrail, adapter, command) carry shapes this
    function does not model field by field. Rendering their scalars keeps the feed
    readable and consistent, while skipping nested dicts/lists deliberately drops
    the large blobs — a `command_plan` belongs in the Session Report's full detail
    view, not inlined into a one-line feed row.
    """
    parts: list[str] = []
    for key, value in detail.items():
        if isinstance(value, (dict, list, tuple, set)) or value in (None, ""):
            continue
        parts.append(f"{key}={str(value)[:120]}")
        if len(parts) >= 6:
            break
    return parts


def _token_turn_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "usage_kind": row["usage_kind"],
        "model": row["model"],
        "prompt_tokens": row["prompt_tokens"],
        "completion_tokens": row["completion_tokens"],
        "total_tokens": row["total_tokens"],
        "cost": row["cost"],
        "raw_usage": _from_json(row["raw_usage_json"]),
        "created_at": row["created_at"],
    }


def _tool_trace_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "tool_name": row["tool_name"],
        "input_hash": row["input_hash"],
        "duration_ms": row["duration_ms"],
        "metadata": _from_json(row["metadata_json"]),
        "created_at": row["created_at"],
    }


def _snapshot_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "zone": row["zone"],
        "decision": _from_json(row["decision_json"]),
        "created_at": row["created_at"],
    }


def _alarm_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "type": row["type"],
        "severity": row["severity"],
        "context": _from_json(row["context_json"]),
        "recommended_action": row["recommended_action"],
        "created_at": row["created_at"],
        "resolved_at": row["resolved_at"],
    }


def _checkpoint_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "name": row["name"],
        "passed": bool(row["passed"]),
        "details": _from_json(row["details_json"]),
        "created_at": row["created_at"],
    }


def _action_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "alarm_id": row["alarm_id"],
        "action": row["action"],
        "payload": _from_json(row["payload_json"]),
        "created_at": row["created_at"],
    }


def _worker_adapter_from_row(row: sqlite3.Row) -> dict[str, Any]:
    config = _from_json(row["config_json"])
    supported_models = json.loads(row["supported_models_json"])
    return {
        "id": row["id"],
        "kind": row["kind"],
        "name": row["name"],
        "workdir": row["workdir"],
        "config": config,
        "supported_models": supported_models,
        "is_default": bool(row["is_default"]),
        "verification_status": row["verification_status"],
        "verification_evidence": _from_json(row["verification_evidence_json"]),
        "verified_at": row["verified_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "configured": bool(
            config.get("command")
            or config.get("verification_template")
            or config.get("launch_template")
            or config.get("native_verification_template")
            or config.get("native_launch_template")
        ),
    }


def _connected_project_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "root_path": row["root_path"],
        "profile": _from_json(row["profile_json"]),
        "capability": _from_json(row["capability_json"]),
        "backend_id": row["backend_id"],
        "archived_at": row["archived_at"],
        "archived_by": row["archived_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _execution_backend_status_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "online": bool(row["online"]),
        "details": _from_json(row["details_json"]),
        "checked_at": row["checked_at"],
    }


SECRET_KEY_TERMS = ("key", "secret", "password", "authorization")
SECRET_TOKEN_KEYS = {"token", "api_token", "access_token", "refresh_token", "session_token"}
SECRET_VALUE_PATTERN = re.compile(r"sk_[A-Za-z0-9_\-.]+")


def _is_secret_key_hint(key_hint: str) -> bool:
    lowered = key_hint.lower()
    return any(term in lowered for term in SECRET_KEY_TERMS) or lowered in SECRET_TOKEN_KEYS or lowered.endswith("_token")


def _sanitize_secret_string(value: str) -> str:
    if "secret" in value.lower():
        return "***REDACTED***"
    return SECRET_VALUE_PATTERN.sub("***REDACTED***", value)


def _sanitize_evidence(value: Any, key_hint: str = "") -> Any:
    if isinstance(value, dict):
        return {k: _sanitize_evidence(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_evidence(item, key_hint) for item in value]
    if isinstance(value, str):
        # Evidence can include raw CLI output, so sanitize by both key hints and token-like values.
        if _is_secret_key_hint(key_hint):
            return "***REDACTED***"
        return _sanitize_secret_string(value)
    return value


def _to_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _to_json_list(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _from_json(value: str) -> dict[str, Any]:
    return json.loads(value)


def _from_json_list(value: str) -> list[Any]:
    parsed = json.loads(value)
    return parsed if isinstance(parsed, list) else []


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalize_utc_iso(value: str) -> str:
    parsed = _parse_iso_datetime(value)
    if parsed is None:
        return _now_iso()
    return parsed.isoformat()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
