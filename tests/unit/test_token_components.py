from foreman_ai_hq import db
from foreman_ai_hq.native_usage import token_usage_components


def test_token_usage_components_normalizes_provider_aliases():
    claude = token_usage_components(
        {
            "input_tokens": 10,
            "cache_read_input_tokens": 20,
            "cache_creation_input_tokens": 30,
            "output_tokens": 40,
            "total_tokens": 100,
            "cost_usd": 0.12,
        }
    )
    openai = token_usage_components(
        {"input_tokens": 100, "prompt_tokens_details": {"cached_tokens": 70}},
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
    )
    openai_reasoning_detail = token_usage_components(
        {
            "input_tokens": 100,
            "prompt_tokens_details": {"cached_tokens": 70},
            "completion_tokens": 20,
            "completion_tokens_details": {"reasoning_tokens": 5},
            "total_tokens": 120,
        }
    )
    opencode = token_usage_components(
        {"tokens": {"input": 5, "cache": {"read": 2, "write": 3}, "output": 4, "reasoning": 1, "total": 15}}
    )
    usage_cache = token_usage_components({"usage": {"input": 4, "cache": {"read": 6, "creation": 7}, "output": 8, "total_tokens": 25}})
    native_claude_envelope = token_usage_components(
        {
            "usage": {
                "input_tokens": 10,
                "cache_read_input_tokens": 20,
                "cache_creation_input_tokens": 30,
                "output_tokens": 40,
                "total_tokens": 100,
            }
        },
        prompt_tokens=60,
        completion_tokens=40,
        total_tokens=100,
    )
    missing = token_usage_components({"total_tokens": 10})
    partial = token_usage_components({"input_tokens": 5, "output_tokens": 2, "total_tokens": 10})

    assert claude["fresh_input"] == 10
    assert claude["cache_read"] == 20
    assert claude["cache_write"] == 30
    assert claude["output"] == 40
    assert claude["normalized_actual"] == 80
    assert claude["provider_raw_total"] == 100
    assert claude["cost"] == 0.12
    assert openai["fresh_input"] == 30
    assert openai["cache_read"] == 70
    assert openai["output"] == 20
    assert openai["normalized_actual"] == 50
    assert openai_reasoning_detail["reasoning"] == 5
    assert openai_reasoning_detail["normalized_actual"] == 50
    assert opencode["fresh_input"] == 5
    assert opencode["cache_read"] == 2
    assert opencode["cache_write"] == 3
    assert opencode["reasoning"] == 1
    assert usage_cache["cache_read"] == 6
    assert usage_cache["cache_write"] == 7
    assert native_claude_envelope["fresh_input"] == 10
    assert native_claude_envelope["cache_read"] == 20
    assert native_claude_envelope["cache_write"] == 30
    assert native_claude_envelope["output"] == 40
    assert missing["available"] is False
    assert missing["fresh_input"] is None
    assert partial["unclassified"] == 3
    assert partial["normalized_actual"] == 10


def test_token_usage_components_rejects_invalid_costs_and_preserves_zero():
    for invalid in (-0.01, float("nan"), float("inf"), float("-inf")):
        assert token_usage_components({"cost_usd": invalid})["cost"] is None
        assert token_usage_components({}, cost=invalid)["cost"] is None

    assert token_usage_components({"cost_usd": 0.0})["cost"] == 0.0
    assert token_usage_components({"cost_usd": 0.25}, cost=0.0)["cost"] == 0.0
    assert token_usage_components({"cost_usd": 0.25})["cost"] == 0.25


def test_worker_execution_token_summary_splits_completed_failed_and_components(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    done_session = db.create_session(
        db_path,
        task_description="Done Worker slice",
        model="opencode/gpt-5.1",
        session_key_hash="done-hash",
        guardrail_overrides={},
        status="completed",
    )
    failed_session = db.create_session(
        db_path,
        task_description="Retry Worker slice",
        model="opencode/gpt-5.1",
        session_key_hash="failed-hash",
        guardrail_overrides={},
        status="failed",
    )
    done_task = db.create_task(db_path, description="Done Worker slice", status="Review", actual_tokens=100)
    failed_task = db.create_task(db_path, description="Retry Worker slice", status="Estimated")
    done_run = db.create_worker_run(
        db_path,
        task_id=done_task["id"],
        session_id=done_session["id"],
        adapter_id="opencode",
        model="opencode/gpt-5.1",
        tracking_mode="native_usage",
        command_plan={"command": ["opencode", "run"]},
    )
    failed_run = db.create_worker_run(
        db_path,
        task_id=failed_task["id"],
        session_id=failed_session["id"],
        adapter_id="opencode",
        model="opencode/gpt-5.1",
        tracking_mode="native_usage",
        command_plan={"command": ["opencode", "run"]},
    )
    db.mark_worker_run_completed(db_path, done_run["id"], returncode=0)
    db.mark_worker_run_failed(db_path, failed_run["id"], error_type="worker_adapter_failure", error_message="retry", returncode=1)
    db.record_token_turn(
        db_path,
        session_id=done_session["id"],
        usage_kind="task_execution",
        model="opencode/gpt-5.1",
        prompt_tokens=60,
        completion_tokens=40,
        cost=0.0,
        raw_usage={"input_tokens": 50, "cache_read_input_tokens": 10, "output_tokens": 40, "total_tokens": 100},
    )
    db.record_token_turn(
        db_path,
        session_id=failed_session["id"],
        usage_kind="task_execution",
        model="opencode/gpt-5.1",
        prompt_tokens=9,
        completion_tokens=1,
        cost=0.0,
        raw_usage={"input_tokens": 9, "output_tokens": 1, "total_tokens": 10},
    )

    summary = db.worker_execution_token_summary(db_path)

    assert summary["status_split"] == {"completed": 90, "failed_retry": 10, "unknown": 0}
    assert {item["key"]: item["value"] for item in summary["components"]["items"]} == {
        "normalized_actual": 100,
        "provider_raw_total": 110,
        "fresh_input": 59,
        "cache_read": 10,
        "output": 41,
    }
