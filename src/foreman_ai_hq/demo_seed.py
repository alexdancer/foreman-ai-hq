from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from foreman_ai_hq import db
from foreman_ai_hq.project_context import project_task_metadata

DEMO_PROJECT_NAME = "DEMO_2099_snip_project"
DEMO_WORKER_ADAPTER_ID = "demo_worker"
DEMO_SCHEMA_VERSION = 2
DEMO_SESSION_DESCRIPTION = "DEMO 2099 synthetic Worker session · schema 2"
DEMO_BREAKDOWN_ID = "DEMO_BREAKDOWN_2099_999"
DEMO_WORKER_RUN_ID = "DEMO_WORKER_RUN_2099_REVIEW_999"
DEMO_ALARM_ID = "DEMO_ALARM_2099_REVIEW_999"
DEMO_README_TEXT = "# DEMO 2099 snip project\n\nA synthetic fixture for Foreman AI HQ. Safe to delete.\n"
DEMO_SNIP_TEXT = "print('DEMO 2099 snip fixture')\n"
DEMO_WORKER_MODELS = (
    "claude-sonnet-5",
    "claude-haiku-4-5",
)

DEMO_TASKS = (
    {
        "id": "DEMO_TASK_2099_T1",
        "description": "Implement `snip save` — accept title, language, and body via CLI args; write snippet to the store",
        "complexity": "Simple",
        "status": "Estimated",
        "estimate_tokens": 8_000,
        "recommended_model": "Claude Haiku",
    },
    {
        "id": "DEMO_TASK_2099_T2",
        "description": "Add a `--color` flag — support `--color/--no-color` for terminal output; pass through to rich.print",
        "complexity": "Simple",
        "status": "Estimated",
        "estimate_tokens": 5_000,
        "recommended_model": "Claude Haiku",
        "metadata": {
            "requires_manual_estimate": True,
            "blocked_condition": {
                "reason": "DEMO 2099 requires an operator estimate before launch.",
                "origin": "estimation",
                "timestamp": "2099-06-13T00:02:00+00:00",
            },
        },
    },
    {
        "id": "DEMO_TASK_2099_T3",
        "description": "Implement `snip list` with filters — list all snippets; support `--language` and `--tag` filters; format as a table with rich",
        "complexity": "Modest",
        "status": "Running",
        "estimate_tokens": 25_000,
        "recommended_model": "Claude Sonnet",
        "session_id": "DEMO_SESSION_2099_RUNNING_999",
        "metadata": {
            "active_worker_run_id": "DEMO_WORKER_RUN_2099_999",
            "worker_run_status": "running",
            "launch_adapter_id": DEMO_WORKER_ADAPTER_ID,
            "launch_model": "claude-sonnet-5",
            "worker_run_events": [{
                "id": 999001,
                "created_at": "2099-06-13T00:03:00+00:00",
                "kind": "worker_progress",
                "layer": "worker_harness",
                "title": "DEMO Worker implementing filters",
                "detail_summary": "Synthetic run is active with bounded evidence.",
            }],
        },
    },
    {
        "id": "DEMO_TASK_2099_T4",
        "description": "Add fuzzy search via `snip search` — accept a query string; use thefuzz for fuzzy matching on title and body; rank and display results",
        "complexity": "Modest",
        "status": "Review",
        "estimate_tokens": 35_000,
        "recommended_model": "Claude Sonnet",
        "actual_tokens": 31_999,
        "session_id": "DEMO_SESSION_2099_REVIEW_999",
        "metadata": {
            "review_actions_available": True,
            "launch_model": "claude-sonnet-5",
            "review_prompt": "Verify synthetic DEMO 2099 fuzzy ranking and bounded output.",
            "agent_review": {
                "status": "completed",
                "recommendation": "approve",
                "summary": "DEMO 2099 Agent Review found the synthetic fuzzy-search contract satisfied.",
                "findings": [{
                    "severity": "info",
                    "message": "DEMO 2099 ranking evidence is deterministic and bounded.",
                    "path": "snip.py",
                    "line": 9,
                }],
                "review_session_id": "DEMO_SESSION_2099_AGENT_REVIEW_999",
                "model": "DEMO_CONTROL_PLANE_2099_999",
                "reviewed_at": "2099-06-13T00:05:00+00:00",
            },
            "blocked_condition": {
                "reason": "DEMO 2099 Worker output awaits operator disposition.",
                "origin": "review",
                "timestamp": "2099-06-13T00:04:00+00:00",
            },
        },
    },
    {
        "id": "DEMO_TASK_2099_T5",
        "description": "Add SQLite backend with migration — replace JSON file store with sqlite3; import existing DEMO JSON snippets; add `--db-path` flag",
        "complexity": "Complex",
        "status": "Done",
        "estimate_tokens": 90_000,
        "recommended_model": "Claude Opus",
        "actual_tokens": 84_999,
    },
    {
        "id": "DEMO_TASK_2099_T6",
        "description": "Add `snip share` with DEMO gist integration — accept a snippet ID; call a fake GitHub Gist seam; require a demo token env var",
        "complexity": "Complex",
        "status": "Estimated",
        "estimate_tokens": 80_000,
        "recommended_model": "Claude Opus",
        "metadata": {
            "budget_override_available": True,
            "blocked_condition": {
                "reason": "DEMO 2099 launch exceeds the synthetic session budget.",
                "origin": "launch_guardrail",
                "timestamp": "2099-06-13T00:06:00+00:00",
            },
        },
    },
)


def _demo_worker_template() -> list[str]:
    """Command template for the synthetic Worker, using the installed entrypoint."""
    return ["foremanctl", "demo-worker", "--model", "{model}", "--workdir", "{workdir}", "{prompt}"]


def seed_demo_tasks(db_path: Path | str, project: dict[str, Any] | None = None) -> list[dict[str, object]]:
    """Insert the six synthetic DEMO snip tasks if absent.

    Returns only tasks inserted during this call, making the function idempotent
    and easy for operators/tests to verify.

    When `project` is given, each task carries that project's binding snapshot.
    Without it the tasks are board-visible but not launchable: `resolve_task_project`
    rejects any task with no `connected_project_id`.
    """
    db.init_db(db_path)
    _validate_demo_task_ids(db_path)
    _validate_demo_evidence_ids(db_path)
    binding = project_task_metadata(project) if project else {}
    inserted_ids: list[str] = []
    with db.connect(db_path) as conn:
        for session_id, status in (
            ("DEMO_SESSION_2099_RUNNING_999", "running"),
            ("DEMO_SESSION_2099_REVIEW_999", "completed"),
            ("DEMO_SESSION_2099_AGENT_REVIEW_999", "completed"),
        ):
            conn.execute(
                """insert or ignore into sessions
                   (id, task_description, model, session_key_hash, started_at, status, guardrail_overrides_json)
                   values (?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    DEMO_SESSION_DESCRIPTION,
                    "claude-sonnet-5",
                    f"DEMO_HASH_2099_{session_id}",
                    "2099-06-13T00:00:00+00:00",
                    status,
                    "{}",
                ),
            )
            conn.execute(
                "update sessions set task_description = ? where id = ?",
                (DEMO_SESSION_DESCRIPTION, session_id),
            )
        for task in DEMO_TASKS:
            existing = conn.execute(
                "select id, metadata_json from tasks where id = ?",
                (task["id"],),
            ).fetchone()
            if existing is not None:
                metadata = json.loads(existing["metadata_json"] or "{}")
                if metadata.get("demo") != "DEMO_SNIP_2099":
                    raise RuntimeError(f"refusing to replace non-demo task {task['id']}")
                canonical_metadata = {
                    **metadata,
                    "complexity": task["complexity"],
                    "demo": "DEMO_SNIP_2099",
                    "demo_schema_version": DEMO_SCHEMA_VERSION,
                    "read_only": True,
                    **binding,
                    **task.get("metadata", {}),
                }
                if metadata.get("demo_schema_version") != DEMO_SCHEMA_VERSION:
                    conn.execute(
                        """update tasks
                           set description = ?, status = ?, estimate_tokens = ?,
                               recommended_model = ?, actual_tokens = ?, session_id = ?,
                               metadata_json = ?
                           where id = ?""",
                        (
                            task["description"],
                            task["status"],
                            task["estimate_tokens"],
                            task["recommended_model"],
                            task.get("actual_tokens"),
                            task.get("session_id"),
                            json.dumps(canonical_metadata, separators=(",", ":"), sort_keys=True),
                            task["id"],
                        ),
                    )
                elif project is not None:
                    conn.execute(
                        "update tasks set metadata_json = ? where id = ?",
                        (
                            json.dumps({**metadata, **binding}, separators=(",", ":"), sort_keys=True),
                            task["id"],
                        ),
                    )
                continue
            conn.execute(
                """
                insert into tasks (
                    id, description, status, estimate_tokens, recommended_model,
                    actual_tokens, session_id, metadata_json, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task["id"],
                    task["description"],
                    task["status"],
                    task["estimate_tokens"],
                    task["recommended_model"],
                    task.get("actual_tokens"),
                    task.get("session_id"),
                    json.dumps(
                        {
                            "complexity": task["complexity"],
                            "demo": "DEMO_SNIP_2099",
                            "demo_schema_version": DEMO_SCHEMA_VERSION,
                            "read_only": True,
                            **binding,
                            **task.get("metadata", {}),
                        },
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    "2099-06-13T00:00:00+00:00",
                ),
            )
            inserted_ids.append(task["id"])
    _seed_demo_review_evidence(db_path)
    return [db.get_task(db_path, task_id) for task_id in inserted_ids]


def _seed_demo_review_evidence(db_path: Path | str) -> None:
    """Create deterministic, idempotent Session Report evidence for the drawer."""
    session_id = "DEMO_SESSION_2099_REVIEW_999"
    run_id = DEMO_WORKER_RUN_ID
    created_at = "2099-06-13T00:04:00+00:00"
    with db.connect(db_path) as conn:
        conn.execute(
            """insert or ignore into worker_runs
               (id, task_id, session_id, adapter_id, model, tracking_mode, status,
                command_plan_json, metadata_json, stdout, stderr, returncode,
                created_at, started_at, completed_at)
               values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                "DEMO_TASK_2099_T4",
                session_id,
                DEMO_WORKER_ADAPTER_ID,
                "claude-sonnet-5",
                "native_usage",
                "completed",
                json.dumps({"command": ["foremanctl", "demo-worker", "DEMO 2099 fuzzy search"]}),
                json.dumps({
                    "synthetic_fixture": True,
                    "demo": "DEMO_SNIP_2099",
                    "demo_schema_version": DEMO_SCHEMA_VERSION,
                    "repo_context_brief": {
                        "documents": [{"path": "README.md"}],
                        "manifests": ["pyproject.toml"],
                        "text": "DEMO 2099 Repo Context Brief for the synthetic snip project.",
                    },
                }),
                "DEMO 2099 Worker output: fuzzy-search ranking verified.\n",
                "",
                0,
                created_at,
                created_at,
                "2099-06-13T00:04:30+00:00",
            ),
        )
        worker_metadata = _demo_json_marker(
            conn.execute("select metadata_json from worker_runs where id = ?", (run_id,)).fetchone()[0]
        )
        conn.execute(
            "update worker_runs set metadata_json = ? where id = ?",
            (
                json.dumps({
                    **worker_metadata,
                    "synthetic_fixture": True,
                    "demo": "DEMO_SNIP_2099",
                    "demo_schema_version": DEMO_SCHEMA_VERSION,
                }, separators=(",", ":"), sort_keys=True),
                run_id,
            ),
        )
        conn.execute(
            """insert into worker_run_events
               (worker_run_id, session_id, task_id, layer, kind, level, title, detail_json, created_at)
               select ?, ?, ?, ?, ?, ?, ?, ?, ?
               where not exists (
                   select 1 from worker_run_events where worker_run_id = ? and kind = ?
               )""",
            (
                run_id, session_id, "DEMO_TASK_2099_T4", "worker_harness",
                "worker_output", "info", "DEMO Worker completed fuzzy search",
                json.dumps({"output": "DEMO 2099 Worker output: fuzzy-search ranking verified."}),
                created_at, run_id, "worker_output",
            ),
        )
        conn.execute(
            """insert into token_turns
               (session_id, usage_kind, model, prompt_tokens, completion_tokens,
                total_tokens, cost, raw_usage_json, created_at)
               select ?, ?, ?, ?, ?, ?, ?, ?, ?
               where not exists (select 1 from token_turns where session_id = ? and usage_kind = ?)""",
            (
                session_id, "worker", "claude-sonnet-5", 28_999, 3_000, 31_999, None,
                json.dumps({"input_tokens": 28_999, "output_tokens": 3_000, "total_tokens": 31_999}),
                created_at, session_id, "worker",
            ),
        )
        conn.execute(
            """insert into guardrail_snapshots (session_id, zone, decision_json, created_at)
               select ?, ?, ?, ?
               where not exists (select 1 from guardrail_snapshots where session_id = ? and zone = ?)""",
            (
                session_id, "yellow",
                json.dumps({"max_tokens": 35_000, "reason": "DEMO 2099 bounded review run"}),
                created_at, session_id, "yellow",
            ),
        )
        conn.execute(
            """insert or ignore into alarms
               (id, session_id, type, severity, context_json, recommended_action, created_at)
               values (?, ?, ?, ?, ?, ?, ?)""",
            (
                DEMO_ALARM_ID, session_id, "BUDGET_YELLOW", "MEDIUM",
                json.dumps({
                    "synthetic_fixture": True,
                    "demo": "DEMO_SNIP_2099",
                    "demo_schema_version": DEMO_SCHEMA_VERSION,
                }),
                "Review synthetic DEMO 2099 spend.", created_at,
            ),
        )
        alarm_context = _demo_json_marker(
            conn.execute("select context_json from alarms where id = ?", (DEMO_ALARM_ID,)).fetchone()[0]
        )
        conn.execute(
            "update alarms set context_json = ? where id = ?",
            (
                json.dumps({
                    **alarm_context,
                    "synthetic_fixture": True,
                    "demo": "DEMO_SNIP_2099",
                    "demo_schema_version": DEMO_SCHEMA_VERSION,
                }, separators=(",", ":"), sort_keys=True),
                DEMO_ALARM_ID,
            ),
        )
        conn.execute(
            """insert into checkpoint_results (session_id, name, passed, details_json, created_at)
               select ?, ?, ?, ?, ?
               where not exists (select 1 from checkpoint_results where session_id = ? and name = ?)""",
            (
                session_id, "demo_contract", 1,
                json.dumps({"summary": "DEMO 2099 synthetic verification passed."}),
                created_at, session_id, "demo_contract",
            ),
        )


def seed_demo_sandbox(db_path: Path | str, project_root: Path | str) -> dict[str, Any]:
    """Seed a self-contained, launchable demo project at `project_root`.

    Creates the synthetic repo, connects it as a project, seeds the demo tasks
    bound to it, and sets a deterministic budget. Idempotent: re-running against
    the same root refreshes the project and leaves existing tasks alone.
    """
    db.init_db(db_path)
    _validate_demo_task_ids(db_path)
    _validate_demo_evidence_ids(db_path)
    _validate_demo_breakdown_id(db_path)
    _validate_demo_worker_adapter_id(db_path)
    root = Path(project_root).expanduser().resolve()
    _synthetic_demo_repo(root)
    project = _seed_demo_project(db_path, root)
    _seed_demo_worker_adapter(db_path)
    inserted = seed_demo_tasks(db_path, project=project)
    breakdown = _seed_demo_breakdown(db_path, project)
    db.set_token_budget_settings(db_path, daily_cap_tokens=200_000, session_cap_tokens=100_000)
    return {
        "project": project,
        "project_root": str(root),
        "inserted_tasks": inserted,
        "planning_breakdown": breakdown,
    }


def _seed_demo_breakdown(db_path: Path | str, project: dict[str, Any]) -> dict[str, Any]:
    """Seed one deterministic proposed breakdown for the Needs You queue."""
    breakdown_id = DEMO_BREAKDOWN_ID
    try:
        existing = db.get_task_breakdown(db_path, breakdown_id)
    except KeyError:
        created = db.create_task_breakdown(
            db_path,
            source_text="# DEMO 2099 planning intake\n\nSplit synthetic snippet export into governed slices.",
            source_sha256="9" * 64,
            intake_metadata={
                "connected_project_id": project["id"],
                "source_name": "DEMO_INTAKE_2099_999.md",
                "demo": "DEMO_SNIP_2099",
                "demo_schema_version": DEMO_SCHEMA_VERSION,
            },
            status="proposed",
            decision="pending_review",
            model="DEMO_CONTROL_PLANE_2099_999",
            candidates=[{
                "summary": "Add deterministic DEMO 2099 snippet export",
                "prompt": "Implement synthetic export without network access.",
                "acceptance_claim": "DEMO 2099 export is locally verifiable.",
            }],
            global_contract_summary="Preserve the synthetic DEMO 2099 contract.",
            verification=["Run the DEMO 2099 local test suite."],
            confidence=0.99,
            rationale="Synthetic Needs You fixture.",
        )
    else:
        intake_metadata = {
            **existing["intake_metadata"],
            "connected_project_id": project["id"],
            "source_name": "DEMO_INTAKE_2099_999.md",
            "demo": "DEMO_SNIP_2099",
            "demo_schema_version": DEMO_SCHEMA_VERSION,
        }
        with db.connect(db_path) as conn:
            conn.execute(
                "update task_breakdowns set intake_metadata_json = ? where id = ?",
                (
                    json.dumps(intake_metadata, separators=(",", ":"), sort_keys=True),
                    breakdown_id,
                ),
            )
        return db.get_task_breakdown(db_path, breakdown_id)
    with db.connect(db_path) as conn:
        conn.execute(
            """update task_breakdowns
               set id = ?, created_at = ?, updated_at = ?
               where id = ?""",
            (
                breakdown_id,
                "2099-06-13T00:01:00+00:00",
                "2099-06-13T00:01:00+00:00",
                created["id"],
            ),
        )
    return db.get_task_breakdown(db_path, breakdown_id)


def _synthetic_demo_repo(root: Path) -> None:
    """Create a minimal synthetic git project for the demo worker to run against."""
    if root.exists() and any(root.iterdir()):
        marker = root / "README.md"
        if not marker.is_file() or marker.read_text(encoding="utf-8") != DEMO_README_TEXT:
            raise ValueError(
                f"refusing to overwrite non-demo project root: {root}; choose an empty --project-root"
            )
    root.mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    snippet = root / "snip.py"
    if not readme.exists():
        readme.write_text(DEMO_README_TEXT, encoding="utf-8")
    if not snippet.exists():
        snippet.write_text(DEMO_SNIP_TEXT, encoding="utf-8")
    if not (root / ".git").is_dir():
        subprocess.run(["git", "init"], cwd=str(root), check=True, capture_output=True, text=True)


def _seed_demo_project(db_path: Path | str, root: Path) -> dict[str, Any]:
    """Connect the synthetic repo as a launch-ready Local Runner project."""
    from foreman_ai_hq import execution_backend

    return db.upsert_connected_project(
        db_path,
        name=DEMO_PROJECT_NAME,
        root_path=str(root),
        profile=execution_backend.detect_project_profile(root),
        capability={
            "state": "launch_ready",
            "label": "Launch-ready via Local Runner",
            "backend": "local_runner",
            "reasons": [],
            "can_launch": True,
            "can_analyze": True,
        },
        backend_id="local_runner",
    )


def _seed_demo_worker_adapter(db_path: Path | str) -> None:
    """Ensure a verified demo worker adapter exists for the portal launch flow.

    The adapter kind is `claude_code` on purpose: the demo worker speaks real
    `stream-json`, so keeping the production builder means launches exercise the
    real stream parsing, event recording, and native-usage accounting instead of
    a demo-only code path. Only the command is synthetic.
    """
    config = {
        "command": "foremanctl",
        "allowed_models_configured": True,
        "verification_template": ["foremanctl", "demo-worker", "--delay-ms", "0", "verify"],
        "launch_template": _demo_worker_template(),
        "native_verification_template": ["foremanctl", "demo-worker", "--delay-ms", "0", "verify"],
        "native_launch_template": _demo_worker_template(),
        "launch_timeout_seconds": 360,
    }
    evidence = {
        "tracking_mode": "native_usage",
        "tracking_authoritative": True,
        "token_recorded": True,
        "source": "synthetic_demo_seed",
        "synthetic_fixture": True,
        "demo": "DEMO_SNIP_2099",
        "demo_schema_version": DEMO_SCHEMA_VERSION,
    }
    try:
        existing = db.get_worker_adapter(db_path, DEMO_WORKER_ADAPTER_ID)
    except KeyError:
        with db.connect(db_path) as conn:
            conn.execute(
                """insert into worker_adapters
               (id, kind, name, config_json, supported_models_json, workdir,
                verification_status, verification_evidence_json, is_default, created_at, updated_at)
               values (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
                (
                    DEMO_WORKER_ADAPTER_ID,
                    "claude_code",
                    "Demo Worker (synthetic stream)",
                    json.dumps(config, separators=(",", ":")),
                    json.dumps(list(DEMO_WORKER_MODELS), separators=(",", ":")),
                    "/tmp",
                    "verified",
                    json.dumps(evidence, separators=(",", ":"), sort_keys=True),
                    "2099-06-13T00:00:00+00:00",
                    "2099-06-13T00:00:00+00:00",
                ),
            )
    else:
        if not existing.get("verification_evidence", {}).get("synthetic_fixture"):
            raise RuntimeError("refusing to replace non-demo worker adapter demo_worker")

    preserve_existing_default = any(
        adapter.get("is_default") and adapter["id"] != DEMO_WORKER_ADAPTER_ID
        for adapter in db.list_worker_adapters(db_path)
    )
    db.update_worker_adapter(
        db_path,
        DEMO_WORKER_ADAPTER_ID,
        workdir="/tmp",
        config=config,
        supported_models=list(DEMO_WORKER_MODELS),
        is_default=not preserve_existing_default,
    )
    with db.connect(db_path) as conn:
        conn.execute(
            """update worker_adapters
               set verification_status = ?, verification_evidence_json = ?,
                   verified_at = ?, updated_at = ?
               where id = ?""",
            (
                "verified",
                json.dumps(evidence, separators=(",", ":"), sort_keys=True),
                "2099-06-13T00:00:00+00:00",
                "2099-06-13T00:00:00+00:00",
                DEMO_WORKER_ADAPTER_ID,
            ),
        )


def _validate_demo_task_ids(db_path: Path | str) -> None:
    """Reject task-id collisions before any demo rows or repository files change."""
    placeholders = ",".join("?" for _ in DEMO_TASKS)
    with db.connect(db_path) as conn:
        rows = conn.execute(
            f"select id, metadata_json from tasks where id in ({placeholders})",
            tuple(task["id"] for task in DEMO_TASKS),
        ).fetchall()
    for row in rows:
        try:
            metadata = json.loads(row["metadata_json"] or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"refusing to replace non-demo task {row['id']}") from exc
        if metadata.get("demo") != "DEMO_SNIP_2099":
            raise RuntimeError(f"refusing to replace non-demo task {row['id']}")


def _validate_demo_worker_adapter_id(db_path: Path | str) -> None:
    """Reject adapter-id collisions before creating the synthetic repository."""
    try:
        adapter = db.get_worker_adapter(db_path, DEMO_WORKER_ADAPTER_ID)
    except KeyError:
        return
    if not adapter.get("verification_evidence", {}).get("synthetic_fixture"):
        raise RuntimeError("refusing to replace non-demo worker adapter demo_worker")


def _validate_demo_evidence_ids(db_path: Path | str) -> None:
    """Fail closed when deterministic demo session/evidence ids are operator-owned."""
    session_ids = (
        "DEMO_SESSION_2099_RUNNING_999",
        "DEMO_SESSION_2099_REVIEW_999",
        "DEMO_SESSION_2099_AGENT_REVIEW_999",
    )
    with db.connect(db_path) as conn:
        session_rows = [
            row
            for session_id in session_ids
            if (
                row := conn.execute(
                    "select id, task_description, session_key_hash from sessions where id = ?",
                    (session_id,),
                ).fetchone()
            )
        ]
        worker_run = conn.execute(
            "select task_id, session_id, metadata_json from worker_runs where id = ?",
            (DEMO_WORKER_RUN_ID,),
        ).fetchone()
        alarm = conn.execute(
            "select session_id, context_json from alarms where id = ?",
            (DEMO_ALARM_ID,),
        ).fetchone()

    accepted_descriptions = {
        "DEMO 2099 synthetic Worker session",
        DEMO_SESSION_DESCRIPTION,
    }
    for row in session_rows:
        if (
            row["task_description"] not in accepted_descriptions
            or row["session_key_hash"] != f"DEMO_HASH_2099_{row['id']}"
        ):
            raise RuntimeError(f"refusing to replace non-demo session {row['id']}")

    if worker_run is not None:
        metadata = _demo_json_marker(worker_run["metadata_json"])
        if (
            worker_run["task_id"] != "DEMO_TASK_2099_T4"
            or worker_run["session_id"] != "DEMO_SESSION_2099_REVIEW_999"
            or not metadata.get("synthetic_fixture")
        ):
            raise RuntimeError(f"refusing to replace non-demo Worker Run {DEMO_WORKER_RUN_ID}")

    if alarm is not None:
        context = _demo_json_marker(alarm["context_json"])
        if (
            alarm["session_id"] != "DEMO_SESSION_2099_REVIEW_999"
            or not context.get("synthetic_fixture")
        ):
            raise RuntimeError(f"refusing to replace non-demo alarm {DEMO_ALARM_ID}")


def _validate_demo_breakdown_id(db_path: Path | str) -> None:
    """Validate the deterministic Needs You id before creating repo/project state."""
    try:
        breakdown = db.get_task_breakdown(db_path, DEMO_BREAKDOWN_ID)
    except KeyError:
        return
    metadata = breakdown.get("intake_metadata") or {}
    if (
        breakdown.get("source_sha256") != "9" * 64
        or metadata.get("source_name") != "DEMO_INTAKE_2099_999.md"
        or metadata.get("demo") not in {None, "DEMO_SNIP_2099"}
    ):
        raise RuntimeError(f"refusing to replace non-demo Task Breakdown {DEMO_BREAKDOWN_ID}")


def _demo_json_marker(raw: str | None) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}
