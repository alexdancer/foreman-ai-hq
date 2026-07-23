"""ACP conversational pi launch: prove multi-turn governance through the Harness Proxy.

This test requires the `pi` CLI and Node.js to be installed. It starts a real
uvicorn server with a fake streaming LLM client and drives pi over ACP through
`foreman_ai_hq.pi_adapter.launch_pi_conversation`.
"""

from __future__ import annotations

import asyncio
import contextlib
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import pytest
import uvicorn

from foreman_ai_hq import db
from foreman_ai_hq.app import create_app
import foreman_ai_hq.pi_adapter as _pi_adapter
from foreman_ai_hq.pi_adapter import DEFAULT_PROFILE_DIR, launch_pi_conversation
from foreman_ai_hq.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATOR_PERSONA_MARKER = "FOREMAN_AI_HQ_ORCHESTRATOR_V1"


class FakePiLLMClient:
    """Streaming fake that returns a finished one-token turn."""

    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    async def acompletion(self, request: dict[str, object]):
        self.requests.append(request)

        async def chunks():
            model = request.get("model", "proxy")
            yield {
                "id": "chunk-1",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [
                    {"index": 0, "delta": {"content": "ok"}, "finish_reason": None}
                ],
            }
            yield {
                "id": "chunk-2",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [
                    {"index": 0, "delta": {}, "finish_reason": "stop"}
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            }

        return chunks()


def _pi_rpc_processes() -> list[str]:
    """Return any surviving ``pi --mode rpc`` process command lines."""
    result = subprocess.run(
        ["pgrep", "-af", "pi --mode rpc"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if "pgrep" not in line]


def test_acp_conversation_records_two_planning_turns_and_cleans_up(
    tmp_path,
) -> None:
    if not shutil.which("pi"):
        pytest.skip("pi CLI not installed")
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")

    database_path = tmp_path / "harness.db"
    guardrails_path = ROOT / "guardrails.yaml"
    if not guardrails_path.is_file():
        guardrails_path = ROOT / "src" / "foreman_ai_hq" / "defaults" / "guardrails.yaml"

    settings = Settings(database_path=database_path, guardrails_path=guardrails_path)
    app = create_app(settings)
    fake = FakePiLLMClient()
    app.state.llm_client = fake

    models_probed: list[bool] = []

    @app.get("/v1/models")
    def list_models() -> dict[str, Any]:
        models_probed.append(True)
        return {"object": "list", "data": [{"id": "harness/proxy"}]}

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=0,
            loop="asyncio",
            log_level="warning",
            access_log=False,
        )
    )
    server.capture_signals = lambda: contextlib.nullcontext()  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if getattr(server, "started", False) and server.servers and server.servers[0].sockets:
            break
        time.sleep(0.05)
    else:
        raise RuntimeError("uvicorn server failed to start")

    port = server.servers[0].sockets[0].getsockname()[1]
    try:
        with launch_pi_conversation(
            database_path,
            ["hi", "echo"],
            proxy_url=f"http://127.0.0.1:{port}/v1",
            cwd=tmp_path,
        ) as conv:
            session = conv.session
            responses = conv.responses
            proc = conv.proc
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        if thread.is_alive():
            server.force_exit = True
            thread.join(timeout=2)

    assert responses == ["ok", "ok"]

    # The bearer must never appear in command-line args.
    assert "sk_plan_" not in " ".join(map(str, proc.args))

    # The tracked profile must contain no secret material.
    profile_text = DEFAULT_PROFILE_DIR.joinpath("models.json").read_text()
    assert "sk_plan_" not in profile_text
    assert "sk_" not in profile_text

    # ACP-mode pi did not need a /v1/models stub for this fake provider config.
    assert not models_probed

    artifact = db.build_session_artifact(database_path, session["id"])
    assert len(artifact["token_log"]) == 2
    for turn in artifact["token_log"]:
        assert turn["usage_kind"] == "planning"
        assert turn["raw_usage"]["spend_category"] == "planning"
        assert turn["raw_usage"]["usage_source"] == "harness_proxy"

    # The bridge subprocess and the underlying pi process must be gone.
    assert proc.poll() is not None
    assert _pi_rpc_processes() == []


class BlockingThenNormalLLMClient:
    """Fake streaming LLM that blocks the first turn until released."""

    def __init__(self) -> None:
        self.request_count = 0
        self.requests: list[dict[str, object]] = []
        self.block_started = threading.Event()
        self.block_released = threading.Event()

    def release(self) -> None:
        self.block_released.set()

    async def acompletion(self, request: dict[str, object]):
        self.request_count += 1
        self.requests.append(request)
        model = request.get("model", "proxy")

        if self.request_count == 1:

            async def _blocked():
                yield {
                    "id": "chunk-1",
                    "object": "chat.completion.chunk",
                    "model": model,
                    "choices": [
                        {"index": 0, "delta": {"content": "partial"}, "finish_reason": None}
                    ],
                }
                self.block_started.set()
                loop = asyncio.get_running_loop()
                try:
                    await loop.run_in_executor(None, self.block_released.wait)
                finally:
                    # Release the executor thread if the request is dropped.
                    self.block_released.set()

            return _blocked()

        async def _normal():
            yield {
                "id": "chunk-1",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [
                    {"index": 0, "delta": {"content": "ok"}, "finish_reason": None}
                ],
            }
            yield {
                "id": "chunk-2",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [
                    {"index": 0, "delta": {}, "finish_reason": "stop"}
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            }

        return _normal()


def test_acp_conversation_cancels_in_flight_turn_and_continues(tmp_path) -> None:
    if not shutil.which("pi"):
        pytest.skip("pi CLI not installed")
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")

    database_path = tmp_path / "harness.db"
    guardrails_path = ROOT / "guardrails.yaml"
    if not guardrails_path.is_file():
        guardrails_path = ROOT / "src" / "foreman_ai_hq" / "defaults" / "guardrails.yaml"

    settings = Settings(database_path=database_path, guardrails_path=guardrails_path)
    app = create_app(settings)
    fake = BlockingThenNormalLLMClient()
    app.state.llm_client = fake

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=0,
            loop="asyncio",
            log_level="warning",
            access_log=False,
        )
    )
    server.capture_signals = lambda: contextlib.nullcontext()  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if getattr(server, "started", False) and server.servers and server.servers[0].sockets:
            break
        time.sleep(0.05)
    else:
        raise RuntimeError("uvicorn server failed to start")

    port = server.servers[0].sockets[0].getsockname()[1]
    try:
        with launch_pi_conversation(
            database_path,
            proxy_url=f"http://127.0.0.1:{port}/v1",
            cwd=tmp_path,
        ) as conv:
            result_holder: dict[str, Any] = {}

            def _run_prompt() -> None:
                result_holder["result"] = conv.prompt("hi")

            prompt_thread = threading.Thread(target=_run_prompt)
            prompt_thread.start()
            assert fake.block_started.wait(timeout=15), "first prompt did not reach proxy"
            # Give the transport call time to be blocked on the response queue.
            time.sleep(0.2)
            conv.cancel()
            prompt_thread.join(timeout=15)
            assert not prompt_thread.is_alive()

            text, stop_reason = result_holder["result"]
            assert stop_reason == "cancelled"
            assert text == "partial"

            # A subsequent prompt on the same handle still completes.
            text2, stop_reason2 = conv.prompt("echo")
            assert stop_reason2 == "end_turn"
            assert text2 == "ok"

            session = conv.session
            proc = conv.proc
    finally:
        fake.release()
        server.should_exit = True
        thread.join(timeout=5)
        if thread.is_alive():
            server.force_exit = True
            thread.join(timeout=2)

    # Only the completed follow-up turn is recorded as planning.
    artifact = db.build_session_artifact(database_path, session["id"])
    assert len(artifact["token_log"]) == 1
    turn = artifact["token_log"][0]
    assert turn["usage_kind"] == "planning"
    assert turn["raw_usage"]["spend_category"] == "planning"
    assert turn["raw_usage"]["usage_source"] == "harness_proxy"
    assert turn["total_tokens"] == 2

    # Cancellation did not create a Worker execution actual.
    assert artifact["worker_runs"] == []

    # The bridge subprocess and the underlying pi process must be gone.
    assert proc.poll() is not None
    assert _pi_rpc_processes() == []


def test_acp_conversation_forwards_orchestrator_persona_in_system_message(
    tmp_path,
) -> None:
    if not shutil.which("pi"):
        pytest.skip("pi CLI not installed")
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")

    database_path = tmp_path / "harness.db"
    default_guardrails_path = ROOT / "src" / "foreman_ai_hq" / "defaults" / "guardrails.yaml"
    guardrails_path = tmp_path / "guardrails.yaml"
    # Disable zone-level prompt rewriting so the test can observe pi's system
    # prompt as forwarded, not the budget-zone replacement.
    guardrails_path.write_text(
        default_guardrails_path.read_text(encoding="utf-8").replace(
            "zones:\n    enabled: true", "zones:\n    enabled: false"
        ),
        encoding="utf-8",
    )

    settings = Settings(database_path=database_path, guardrails_path=guardrails_path)
    app = create_app(settings)
    fake = FakePiLLMClient()
    app.state.llm_client = fake

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=0,
            loop="asyncio",
            log_level="warning",
            access_log=False,
        )
    )
    server.capture_signals = lambda: contextlib.nullcontext()  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if getattr(server, "started", False) and server.servers and server.servers[0].sockets:
            break
        time.sleep(0.05)
    else:
        raise RuntimeError("uvicorn server failed to start")

    port = server.servers[0].sockets[0].getsockname()[1]
    try:
        with launch_pi_conversation(
            database_path,
            ["hi"],
            proxy_url=f"http://127.0.0.1:{port}/v1",
            cwd=tmp_path,
        ) as conv:
            session = conv.session
            proc = conv.proc
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        if thread.is_alive():
            server.force_exit = True
            thread.join(timeout=2)

    assert proc.poll() is not None

    forwarded = fake.requests[0]
    system_messages = [m for m in forwarded["messages"] if m.get("role") == "system"]
    assert any(ORCHESTRATOR_PERSONA_MARKER in str(m.get("content", "")) for m in system_messages)

    artifact = db.build_session_artifact(database_path, session["id"])
    assert len(artifact["token_log"]) == 1
    turn = artifact["token_log"][0]
    assert turn["usage_kind"] == "planning"
    assert turn["raw_usage"]["spend_category"] == "planning"
    assert turn["raw_usage"]["usage_source"] == "harness_proxy"


def test_acp_conversation_applies_read_only_tool_policy(
    monkeypatch,
    tmp_path,
) -> None:
    if not shutil.which("pi"):
        pytest.skip("pi CLI not installed")
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")

    database_path = tmp_path / "harness.db"
    guardrails_path = ROOT / "guardrails.yaml"
    if not guardrails_path.is_file():
        guardrails_path = ROOT / "src" / "foreman_ai_hq" / "defaults" / "guardrails.yaml"

    settings = Settings(database_path=database_path, guardrails_path=guardrails_path)
    app = create_app(settings)
    fake = FakePiLLMClient()
    app.state.llm_client = fake

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=0,
            loop="asyncio",
            log_level="warning",
            access_log=False,
        )
    )
    server.capture_signals = lambda: contextlib.nullcontext()  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if getattr(server, "started", False) and server.servers and server.servers[0].sockets:
            break
        time.sleep(0.05)
    else:
        raise RuntimeError("uvicorn server failed to start")

    port = server.servers[0].sockets[0].getsockname()[1]

    original_write_wrapper = _pi_adapter._write_pi_acp_wrapper
    captured_wrapper: dict[str, str] = {}

    def _tracking_write_wrapper(tmpdir: Path, persona_path: Path) -> Path:
        wrapper = original_write_wrapper(tmpdir, persona_path)
        captured_wrapper["text"] = wrapper.read_text()
        return wrapper

    monkeypatch.setattr(
        _pi_adapter, "_write_pi_acp_wrapper", _tracking_write_wrapper
    )

    try:
        with launch_pi_conversation(
            database_path,
            ["List the files in this directory"],
            proxy_url=f"http://127.0.0.1:{port}/v1",
            cwd=tmp_path,
        ) as conv:
            session = conv.session
            proc = conv.proc
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        if thread.is_alive():
            server.force_exit = True
            thread.join(timeout=2)

    assert proc.poll() is not None
    assert _pi_rpc_processes() == []

    # The generated wrapper carries the read-only allowlist and omits mutating tools.
    wrapper_text = captured_wrapper["text"]
    assert '--tools "${PI_ACP_ALLOWED_TOOLS}"' in wrapper_text
    assert "bash" not in wrapper_text
    assert "edit" not in wrapper_text
    assert "write" not in wrapper_text

    artifact = db.build_session_artifact(database_path, session["id"])
    assert len(artifact["token_log"]) == 1
    turn = artifact["token_log"][0]
    assert turn["usage_kind"] == "planning"
    assert turn["raw_usage"]["spend_category"] == "planning"
    assert turn["raw_usage"]["usage_source"] == "harness_proxy"
