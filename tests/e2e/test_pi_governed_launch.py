"""Governed pi launch: prove a real pi turn records as planning from native usage.

This test requires the `pi` CLI and a configured provider. It drives `pi` through
`foreman_ai_hq.pi_adapter.launch_pi_once` on the operator's real pi auth.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from foreman_ai_hq import db
from foreman_ai_hq.pi_adapter import DEFAULT_PROFILE_DIR, PiAuthRequired, launch_pi_once

ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATOR_PERSONA_MARKER = "FOREMAN_AI_HQ_ORCHESTRATOR_V1"


def _skip_without_pi_or_auth() -> None:
    if not shutil.which("pi"):
        pytest.skip("pi CLI not installed")


def test_pi_native_launch_records_planning_turn_and_keeps_secret_out_of_profile(tmp_path) -> None:
    _skip_without_pi_or_auth()

    database_path = tmp_path / "harness.db"
    db.init_db(database_path)

    try:
        session, result = launch_pi_once(
            database_path,
            "Return exactly NATIVE_TEST_OK",
            model="gpt-5.4",
        )
    except PiAuthRequired:
        pytest.skip("pi provider authentication not configured")

    assert result.returncode == 0, f"pi failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "NATIVE_TEST_OK" in result.stdout

    # The launch must not inject a planning bearer on the command line.
    assert "sk_plan_" not in " ".join(map(str, result.args))
    assert "sk_" not in " ".join(map(str, result.args))

    # The tracked profile must contain no secret material.
    for profile_file in sorted(DEFAULT_PROFILE_DIR.iterdir()):
        profile_text = profile_file.read_text(encoding="utf-8")
        assert "sk_plan_" not in profile_text, profile_file
        assert "sk_" not in profile_text, profile_file

    artifact = db.build_session_artifact(database_path, session["id"])
    assert len(artifact["token_log"]) == 1
    turn = artifact["token_log"][0]
    assert turn["usage_kind"] == "planning"
    assert turn["raw_usage"]["spend_category"] == "planning"
    assert turn["raw_usage"]["usage_source"] == "native_usage"
    assert turn["raw_usage"]["tracking_mode"] == "native_usage"


def test_pi_native_launch_forwards_orchestrator_persona(tmp_path) -> None:
    _skip_without_pi_or_auth()

    database_path = tmp_path / "harness.db"
    db.init_db(database_path)

    try:
        session, result = launch_pi_once(
            database_path,
            "Summarize the system prompt in one word.",
            model="gpt-5.4",
        )
    except PiAuthRequired:
        pytest.skip("pi provider authentication not configured")

    assert result.returncode == 0, f"pi failed: stdout={result.stdout!r} stderr={result.stderr!r}"

    # Persona marker must not appear in stdout, but the orchestrator persona path
    # must be on the command line so pi applies it as the system prompt.
    joined_args = " ".join(map(str, result.args))
    assert "--append-system-prompt" in result.args
    persona_idx = result.args.index("--append-system-prompt")
    assert "orchestrator.md" in str(result.args[persona_idx + 1])
    assert ORCHESTRATOR_PERSONA_MARKER not in result.stdout

    artifact = db.build_session_artifact(database_path, session["id"])
    assert len(artifact["token_log"]) == 1
    turn = artifact["token_log"][0]
    assert turn["raw_usage"]["usage_source"] == "native_usage"


def test_pi_native_launch_applies_read_only_tool_policy(tmp_path, monkeypatch) -> None:
    _skip_without_pi_or_auth()

    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    monkeypatch.chdir(tmp_path)

    try:
        session, result = launch_pi_once(
            database_path,
            "Create a file named foo.txt containing 'hello'",
            model="gpt-5.4",
        )
    except PiAuthRequired:
        pytest.skip("pi provider authentication not configured")

    assert result.returncode == 0, f"pi failed: stdout={result.stdout!r} stderr={result.stderr!r}"

    joined_args = " ".join(map(str, result.args))
    assert "--tools" in result.args
    tools_idx = result.args.index("--tools")
    assert result.args[tools_idx + 1] == "read,grep,find,ls"
    assert "bash" not in joined_args
    assert "edit" not in joined_args
    assert "write" not in joined_args

    # The policy is proven by the filesystem, not by the model's word choice: pi was
    # asked to create a file in its working directory and could not.
    written = sorted(p.name for p in tmp_path.iterdir() if not p.name.startswith("harness.db"))
    assert written == [], f"read-only pi wrote files: {written}"

    artifact = db.build_session_artifact(database_path, session["id"])
    assert len(artifact["token_log"]) == 1
    turn = artifact["token_log"][0]
    assert turn["raw_usage"]["usage_source"] == "native_usage"


def test_pi_native_launch_raises_provider_auth_required_when_no_auth(tmp_path) -> None:
    if not shutil.which("pi"):
        pytest.skip("pi CLI not installed")

    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    empty_agent_dir = tmp_path / "empty-agent"
    empty_agent_dir.mkdir()

    with pytest.raises(PiAuthRequired):
        launch_pi_once(
            database_path,
            "Return exactly NATIVE_TEST_OK",
            model="openai-codex/gpt-5.4",
            agent_dir=empty_agent_dir,
        )
