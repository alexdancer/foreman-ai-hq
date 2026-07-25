"""Unit tests for the pi orchestrator launch wiring."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from foreman_ai_hq import db
import foreman_ai_hq.pi_adapter as _pi_adapter
from foreman_ai_hq.native_usage import (
    extract_pi_successful_tool_calls,
    parse_pi_usage_stream,
)
from foreman_ai_hq.pi_adapter import (
    DEFAULT_PROFILE_DIR,
    PI_ORCHESTRATOR_ALLOWED_TOOLS,
    PiStructuredJobError,
    PiStructuredOutputError,
    _write_pi_acp_wrapper,
    launch_pi_once,
    run_pi_structured_job,
)


def _pi_assistant_message(response_id: str, *, input_tokens: int, output_tokens: int, cost: float) -> dict:
    """One assistant message as pi 0.82 emits it in ``--mode json`` (captured shape)."""
    return {
        "role": "assistant",
        "api": "openai-responses",
        "provider": "openai-codex",
        "model": "gpt-5.4",
        "responseId": response_id,
        "stopReason": "stop",
        "timestamp": "2026-07-25T01:04:03.000Z",
        "content": [{"type": "text", "text": "OK"}],
        "usage": {
            "input": input_tokens,
            "output": output_tokens,
            "cacheRead": 0,
            "cacheWrite": 0,
            "reasoning": 13,
            "totalTokens": input_tokens + output_tokens,
            "cost": {"input": cost, "output": 0.0, "cacheRead": 0, "cacheWrite": 0, "total": cost},
        },
    }


def _pi_stream(*messages: dict, with_usage: bool = True) -> str:
    """Render a pi ``--mode json`` stream: session header, then message_end + turn_end per call.

    pi repeats the same message (same ``responseId``) on ``message_end`` and
    ``turn_end``; the parser must count that call once.
    """
    lines: list[dict] = [{"type": "session", "version": 3, "id": "sess-json"}, {"type": "agent_start"}]
    for message in messages:
        lines.append({"type": "message_end", "message": message})
        lines.append({"type": "turn_end", "turnIndex": 0, "message": message, "toolResults": []})
    if not with_usage:
        lines = [line for line in lines if line["type"] in {"session", "agent_start"}]
    lines.append({"type": "agent_end"})
    return "".join(f"{json.dumps(line)}\n" for line in lines)


def test_pi_usage_stream_counts_a_repeated_message_once() -> None:
    stream = _pi_stream(_pi_assistant_message("resp_1", input_tokens=38808, output_tokens=20, cost=0.09732))

    evidence = parse_pi_usage_stream(stream, model="gpt-5.4")

    assert evidence is not None
    assert evidence.prompt_tokens == 38808
    assert evidence.completion_tokens == 20
    assert evidence.total_tokens == 38828
    assert evidence.cost == 0.09732
    assert evidence.raw_usage["response_ids"] == ["resp_1"]
    assert evidence.raw_usage["provider"] == "openai-codex"


def test_pi_usage_stream_sums_multiple_model_calls_in_one_turn() -> None:
    stream = _pi_stream(
        _pi_assistant_message("resp_1", input_tokens=1000, output_tokens=10, cost=0.01),
        _pi_assistant_message("resp_2", input_tokens=2000, output_tokens=20, cost=0.02),
    )

    evidence = parse_pi_usage_stream(stream, model="gpt-5.4")

    assert evidence is not None
    assert evidence.prompt_tokens == 3000
    assert evidence.completion_tokens == 30
    assert evidence.total_tokens == 3030
    assert evidence.raw_usage["response_ids"] == ["resp_1", "resp_2"]


def test_pi_usage_stream_excludes_already_recorded_calls() -> None:
    stream = _pi_stream(
        _pi_assistant_message("resp_1", input_tokens=1000, output_tokens=10, cost=0.01),
        _pi_assistant_message("resp_2", input_tokens=2000, output_tokens=20, cost=0.02),
    )

    evidence = parse_pi_usage_stream(stream, model="gpt-5.4", exclude_response_ids={"resp_1"})

    assert evidence is not None
    assert evidence.prompt_tokens == 2000
    assert evidence.raw_usage["response_ids"] == ["resp_2"]


def test_pi_usage_stream_without_usage_yields_no_evidence() -> None:
    assert parse_pi_usage_stream(_pi_stream(with_usage=False), model="gpt-5.4") is None
    assert parse_pi_usage_stream("", model="gpt-5.4") is None


def _pi_submit_stream(tool_name: str, arguments: dict, *, call_id: str = "call_submit") -> str:
    message = _pi_assistant_message(
        "resp_submit", input_tokens=1200, output_tokens=30, cost=0.02
    )
    message["content"] = [
        {"type": "toolCall", "id": call_id, "name": tool_name, "arguments": arguments}
    ]
    events = [
        {"type": "session", "version": 3, "id": "sess-json"},
        {"type": "agent_start"},
        {"type": "message_end", "message": message},
        {
            "type": "tool_execution_start",
            "toolCallId": call_id,
            "toolName": tool_name,
            "args": arguments,
        },
        {
            "type": "tool_execution_end",
            "toolCallId": call_id,
            "toolName": tool_name,
            "result": {"content": [{"type": "text", "text": "submitted"}]},
            "isError": False,
        },
        {"type": "turn_end", "turnIndex": 0, "message": message, "toolResults": []},
        {"type": "agent_end"},
    ]
    return "".join(f"{json.dumps(event)}\n" for event in events)


def test_pi_successful_tool_call_extraction_requires_successful_execution() -> None:
    stream = _pi_submit_stream("submit_estimate", {"confidence": 0.8})

    assert extract_pi_successful_tool_calls(stream, tool_name="submit_estimate") == [
        {"confidence": 0.8}
    ]
    assert extract_pi_successful_tool_calls(stream, tool_name="submit_breakdown") == []

    failed = stream.replace('"isError": false', '"isError": true')
    assert extract_pi_successful_tool_calls(failed, tool_name="submit_estimate") == []


def test_auth_error_detection_matches_pi_wording_only() -> None:
    # Captured verbatim from pi 0.82: ACP session/new, and `pi -p` on a keyless provider.
    assert _pi_adapter._is_auth_error(
        "ACP session/new failed: {'code': -32000, 'message': 'Authentication required: "
        "Configure an API key or log in with an OAuth provider.'}"
    )
    assert _pi_adapter._is_auth_error(
        "No API key found for azure-openai-responses.\n\nUse /login to log into a provider "
        "via OAuth or API key."
    )

    # An unrelated failure must surface as itself, not as a sign-in prompt.
    assert not _pi_adapter._is_auth_error("ACP session/prompt timed out")
    assert not _pi_adapter._is_auth_error("cannot read /repo/authors.md: permission denied")
    assert not _pi_adapter._is_auth_error("failed to author the summary")


class _StubTransport:
    """Minimal ACP transport stub that fails every call with a fixed message."""

    def __init__(self, message: str) -> None:
        self.message = message

    def call(self, method, params, *, timeout=None):
        raise _pi_adapter.AcpRuntimeError(self.message)


def _conversation_with_transport(tmp_path, transport) -> _pi_adapter.PiConversation:
    return _pi_adapter.PiConversation(
        session={"id": "sess_test"},
        proc=mock.Mock(),
        transport=transport,
        session_id="acp-1",
        default_timeout=1,
        workdir=tmp_path,
        database_path=tmp_path / "harness.db",
        model="gpt-5.4",
        sessions_dir=tmp_path / "sessions",
    )


def test_prompt_maps_expired_provider_auth_to_pi_auth_required(tmp_path) -> None:
    conv = _conversation_with_transport(
        tmp_path,
        _StubTransport(
            "ACP session/prompt failed: {'code': -32000, 'message': 'Authentication required: "
            "Configure an API key or log in with an OAuth provider.'}"
        ),
    )

    with pytest.raises(_pi_adapter.PiAuthRequired):
        conv.prompt("plan this")


def test_prompt_leaves_an_unrelated_acp_failure_as_itself(tmp_path) -> None:
    conv = _conversation_with_transport(tmp_path, _StubTransport("ACP session/prompt timed out"))

    with pytest.raises(_pi_adapter.AcpRuntimeError):
        conv.prompt("plan this")


def _fake_pi_run(monkeypatch, stdout: str) -> dict[str, object]:
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["args"] = command
        return mock.Mock(returncode=0, stdout=stdout, stderr="", args=command)

    monkeypatch.setattr(_pi_adapter.subprocess, "run", fake_run)
    return captured


def test_launch_pi_once_records_one_planning_turn_from_native_usage(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    _fake_pi_run(
        monkeypatch,
        _pi_stream(_pi_assistant_message("resp_1", input_tokens=38808, output_tokens=20, cost=0.09732)),
    )

    session, result = launch_pi_once(database_path, "hi", profile_dir=DEFAULT_PROFILE_DIR, timeout=1)

    assert result.stdout == "OK"
    token_log = db.build_session_artifact(database_path, session["id"])["token_log"]
    assert len(token_log) == 1
    turn = token_log[0]
    assert turn["usage_kind"] == "planning"
    assert turn["prompt_tokens"] == 38808
    assert turn["completion_tokens"] == 20
    assert turn["raw_usage"]["spend_category"] == "planning"
    assert turn["raw_usage"]["usage_source"] == "native_usage"
    assert turn["raw_usage"]["tracking_mode"] == "native_usage"


def test_launch_pi_once_without_usage_evidence_records_no_spend(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    _fake_pi_run(monkeypatch, _pi_stream(with_usage=False))

    session, _result = launch_pi_once(database_path, "hi", profile_dir=DEFAULT_PROFILE_DIR, timeout=1)

    assert db.build_session_artifact(database_path, session["id"])["token_log"] == []


def test_orchestrator_allowed_tools_allows_read_only_set() -> None:
    assert PI_ORCHESTRATOR_ALLOWED_TOOLS == ("read", "grep", "find", "ls")
    assert "bash" not in PI_ORCHESTRATOR_ALLOWED_TOOLS
    assert "edit" not in PI_ORCHESTRATOR_ALLOWED_TOOLS
    assert "write" not in PI_ORCHESTRATOR_ALLOWED_TOOLS


def test_acp_wrapper_includes_tool_allowlist_and_model_env() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        persona = Path(tmpdir) / "orchestrator.md"
        persona.write_text("test", encoding="utf-8")
        sessions_dir = Path(tmpdir) / "sessions"
        wrapper = _write_pi_acp_wrapper(
            Path(tmpdir), persona, sessions_dir, "openai-codex", "gpt-5.4"
        )
        text = wrapper.read_text()

        assert '--tools "$PI_ACP_ALLOWED_TOOLS"' in text
        assert '--model "$PI_ACP_MODEL"' in text
        assert '--session-dir "$PI_ACP_SESSION_DIR"' in text
        assert '--provider "$PI_ACP_PROVIDER"' in text
        assert "bash" not in text
        assert "edit" not in text
        assert "write" not in text
        assert wrapper.stat().st_mode & 0o111


def test_acp_wrapper_omits_provider_when_unset() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        persona = Path(tmpdir) / "orchestrator.md"
        persona.write_text("test", encoding="utf-8")
        sessions_dir = Path(tmpdir) / "sessions"
        wrapper = _write_pi_acp_wrapper(
            Path(tmpdir), persona, sessions_dir, None, "gpt-5.4"
        )
        text = wrapper.read_text()

        assert "--provider" not in text
        assert '--model "$PI_ACP_MODEL"' in text


@pytest.mark.asyncio
async def test_structured_job_records_native_usage_and_enforces_isolated_submit_tool(
    monkeypatch, tmp_path
) -> None:
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    submitted = {"drivers": {"files_to_read": 1}}
    stream = _pi_submit_stream("submit_estimate", submitted)
    captured: dict[str, object] = {}

    class FakeProcess:
        pid = 999999
        returncode = 0

        async def communicate(self):
            return stream.encode(), b""

        async def wait(self):
            return self.returncode

    async def fake_exec(*args, **kwargs):
        captured["args"] = list(args)
        captured["cwd"] = kwargs["cwd"]
        captured["input"] = json.loads(
            (Path(kwargs["cwd"]) / "job-input.json").read_text(encoding="utf-8")
        )
        return FakeProcess()

    monkeypatch.setattr(_pi_adapter.asyncio, "create_subprocess_exec", fake_exec)

    result = await run_pi_structured_job(
        database_path,
        instructions="Estimate from curated context.",
        input_payload={"task_description": "DEMO_TASK_2099"},
        model="openai-codex/gpt-5.4",
        persona_filename="estimator.md",
        extension_filename="submit-estimate.ts",
        submit_tool="submit_estimate",
        usage_kind="estimation",
        task_description="Task estimation: DEMO_TASK_2099",
        agent_dir=tmp_path / "agent",
    )

    assert result.arguments == submitted
    assert result.validated == submitted
    assert result.session["status"] == "completed"
    assert result.session["model"] == "openai-codex/gpt-5.4"
    assert captured["input"] == {
        "input": {"task_description": "DEMO_TASK_2099"},
        "instructions": "Estimate from curated context.",
    }
    args = captured["args"]
    assert "--no-extensions" in args
    assert "--extension" in args
    assert "--no-context-files" in args
    tools = args[args.index("--tools") + 1]
    assert tools == "read_curated_input,submit_estimate"
    assert all(
        name not in tools.split(",")
        for name in ("read", "grep", "find", "ls", "bash", "edit", "write")
    )
    assert not Path(captured["cwd"]).exists()

    artifact = db.build_session_artifact(database_path, result.session["id"])
    assert len(artifact["token_log"]) == 1
    assert artifact["token_log"][0]["usage_kind"] == "estimation"
    assert artifact["token_log"][0]["raw_usage"]["usage_source"] == "native_usage"


@pytest.mark.asyncio
async def test_structured_job_domain_validation_fails_session(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    stream = _pi_submit_stream("submit_estimate", {"confidence": 0.8})

    class FakeProcess:
        pid = 999999
        returncode = 0

        async def communicate(self):
            return stream.encode(), b""

        async def wait(self):
            return self.returncode

    async def fake_exec(*_args, **_kwargs):
        return FakeProcess()

    def reject(_arguments):
        raise ValueError("semantic contract mismatch")

    monkeypatch.setattr(_pi_adapter.asyncio, "create_subprocess_exec", fake_exec)

    with pytest.raises(PiStructuredOutputError, match="semantic contract mismatch") as raised:
        await run_pi_structured_job(
            database_path,
            instructions="Estimate.",
            input_payload={"task": "DEMO_TASK_2099"},
            model="gpt-5.4",
            persona_filename="estimator.md",
            extension_filename="submit-estimate.ts",
            submit_tool="submit_estimate",
            usage_kind="estimation",
            task_description="Task estimation: DEMO_TASK_2099",
            result_validator=reject,
            agent_dir=tmp_path / "agent",
        )

    session = db.get_session(database_path, raised.value.session_id)
    assert session["status"] == "failed"
    assert db.session_token_usage(database_path, session["id"]) == 1230


@pytest.mark.asyncio
async def test_structured_job_without_submit_records_spend_then_fails(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    stream = _pi_stream(
        _pi_assistant_message("resp_1", input_tokens=1000, output_tokens=10, cost=0.01)
    )

    class FakeProcess:
        pid = 999999
        returncode = 0

        async def communicate(self):
            return stream.encode(), b""

        async def wait(self):
            return self.returncode

    async def fake_exec(*_args, **_kwargs):
        return FakeProcess()

    monkeypatch.setattr(_pi_adapter.asyncio, "create_subprocess_exec", fake_exec)

    with pytest.raises(PiStructuredOutputError, match="exactly once; got 0"):
        await run_pi_structured_job(
            database_path,
            instructions="Estimate.",
            input_payload={"task": "DEMO_TASK_2099"},
            model="gpt-5.4",
            persona_filename="estimator.md",
            extension_filename="submit-estimate.ts",
            submit_tool="submit_estimate",
            usage_kind="estimation",
            task_description="Task estimation: DEMO_TASK_2099",
            agent_dir=tmp_path / "agent",
        )

    session = db.list_sessions(database_path, kind=None)[0]
    assert session["status"] == "failed"
    assert db.session_token_usage(database_path, session["id"]) == 1010


@pytest.mark.asyncio
async def test_structured_job_timeout_preserves_already_emitted_native_usage(
    monkeypatch, tmp_path
) -> None:
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    stream = _pi_stream(
        _pi_assistant_message("resp_1", input_tokens=1000, output_tokens=10, cost=0.01)
    )

    class FakeProcess:
        pid = 999999
        returncode = None

        def __init__(self):
            self.stopped = asyncio.Event()

        async def communicate(self):
            await self.stopped.wait()
            return stream.encode(), b"pi: provider stalled waiting for first token\n"

        async def wait(self):
            self.returncode = -9
            self.stopped.set()
            return self.returncode

    async def fake_exec(*_args, **_kwargs):
        return FakeProcess()

    monkeypatch.setattr(_pi_adapter.asyncio, "create_subprocess_exec", fake_exec)

    # A hung run must be diagnosable after the fact: how long it ran, its limit, and
    # what pi last said on stderr.
    with pytest.raises(
        PiStructuredJobError, match=r"timed out after \d+\.\d+s \(limit 0s\)"
    ) as timeout_error:
        await run_pi_structured_job(
            database_path,
            instructions="Estimate.",
            input_payload={"task": "DEMO_TASK_2099"},
            model="gpt-5.4",
            persona_filename="estimator.md",
            extension_filename="submit-estimate.ts",
            submit_tool="submit_estimate",
            usage_kind="estimation",
            task_description="Task estimation: DEMO_TASK_2099",
            timeout=0.001,
            agent_dir=tmp_path / "agent",
        )

    assert "provider stalled waiting for first token" in str(timeout_error.value)

    session = db.list_sessions(database_path, kind=None)[0]
    assert session["status"] == "failed"
    assert db.session_token_usage(database_path, session["id"]) == 1010


def test_stderr_tail_is_bounded_and_single_line() -> None:
    assert _pi_adapter._stderr_tail("") == "<empty>"
    assert _pi_adapter._stderr_tail("  \n \n ") == "<empty>"
    assert _pi_adapter._stderr_tail("first line\nsecond line\n") == "first line second line"
    assert len(_pi_adapter._stderr_tail("x" * 5000)) == 300


def test_launch_pi_once_appends_tool_allowlist(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)

    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["args"] = command
        return mock.Mock(returncode=0, stdout="", stderr="", args=command)

    monkeypatch.setattr(_pi_adapter.subprocess, "run", fake_run)

    launch_pi_once(
        database_path,
        "hi",
        profile_dir=DEFAULT_PROFILE_DIR,
        timeout=1,
    )

    args = captured["args"]
    assert isinstance(args, list)
    assert "--tools" in args
    tools_idx = args.index("--tools")
    assert args[tools_idx + 1] == ",".join(PI_ORCHESTRATOR_ALLOWED_TOOLS)

    joined = " ".join(map(str, args))
    assert "bash" not in joined
    assert "edit" not in joined
    assert "write" not in joined
    assert "--append-system-prompt" in args
    assert "--mode" in args
    assert "json" in args
