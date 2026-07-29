from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = ROOT / "demo"
IGNORED_PARTS = {".venv", ".pytest_cache", "__pycache__"}

BANNED_SECRET_PATTERNS = [
    re.compile(r"sk-(?:live|proj|test)-[A-Za-z0-9_-]{12,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{6,}['\"]"),
]


class TokenTrackerHarnessDemoFakeDataInvariantTests:
    __test__ = True

    def test_no_env_files_under_demo(self) -> None:
        offenders = [path for path in DEMO_DIR.rglob("*") if path.name.startswith(".env")]
        assert offenders == []

    @pytest.mark.parametrize("pattern", BANNED_SECRET_PATTERNS)
    def test_demo_files_do_not_contain_real_looking_secrets(self, pattern: re.Pattern[str]) -> None:
        offenders: list[str] = []
        for path in _demo_source_files():
            if path.suffix not in {".py", ".toml", ".md"}:
                continue
            text = path.read_text()
            if pattern.search(text):
                offenders.append(path.relative_to(ROOT).as_posix())
        assert offenders == []

    def test_demo_source_does_not_use_real_home_snip_path(self) -> None:
        offenders: list[str] = []
        for path in _demo_source_files():
            if path.suffix != ".py":
                continue
            text = path.read_text()
            if "~/.snip" in text or "Path.home()" in text:
                offenders.append(path.relative_to(ROOT).as_posix())
        assert offenders == []


def _context_md_text_without_adr_reference() -> str:
    context_md = ROOT / "CONTEXT.md"
    text = context_md.read_text()
    return "\n".join(
        line for line in text.splitlines()
        if "docs/adr/0005-scout-tasks-replace-spike.md" not in line
    )


def test_context_md_does_not_use_active_spike_terminology() -> None:
    text = _context_md_text_without_adr_reference()
    assert "Spike" not in text and "spike" not in text


def test_synthetic_read_only_demo_fixtures_are_labeled() -> None:
    demo_module = ROOT / "tests" / "e2e" / "recorded_demo.py"
    text = demo_module.read_text()
    # Read-only launch now comes from the canonical kind, not a metadata flag.
    assert '"acceptance_verification"' in text
    assert '"synthetic_fixture": True' in text


def _demo_source_files() -> list[Path]:
    return [
        path
        for path in DEMO_DIR.rglob("*")
        if path.is_file()
        and not any(part in IGNORED_PARTS or part.endswith(".egg-info") for part in path.parts)
    ]
