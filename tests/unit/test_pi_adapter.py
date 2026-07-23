"""Unit tests for the pi orchestrator launch wiring."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import mock

from foreman_ai_hq import db
import foreman_ai_hq.pi_adapter as _pi_adapter
from foreman_ai_hq.pi_adapter import (
    DEFAULT_PROFILE_DIR,
    PI_ORCHESTRATOR_ALLOWED_TOOLS,
    _write_pi_acp_wrapper,
    launch_pi_once,
)


def test_orchestrator_allowed_tools_allows_read_only_set() -> None:
    assert PI_ORCHESTRATOR_ALLOWED_TOOLS == ("read", "grep", "find", "ls")
    assert "bash" not in PI_ORCHESTRATOR_ALLOWED_TOOLS
    assert "edit" not in PI_ORCHESTRATOR_ALLOWED_TOOLS
    assert "write" not in PI_ORCHESTRATOR_ALLOWED_TOOLS


def test_acp_wrapper_includes_tool_allowlist() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        persona = Path(tmpdir) / "orchestrator.md"
        persona.write_text("test", encoding="utf-8")
        wrapper = _write_pi_acp_wrapper(Path(tmpdir), persona)
        text = wrapper.read_text()

        assert (
            'exec pi --append-system-prompt "${PI_ACP_PERSONA_PATH}" --tools "${PI_ACP_ALLOWED_TOOLS}" "$@"'
            in text
        )
        assert "bash" not in text
        assert "edit" not in text
        assert "write" not in text
        assert wrapper.stat().st_mode & 0o111


def test_launch_pi_once_appends_tool_allowlist(
    monkeypatch,
    tmp_path,
) -> None:
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
