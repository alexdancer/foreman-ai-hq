import json
import sys
import time

from foreman_ai_hq import db
from foreman_ai_hq.native_usage import parse_native_usage_evidence
from foreman_ai_hq.project_context import project_task_metadata
from foreman_ai_hq.stream_events import streaming_runner
from foreman_ai_hq.task_launch import launch_task
from foreman_ai_hq.worker_adapters import CommandPlan, get_adapter_builder
from tests.conftest import git_project_profile


def _verified_native_task(db_path, root):
    db.init_db(db_path)
    project = db.upsert_connected_project(
        db_path,
        name="DEMO 999 stream project",
        root_path=str(root),
        profile=git_project_profile(root, name="DEMO 999 stream project"),
        capability={"state": "launch_ready", "can_launch": True},
    )
    db.update_worker_adapter(
        db_path,
        "opencode",
        workdir=str(root),
        config={"command": "opencode"},
        supported_models=["opencode/gpt-5.1"],
        is_default=True,
    )
    db.mark_worker_adapter_verification(
        db_path,
        "opencode",
        verified=True,
        evidence={"tracking_mode": "native_usage", "tracking_authoritative": True},
    )
    return db.create_task(
        db_path,
        description="DEMO 2099 streamed Worker Run",
        status="Estimated",
        estimate_tokens=20,
        recommended_model="opencode/gpt-5.1",
        metadata={
            **project_task_metadata(project),
            "budget": {"daily_used_tokens": 0, "daily_cap_tokens": 100, "session_cap_tokens": 100},
        },
    )


def _wait_for_run(db_path, task_id, status):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        runs = db.list_worker_runs(db_path, task_id=task_id)
        if runs and runs[-1]["status"] == status:
            return runs[-1]
        time.sleep(0.01)
    raise AssertionError("Worker Run did not finish")


def test_adapter_stream_mappers_normalize_and_redact_representative_lines():
    adapter = {"id": "adapter", "name": "DEMO adapter", "workdir": None, "config": {}, "supported_models": []}
    cases = [
        ("claude_code", {"type": "assistant", "message": {"content": [{"type": "text", "text": "hello sk_live_secret"}]}}, "agent_message"),
        ("codex", {"type": "item.completed", "item": {"type": "command_execution", "command": "pytest", "arguments": {"token": "DEMO_SECRET_999"}}}, "tool_call"),
        ("opencode", {"type": "step_finish", "usage": {"input_tokens": 3, "output_tokens": 2, "total_tokens": 5}}, "token"),
    ]

    for kind, payload, expected_kind in cases:
        event = get_adapter_builder({**adapter, "kind": kind}).map_stream_event(json.dumps(payload))
        assert event is not None
        assert event["kind"] == expected_kind
        assert "sk_live_secret" not in json.dumps(event)
        assert "DEMO_SECRET_999" not in json.dumps(event)

    assert get_adapter_builder({**adapter, "kind": "opencode"}).map_stream_event("not json") is None


def test_streaming_runner_preserves_stdout_for_final_native_usage_parse(tmp_path):
    lines = [
        "not-json\n",
        json.dumps({"type": "complete", "model": "opencode/gpt-5.1", "session_id": "DEMO_999", "usage": {"input_tokens": 12, "output_tokens": 3, "total_tokens": 15, "cost": 0.01}}) + "\n",
    ]
    script = "import sys; sys.stdout.write(" + repr("".join(lines)) + "); sys.stderr.write('DEMO stderr')"
    seen = []
    plan = CommandPlan(command=[sys.executable, "-c", script], cwd=tmp_path, env={}, metadata={"timeout_seconds": 5})

    result = streaming_runner(plan, seen.append)

    assert result.returncode == 0
    assert result.stdout == "".join(lines)
    assert result.stderr == "DEMO stderr"
    assert seen == lines
    usage = parse_native_usage_evidence(result.stdout, model="opencode/gpt-5.1", returncode=result.returncode)
    assert usage is not None
    assert usage.total_tokens == 15


def test_streamed_launch_records_events_without_changing_final_actuals(tmp_path):
    db_path = tmp_path / "harness.db"
    (tmp_path / "DEMO_LONG_PROMPT.md").write_text("MULTILINE PROMPT CONTENT\n" * 200, encoding="utf-8")
    task = _verified_native_task(db_path, tmp_path)
    final = json.dumps({
        "type": "complete",
        "model": "opencode/gpt-5.1",
        "session_id": "DEMO_999",
        "usage": {"input_tokens": 12, "output_tokens": 3, "total_tokens": 15, "cost": 0.01},
    })
    prompt_holder = {}

    def runner(plan, on_event):
        # Write-capable runs need a real change, otherwise the diff check blocks them.
        (tmp_path / "worker_change.txt").write_text("changed\n", encoding="utf-8")
        prompt_index = plan.metadata["prompt_argument_indices"][0]
        prompt = plan.command[prompt_index] + ("\nMULTILINE PROMPT CONTENT" * 200)
        plan.command[prompt_index] = prompt
        prompt_holder["value"] = prompt
        on_event(json.dumps({"type": "text", "part": {"text": prompt}}) + "\n")
        on_event(json.dumps({"type": "tool", "part": {"tool": "write", "input": {"prompt": prompt}}}) + "\n")
        on_event(final + "\n")
        return {"returncode": 0, "stdout": final, "stderr": ""}

    launched = launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)  # type: ignore[arg-type]
    run = _wait_for_run(db_path, task["id"], "completed")
    events = db.list_worker_run_events(db_path, worker_run_id=run["id"])
    completed = db.get_task(db_path, task["id"])

    assert launched.task["status"] == "Running"
    assert completed["status"] == "Review"
    assert completed["actual_tokens"] == 15
    streamed_prompt = next(event["detail"]["text"] for event in events if event["kind"] == "agent_message")
    assert streamed_prompt != prompt_holder["value"]
    assert "PROMPT_REDACTED" in streamed_prompt
    streamed_tool = next(event["detail"]["arguments"] for event in events if event["kind"] == "tool_call")
    assert "MULTILINE PROMPT CONTENT" not in streamed_tool
    assert "PROMPT_REDACTED" in streamed_tool
    streamed = [(event["kind"], event["layer"]) for event in events if event["kind"] in {"agent_message", "token"}]
    assert streamed[:2] == [
        ("agent_message", "worker_harness"),
        ("token", "worker_harness"),
    ]
    assert streamed[-1] == ("token", "worker_harness")  # Final authoritative usage evidence.


def test_streamed_retryable_failure_stays_launchable(tmp_path):
    db_path = tmp_path / "harness.db"
    task = _verified_native_task(db_path, tmp_path)

    def runner(plan, on_event):
        on_event(json.dumps({"type": "error", "message": "DEMO adapter failure"}) + "\n")
        return {"returncode": 1, "stdout": "", "stderr": "DEMO failure"}

    launch_task(db_path, task["id"], adapter_id="opencode", model=None, proxy_url=None, runner=runner)  # type: ignore[arg-type]
    run = _wait_for_run(db_path, task["id"], "failed")

    assert db.get_task(db_path, task["id"])["status"] == "Estimated"
    assert any(event["kind"] == "status" and event["layer"] == "worker_harness" for event in db.list_worker_run_events(db_path, worker_run_id=run["id"]))
