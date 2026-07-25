"""ACP conversational pi launch: prove multi-turn governance on native usage.

This test requires the `pi` CLI, Node.js, and a configured provider. It drives
pi over ACP through `foreman_ai_hq.pi_adapter.launch_pi_conversation`.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from foreman_ai_hq import db
from foreman_ai_hq.pi_adapter import (
    PiAuthRequired,
    launch_pi_conversation,
)


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


def _skip_without_pi_or_auth() -> None:
    if not shutil.which("pi"):
        pytest.skip("pi CLI not installed")
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")


def test_acp_conversation_records_two_planning_turns_and_cleans_up(tmp_path) -> None:
    _skip_without_pi_or_auth()

    database_path = tmp_path / "harness.db"
    db.init_db(database_path)

    try:
        with launch_pi_conversation(
            database_path,
            prompts=["Return exactly T1", "Return exactly T2"],
            cwd=tmp_path,
            model="gpt-5.4",
        ) as conv:
            session = conv.session
            responses = conv.responses
            proc = conv.proc
    except PiAuthRequired:
        pytest.skip("pi provider authentication not configured")

    assert len(responses) == 2
    assert "T1" in responses[0]
    assert "T2" in responses[1]

    artifact = db.build_session_artifact(database_path, session["id"])
    assert len(artifact["token_log"]) == 2
    for turn in artifact["token_log"]:
        assert turn["usage_kind"] == "planning"
        assert turn["raw_usage"]["spend_category"] == "planning"
        assert turn["raw_usage"]["usage_source"] == "native_usage"
        assert turn["raw_usage"]["tracking_mode"] == "native_usage"

    assert proc.poll() is not None
    assert _pi_rpc_processes() == []


def test_acp_conversation_forwards_orchestrator_persona_and_tools(tmp_path) -> None:
    _skip_without_pi_or_auth()

    database_path = tmp_path / "harness.db"
    db.init_db(database_path)

    try:
        with launch_pi_conversation(
            database_path,
            prompts=["Return exactly ACP_OK"],
            cwd=tmp_path,
            model="gpt-5.4",
        ) as conv:
            session = conv.session
            proc = conv.proc
            responses = conv.responses

            assert "ACP_OK" in responses[0]

            wrapper = conv._workdir / "pi-wrapper.sh"
            wrapper_text = wrapper.read_text()
            assert "--append-system-prompt" in wrapper_text
            assert '--tools "$PI_ACP_ALLOWED_TOOLS"' in wrapper_text
            assert "bash" not in wrapper_text
            assert "edit" not in wrapper_text
            assert "write" not in wrapper_text
    except PiAuthRequired:
        pytest.skip("pi provider authentication not configured")

    artifact = db.build_session_artifact(database_path, session["id"])
    assert len(artifact["token_log"]) == 1
    turn = artifact["token_log"][0]
    assert turn["usage_kind"] == "planning"
    assert turn["raw_usage"]["usage_source"] == "native_usage"

    assert proc.poll() is not None
    assert _pi_rpc_processes() == []


def test_acp_conversation_raises_provider_auth_required_when_no_auth(tmp_path) -> None:
    if not shutil.which("pi"):
        pytest.skip("pi CLI not installed")
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")

    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    empty_agent_dir = tmp_path / "empty-agent"
    empty_agent_dir.mkdir()

    with pytest.raises(PiAuthRequired):
        with launch_pi_conversation(
            database_path,
            cwd=tmp_path,
            model="openai-codex/gpt-5.4",
            agent_dir=empty_agent_dir,
        ):
            pass
