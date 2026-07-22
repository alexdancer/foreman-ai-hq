import sqlite3
from datetime import UTC, datetime

import pytest

from foreman_ai_hq import db
from foreman_ai_hq.db import (
    build_session_artifact,
    connect,
    create_session,
    create_task,
    estimation_accuracy,
    effective_daily_budget_window_start,
    get_session,
    init_db,
    list_task_breakdowns_for_project,
    record_alarm,
    record_checkpoint_result,
    record_guardrail_snapshot,
    record_token_turn,
    record_tool_trace,
    reset_daily_budget_counter,
    set_token_budget_settings,
    token_usage_breakdown,
    update_session_status,
)


def test_init_db_creates_schema_idempotently_with_foreign_keys(tmp_path):
    db_path = tmp_path / "harness.db"

    init_db(db_path)
    init_db(db_path)

    with connect(db_path) as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table' and name not like 'sqlite_%'"
            )
        }
        foreign_keys_enabled = conn.execute("pragma foreign_keys").fetchone()[0]
        token_turn_columns = {
            row["name"] for row in conn.execute("pragma table_info(token_turns)").fetchall()
        }

    assert {
        "sessions",
        "tasks",
        "token_turns",
        "tool_traces",
        "alarms",
        "guardrail_snapshots",
        "checkpoint_results",
        "action_history",
        "worker_adapters",
        "connected_projects",
        "execution_backend_status",
    }.issubset(tables)
    assert foreign_keys_enabled == 1
    assert "usage_kind" in token_turn_columns


def test_create_and_get_session_round_trips_json_overrides(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)

    session = create_session(
        db_path,
        task_description="Implement snip save",
        model="claude-haiku",
        session_key_hash="hash-123",
        guardrail_overrides={"session_cap": {"tokens": 50_000}},
    )

    loaded = get_session(db_path, session["id"])

    assert loaded == session
    assert loaded["status"] == "running"
    assert loaded["task_description"] == "Implement snip save"
    assert loaded["model"] == "claude-haiku"
    assert loaded["session_key_hash"] == "hash-123"
    assert loaded["guardrail_overrides"] == {"session_cap": {"tokens": 50_000}}
    assert loaded["started_at"]


def test_list_task_breakdowns_for_project_returns_open_newest_first(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)
    first = db.create_task_breakdown(
        db_path,
        source_text="DEMO first 2099",
        source_sha256="first-999",
        intake_metadata={"connected_project_id": "project-999"},
        status="pending_review",
        decision="multi_task",
        model="demo-model",
    )
    second = db.create_task_breakdown(
        db_path,
        source_text="DEMO second 2099",
        source_sha256="second-999",
        intake_metadata={"connected_project_id": "project-999"},
        status="failed",
        decision="failed",
        model="demo-model",
    )
    db.create_task_breakdown(
        db_path,
        source_text="DEMO other 2099",
        source_sha256="other-999",
        intake_metadata={"connected_project_id": "other-project-999"},
        status="pending_review",
        decision="multi_task",
        model="demo-model",
    )
    db.update_task_breakdown(db_path, first["id"], {"status": "accepted"})

    listed = list_task_breakdowns_for_project(db_path, "project-999")

    assert [item["id"] for item in listed] == [second["id"]]


def test_init_db_migrates_blocked_tasks_to_estimated_conditions(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)
    estimated = create_task(
        db_path,
        description="DEMO blocked estimated 2099",
        status="Estimated",
        estimate_tokens=999,
        metadata={},
    )
    manual = create_task(
        db_path,
        description="DEMO blocked manual 2099",
        status="Estimated",
        metadata={},
    )
    with connect(db_path) as conn:
        conn.execute(
            "update tasks set status = 'Blocked', metadata_json = ? where id = ?",
            ('{"blocked_reason":"DEMO review required 2099"}', estimated["id"]),
        )
        conn.execute("update tasks set status = 'Blocked' where id = ?", (manual["id"],))

    init_db(db_path)

    migrated = [db.get_task(db_path, task_id) for task_id in (estimated["id"], manual["id"])]
    assert {task["status"] for task in migrated} == {"Estimated"}
    assert migrated[0]["metadata"]["blocked_condition"]["reason"] == "DEMO review required 2099"
    assert migrated[1]["metadata"]["blocked_condition"]["reason"] == "manual estimate required"
    assert migrated[1]["metadata"]["requires_manual_estimate"] is True
    with connect(db_path) as conn:
        assert conn.execute("select count(*) from tasks where status = 'Blocked'").fetchone()[0] == 0


def test_blocked_review_task_is_dismissible_but_plain_review_is_not(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)
    blocked = create_task(
        db_path,
        description="DEMO failed run 2099",
        status="Review",
        estimate_tokens=9000,
        recommended_model="5.4",
        metadata={
            "blocked_condition": {
                "reason": "Session failed.",
                "origin": "session_completion",
                "timestamp": "2099-06-13T00:00:00+00:00",
            }
        },
    )
    plain = create_task(
        db_path,
        description="DEMO awaiting review 2099",
        status="Review",
        estimate_tokens=9000,
        recommended_model="5.4",
        metadata={},
    )

    archived = db.archive_task(db_path, blocked["id"])
    assert archived["metadata"]["archived_at"]

    with pytest.raises(ValueError, match="blocked Review tasks"):
        db.archive_task(db_path, plain["id"])
    assert not db.get_task(db_path, plain["id"])["metadata"].get("archived_at")


def test_update_session_status_marks_final_state(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)
    session = create_session(
        db_path,
        task_description="Verify worker",
        model="claude-haiku",
        session_key_hash="hash-status",
        guardrail_overrides={},
    )

    updated = update_session_status(db_path, session["id"], "completed")

    assert updated["status"] == "completed"
    assert get_session(db_path, session["id"])["status"] == "completed"


def test_session_artifact_rebuilds_persisted_session_rows(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)
    session = create_session(
        db_path,
        task_description="Implement snip list",
        model="claude-sonnet",
        session_key_hash="hash-456",
        guardrail_overrides={},
    )

    record_token_turn(
        db_path,
        session_id=session["id"],
        model="claude-sonnet",
        prompt_tokens=1200,
        completion_tokens=300,
        cost=0.0123,
        raw_usage={"prompt_tokens": 1200, "completion_tokens": 300, "total_tokens": 1600},
    )
    record_tool_trace(
        db_path,
        session_id=session["id"],
        tool_name="read_file",
        input_hash="hash-readme",
        duration_ms=42,
        metadata={"path": "README.md"},
    )
    record_guardrail_snapshot(
        db_path,
        session_id=session["id"],
        zone="yellow",
        decision={"max_tokens": 2048, "blocked_tools": ["web_search"]},
    )
    record_alarm(
        db_path,
        session_id=session["id"],
        alarm={
            "id": "alarm-1",
            "type": "BUDGET_YELLOW",
            "severity": "LOW",
            "context": {"zone": "yellow"},
            "recommended_action": "Agent constrained; no user action needed.",
        },
    )
    record_checkpoint_result(
        db_path,
        session_id=session["id"],
        checkpoint={
            "name": "budget_health",
            "passed": True,
            "details": {"spent": 1600},
        },
    )

    artifact = build_session_artifact(db_path, session["id"])

    assert artifact["session"]["id"] == session["id"]
    assert artifact["session"]["task_description"] == "Implement snip list"
    token_turn = artifact["token_log"][0]
    assert token_turn == {
        "usage_kind": "worker",
        "model": "claude-sonnet",
        "prompt_tokens": 1200,
        "completion_tokens": 300,
        "total_tokens": 1600,
        "cost": 0.0123,
        "raw_usage": {
            "prompt_tokens": 1200,
            "completion_tokens": 300,
            "total_tokens": 1600,
            "spend_category": "worker_execution",
            "usage_source": "harness_proxy",
        },
        "created_at": token_turn["created_at"],
    }
    assert token_turn["created_at"]
    tool_trace = artifact["tool_trace"][0]
    assert tool_trace == {
        "tool_name": "read_file",
        "input_hash": "hash-readme",
        "duration_ms": 42,
        "metadata": {"path": "README.md"},
        "created_at": tool_trace["created_at"],
    }
    assert tool_trace["created_at"]
    snapshot = artifact["guardrail_snapshots"][0]
    assert snapshot == {
        "zone": "yellow",
        "decision": {"max_tokens": 2048, "blocked_tools": ["web_search"]},
        "created_at": snapshot["created_at"],
    }
    alarm = artifact["alarms"][0]
    assert alarm == {
        "id": "alarm-1",
        "session_id": session["id"],
        "type": "BUDGET_YELLOW",
        "severity": "LOW",
        "context": {"zone": "yellow"},
        "recommended_action": "Agent constrained; no user action needed.",
        "created_at": alarm["created_at"],
        "resolved_at": None,
    }
    checkpoint = artifact["checkpoint_results"][0]
    assert checkpoint == {
        "name": "budget_health",
        "passed": True,
        "details": {"spent": 1600},
        "created_at": checkpoint["created_at"],
    }


def test_foreign_keys_reject_rows_for_unknown_session(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)

    try:
        record_token_turn(
            db_path,
            session_id="missing",
            model="claude-haiku",
            prompt_tokens=1,
            completion_tokens=2,
            cost=0.0,
            raw_usage={},
        )
    except sqlite3.IntegrityError:
        return

    raise AssertionError("expected sqlite3.IntegrityError for unknown session")


def test_record_token_turn_persists_explicit_usage_kind(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)
    session = create_session(
        db_path,
        task_description="Estimate task",
        model="gpt-4o-mini",
        session_key_hash="hash-estimator",
        guardrail_overrides={},
    )

    record_token_turn(
        db_path,
        session_id=session["id"],
        usage_kind="estimation",
        model="gpt-4o-mini",
        prompt_tokens=200,
        completion_tokens=50,
        cost=0.001,
        raw_usage={"prompt_tokens": 200, "completion_tokens": 50, "total_tokens": 250},
    )

    artifact = build_session_artifact(db_path, session["id"])

    assert artifact["token_log"][0]["usage_kind"] == "estimation"


def test_daily_budget_reset_moves_window_without_deleting_token_rows(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)
    set_token_budget_settings(db_path, daily_cap_tokens=1000, session_cap_tokens=500)
    session = create_session(
        db_path,
        task_description="Spend before reset",
        model="claude-haiku",
        session_key_hash="hash-before-reset",
        guardrail_overrides={},
    )
    record_token_turn(
        db_path,
        session_id=session["id"],
        model="claude-haiku",
        prompt_tokens=400,
        completion_tokens=100,
        cost=0.0,
        raw_usage={"total_tokens": 500, "spend_category": "worker_execution"},
    )
    reset_at = "2099-01-01T12:00:00+00:00"
    with connect(db_path) as conn:
        conn.execute("update token_turns set created_at = ?", ("2099-01-01T11:00:00+00:00",))

    saved = reset_daily_budget_counter(db_path, reset_at=reset_at)
    window_start = effective_daily_budget_window_start(
        db_path,
        timezone="UTC",
        now=datetime(2099, 1, 1, 13, 0, tzinfo=UTC),
    )

    with connect(db_path) as conn:
        token_rows = conn.execute("select count(*) from token_turns").fetchone()[0]
    assert saved["daily_usage_reset_at"] == reset_at
    assert window_start == reset_at
    assert token_rows == 1
    assert build_session_artifact(db_path, session["id"])["token_log"][0]["total_tokens"] == 500


def test_daily_budget_reset_from_previous_day_does_not_hide_new_day_usage(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)
    reset_daily_budget_counter(db_path, reset_at="2099-01-01T23:00:00+00:00")

    window_start = effective_daily_budget_window_start(
        db_path,
        timezone="UTC",
        now=datetime(2099, 1, 2, 9, 0, tzinfo=UTC),
    )

    assert window_start == "2099-01-02T00:00:00+00:00"


def test_saving_budget_settings_preserves_daily_reset_marker(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)
    reset_daily_budget_counter(db_path, reset_at="2099-01-01T12:00:00+00:00")

    saved = set_token_budget_settings(db_path, daily_cap_tokens=2000, session_cap_tokens=800)

    assert saved["daily_cap_tokens"] == 2000
    assert saved["session_cap_tokens"] == 800
    assert saved["daily_usage_reset_at"] == "2099-01-01T12:00:00+00:00"


def test_init_db_migrates_existing_token_turns_to_worker_usage_kind(tmp_path):
    db_path = tmp_path / "harness.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            create table sessions (
                id text primary key,
                task_description text not null,
                model text not null,
                session_key_hash text not null,
                started_at text not null,
                status text not null,
                guardrail_overrides_json text not null
            );
            create table token_turns (
                id integer primary key autoincrement,
                session_id text not null references sessions(id) on delete cascade,
                model text not null,
                prompt_tokens integer not null,
                completion_tokens integer not null,
                total_tokens integer not null,
                cost real not null,
                raw_usage_json text not null,
                created_at text not null
            );
            insert into sessions (
                id, task_description, model, session_key_hash, started_at, status,
                guardrail_overrides_json
            ) values (
                'sess_legacy', 'Legacy task', 'claude-haiku', 'legacy-hash',
                '2026-01-01T00:00:00+00:00', 'running', '{}'
            );
            insert into token_turns (
                session_id, model, prompt_tokens, completion_tokens, total_tokens,
                cost, raw_usage_json, created_at
            ) values (
                'sess_legacy', 'claude-haiku', 10, 5, 15, 0.01,
                '{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}',
                '2026-01-01T00:00:00+00:00'
            );
            """
        )

    init_db(db_path)

    artifact = build_session_artifact(db_path, "sess_legacy")
    with connect(db_path) as conn:
        token_turn_columns = {
            row["name"] for row in conn.execute("pragma table_info(token_turns)").fetchall()
        }

    assert "usage_kind" in token_turn_columns
    assert artifact["token_log"][0]["usage_kind"] == "worker"


def test_init_db_migrates_token_turn_cost_to_nullable_and_preserves_rows(tmp_path):
    db_path = tmp_path / "harness.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            create table sessions (
                id text primary key,
                task_description text not null,
                model text not null,
                session_key_hash text not null,
                started_at text not null,
                status text not null,
                guardrail_overrides_json text not null
            );
            create table token_turns (
                id integer primary key autoincrement,
                session_id text not null references sessions(id) on delete cascade,
                usage_kind text not null default 'worker',
                model text not null,
                prompt_tokens integer not null,
                completion_tokens integer not null,
                total_tokens integer not null,
                cost real not null,
                raw_usage_json text not null,
                created_at text not null
            );
            insert into sessions (
                id, task_description, model, session_key_hash, started_at, status,
                guardrail_overrides_json
            ) values (
                'sess_nullable_cost', 'Nullable cost migration', 'demo-model', 'demo-hash',
                '2099-01-01T00:00:00+00:00', 'completed', '{}'
            );
            insert into token_turns (
                session_id, usage_kind, model, prompt_tokens, completion_tokens,
                total_tokens, cost, raw_usage_json, created_at
            ) values (
                'sess_nullable_cost', 'estimation', 'demo-model', 10, 5, 15, 0.01,
                '{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}',
                '2099-01-01T00:00:01+00:00'
            );
            """
        )

    init_db(db_path)
    init_db(db_path)
    record_token_turn(
        db_path,
        session_id="sess_nullable_cost",
        usage_kind="estimation",
        model="unpriced-model",
        prompt_tokens=4,
        completion_tokens=2,
        cost=None,
        raw_usage={"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
    )

    with connect(db_path) as conn:
        cost_column = next(
            row for row in conn.execute("pragma table_info(token_turns)") if row["name"] == "cost"
        )
        rows = conn.execute("select model, cost from token_turns order by id").fetchall()

    assert cost_column["notnull"] == 0
    assert [(row["model"], row["cost"]) for row in rows] == [
        ("demo-model", 0.01),
        ("unpriced-model", None),
    ]


def test_estimation_accuracy_with_completed_tasks(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)

    # 5 tasks from spec scenario: estimates [500, 300, 1000, 200, 800], actuals [550, 280, 1400, 180, 750]
    scenarios = [
        (500, 550),   # ratio=1.10
        (300, 280),   # ratio=0.933
        (1000, 1400), # ratio=1.40
        (200, 180),   # ratio=0.90
        (800, 750),   # ratio=0.9375
    ]
    for estimate, actual in scenarios:
        create_task(
            db_path,
            description=f"Task est={estimate} actual={actual}",
            status="Done",
            estimate_tokens=estimate,
            actual_tokens=actual,
        )

    result = estimation_accuracy(db_path)
    assert result["completed_count"] == 5
    assert result["median_error_ratio"] == pytest.approx(0.94, abs=0.01)
    assert result["within_2x_pct"] == pytest.approx(100.0)


def test_estimation_accuracy_returns_nulls_when_no_completed_tasks(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)

    result = estimation_accuracy(db_path)
    assert result["completed_count"] is None
    assert result["median_error_ratio"] is None
    assert result["within_2x_pct"] is None


def test_token_usage_breakdown_aggregates_resolved_cost_and_coverage(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)
    session = create_session(
        db_path,
        task_description="cost coverage",
        model="mixed",
        session_key_hash="a" * 64,
        guardrail_overrides={},
        status="completed",
    )
    turns = [
        ("control_plane", 10, 0.02),
        ("task_breakdown", 5, None),
        ("worker_execution", 20, 0.10),
        ("adapter_verification", 3, None),
        ("reporting_summary", 2, 1.0),
        ("other", 1, None),
    ]
    for category, tokens, cost in turns:
        record_token_turn(
            db_path,
            session_id=session["id"],
            usage_kind="worker",
            model="mixed",
            prompt_tokens=tokens,
            completion_tokens=0,
            cost=cost,
            raw_usage={"total_tokens": tokens, "spend_category": category, "usage_source": "harness_proxy"},
        )

    breakdown = token_usage_breakdown(db_path)

    assert breakdown["total_tokens"] == 41
    assert breakdown["priced_tokens"] == 32
    assert breakdown["unpriced_tokens"] == 9
    assert breakdown["total_cost"] == pytest.approx(1.12)
    assert breakdown["cost_by_category"]["control_plane"] == pytest.approx(0.02)
    assert breakdown["cost_by_category"]["worker_execution"] == pytest.approx(0.10)
    assert breakdown["cost_by_category"]["reporting_summary"] == pytest.approx(1.0)
    assert breakdown["cost_by_category"]["task_breakdown"] is None
    assert breakdown["cost_by_category"]["adapter_verification"] is None
    assert breakdown["cost_by_category"]["other"] is None


def test_token_usage_breakdown_distinguishes_zero_priced_from_null_unpriced(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)
    session = create_session(
        db_path,
        task_description="zero vs null",
        model="mixed",
        session_key_hash="b" * 64,
        guardrail_overrides={},
        status="completed",
    )
    record_token_turn(
        db_path,
        session_id=session["id"],
        usage_kind="worker",
        model="mixed",
        prompt_tokens=4,
        completion_tokens=0,
        cost=0.0,
        raw_usage={"total_tokens": 4, "spend_category": "task_breakdown"},
    )
    record_token_turn(
        db_path,
        session_id=session["id"],
        usage_kind="worker",
        model="mixed",
        prompt_tokens=6,
        completion_tokens=0,
        cost=None,
        raw_usage={"total_tokens": 6, "spend_category": "control_plane"},
    )

    breakdown = token_usage_breakdown(db_path)

    assert breakdown["cost_by_category"]["task_breakdown"] == 0.0
    assert breakdown["cost_by_category"]["control_plane"] is None
    assert breakdown["total_cost"] == 0.0
    assert breakdown["priced_tokens"] == 4
    assert breakdown["unpriced_tokens"] == 6


def test_token_usage_breakdown_reports_null_total_cost_when_all_unpriced(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)
    session = create_session(
        db_path,
        task_description="all unpriced",
        model="unpriced",
        session_key_hash="c" * 64,
        guardrail_overrides={},
        status="completed",
    )
    for category, tokens in [("control_plane", 3), ("worker_execution", 4)]:
        record_token_turn(
            db_path,
            session_id=session["id"],
            usage_kind="worker",
            model="unpriced",
            prompt_tokens=tokens,
            completion_tokens=0,
            cost=None,
            raw_usage={"total_tokens": tokens, "spend_category": category},
        )

    breakdown = token_usage_breakdown(db_path)

    assert breakdown["total_tokens"] == 7
    assert breakdown["priced_tokens"] == 0
    assert breakdown["unpriced_tokens"] == 7
    assert breakdown["total_cost"] is None
    assert breakdown["cost_by_category"]["control_plane"] is None
    assert breakdown["cost_by_category"]["worker_execution"] is None


def test_estimation_accuracy_excludes_tasks_with_missing_actuals(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)

    # Task with estimate but no actual (still Estimated)
    create_task(db_path, description="No actual", status="Estimated", estimate_tokens=500, actual_tokens=None)
    # Task Done with both
    create_task(db_path, description="With actual", status="Done", estimate_tokens=500, actual_tokens=600)

    result = estimation_accuracy(db_path)
    assert result["completed_count"] == 1
    assert result["median_error_ratio"] == 1.2


def test_read_session_kind_defaults_to_worker_for_legacy_sessions(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)
    session = create_session(
        db_path,
        task_description="Legacy session",
        model="claude-haiku",
        session_key_hash="legacy-hash",
        guardrail_overrides={},
    )

    assert db.read_session_kind(session) == "worker"
    assert session["guardrail_overrides"] == {}


def test_create_planning_session_returns_bearer_key_and_kind(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)

    session, bearer_key = db.create_planning_session(
        db_path,
        task_description="Planning anchor",
        model="claude-haiku",
    )

    assert db.read_session_kind(session) == "planning"
    assert session["guardrail_overrides"]["session_kind"] == "planning"
    assert bearer_key.startswith("sk_plan_")
    loaded = db.get_session_by_key_hash(db_path, session["session_key_hash"])
    assert db.read_session_kind(loaded) == "planning"


def test_list_sessions_excludes_planning_by_default(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)
    worker_session = create_session(
        db_path,
        task_description="Worker session",
        model="claude-haiku",
        session_key_hash="worker-hash",
        guardrail_overrides={},
    )
    planning_session, _ = db.create_planning_session(
        db_path,
        task_description="Planning session",
        model="claude-haiku",
    )

    assert db.read_session_kind(worker_session) == "worker"
    assert db.read_session_kind(planning_session) == "planning"
    assert db.list_sessions(db_path) == [worker_session]
    assert len(db.list_sessions(db_path, kind=None)) == 2


def test_planning_token_turn_spend_category_and_usage_source(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)
    session = create_session(
        db_path,
        task_description="Planning spend",
        model="claude-haiku",
        session_key_hash="planning-hash",
        guardrail_overrides={"session_kind": "planning"},
    )

    record_token_turn(
        db_path,
        session_id=session["id"],
        usage_kind="planning",
        model="claude-haiku",
        prompt_tokens=100,
        completion_tokens=50,
        cost=0.001,
        raw_usage={"total_tokens": 150},
    )

    artifact = build_session_artifact(db_path, session["id"])
    turn = artifact["token_log"][0]
    assert turn["usage_kind"] == "planning"
    assert turn["raw_usage"]["spend_category"] == "planning"
    assert turn["raw_usage"]["usage_source"] == "harness_proxy"

    breakdown = token_usage_breakdown(db_path)
    assert breakdown["by_category"]["other"] == 150
    assert breakdown["by_category"]["worker_execution"] == 0
    assert breakdown["by_source"]["harness_proxy"] == 150
    assert db.budgeted_token_usage(db_path) == 150


def test_token_usage_breakdown_keeps_six_fixed_keys_and_rolls_up_planning(tmp_path):
    db_path = tmp_path / "harness.db"
    init_db(db_path)
    session = create_session(
        db_path,
        task_description="Fixed key rollup",
        model="claude-haiku",
        session_key_hash="rollup-hash",
        guardrail_overrides={"session_kind": "planning"},
    )
    record_token_turn(
        db_path,
        session_id=session["id"],
        usage_kind="planning",
        model="claude-haiku",
        prompt_tokens=1,
        completion_tokens=0,
        cost=None,
        raw_usage={"total_tokens": 1},
    )

    breakdown = token_usage_breakdown(db_path)

    assert set(breakdown["by_category"].keys()) == {
        "control_plane",
        "task_breakdown",
        "worker_execution",
        "adapter_verification",
        "reporting_summary",
        "other",
    }
    assert breakdown["by_category"]["other"] == 1
    assert db.budgeted_token_usage(db_path) == 1
