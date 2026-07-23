"""ACP conversational pi launch: prove multi-turn governance through the Harness Proxy.

This test requires the `pi` CLI and Node.js to be installed. It starts a real
uvicorn server with a fake streaming LLM client and drives pi over ACP through
`foreman_ai_hq.pi_adapter.launch_pi_conversation`.
"""

from __future__ import annotations

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
from foreman_ai_hq.pi_adapter import DEFAULT_PROFILE_DIR, launch_pi_conversation
from foreman_ai_hq.settings import Settings

ROOT = Path(__file__).resolve().parents[2]


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
            session = conv["session"]
            responses = conv["responses"]
            proc = conv["proc"]
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
