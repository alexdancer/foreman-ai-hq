from __future__ import annotations

import json
import re
from typing import Any

MAX_SUMMARY_CHARS = 180
MAX_NEXT_ACTION_CHARS = 220
MAX_DETAIL_CHARS = 500
SETUP_HREF = "/settings/workers"
_SECRET_PATTERNS = (
    re.compile(r"(?<!\w)sk[-_][A-Za-z0-9_.-]+"),
    re.compile(r"Bearer\s+[A-Za-z0-9_.-]+", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*[^\s,;]+"),
)
# Split so the harness' own session-key prefix is not a literal in this source.
_SESSION_KEY_PATTERN = re.compile("s" "k_" r"[A-Za-z0-9_\-.]+")


def native_cli_diagnostic(
    *,
    adapter_id: str | None,
    adapter_kind: str | None,
    stdout: str = "",
    stderr: str = "",
    returncode: int | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return bounded operator-facing diagnostics for known native CLI setup failures."""
    # Diagnostics are operator-facing, so merge all CLI channels and redact before pattern matching.
    text = redact_native_cli_text(_combined_cli_text(stdout=stdout, stderr=stderr, evidence=evidence))
    lower = text.lower()
    kind = str(adapter_kind or adapter_id or "worker").lower()
    label = _adapter_label(adapter_id=adapter_id, adapter_kind=adapter_kind)

    if "not logged in" in lower and ("/login" in lower or "claude" in kind):
        return _diagnostic(
            adapter_id=adapter_id,
            adapter_kind=adapter_kind,
            code="claude_code_not_logged_in",
            summary="Not logged in · Please run /login",
            next_action="Run `/login` in Claude Code, then verify the adapter again.",
            detail=text,
            setup_href=SETUP_HREF,
        )

    if "codex" in kind and (
        "not inside a trusted directory" in lower or ("trusted" in lower and "--skip-git-repo-check" in lower)
    ):
        return _diagnostic(
            adapter_id=adapter_id,
            adapter_kind=adapter_kind,
            code="codex_untrusted_directory",
            summary="Not inside a trusted directory and --skip-git-repo-check was not specified.",
            next_action="Trust the connected project or configure Codex native launch with --skip-git-repo-check, then retry.",
            detail=text,
            setup_href=SETUP_HREF,
        )

    if text:
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), text.strip())
        return _diagnostic(
            adapter_id=adapter_id,
            adapter_kind=adapter_kind,
            code="native_cli_failure",
            summary=f"{label} CLI failed: {_bounded(first_line, 120)}",
            next_action=f"Check {label} CLI setup, then verify the adapter or retry launch.",
            detail=text,
            setup_href=SETUP_HREF,
        )

    if returncode not in (None, 0):
        return _diagnostic(
            adapter_id=adapter_id,
            adapter_kind=adapter_kind,
            code="native_cli_failure",
            summary=f"{label} CLI failed with return code {returncode}.",
            next_action=f"Check {label} CLI setup, then verify the adapter or retry launch.",
            detail="",
            setup_href=SETUP_HREF,
        )

    return None


def _diagnostic(
    *,
    adapter_id: str | None,
    adapter_kind: str | None,
    code: str,
    summary: str,
    next_action: str,
    detail: str,
    setup_href: str | None,
) -> dict[str, Any]:
    diagnostic: dict[str, Any] = {
        "code": code,
        "summary": _bounded(summary, MAX_SUMMARY_CHARS),
        "next_action": _bounded(next_action, MAX_NEXT_ACTION_CHARS),
        "adapter_id": adapter_id,
        "adapter_kind": adapter_kind,
    }
    if setup_href:
        diagnostic["setup_href"] = setup_href
    if detail:
        diagnostic["detail"] = _bounded(detail, MAX_DETAIL_CHARS)
    return diagnostic


def _combined_cli_text(*, stdout: str, stderr: str, evidence: dict[str, Any] | None) -> str:
    parts = []
    parts.extend(_json_payload_texts(stdout))
    parts.extend(_json_payload_texts(stderr))
    if stdout.strip():
        parts.append(stdout.strip())
    if stderr.strip():
        parts.append(stderr.strip())
    if evidence:
        parts.extend(_evidence_texts(evidence))
    return "\n".join(_dedupe(part for part in parts if part))


def _json_payload_texts(text: str) -> list[str]:
    texts: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        # Many native CLIs stream JSONL; pull human-readable text out of nested payloads.
        extracted = _payload_text(payload)
        if extracted:
            texts.append(extracted)
    return texts


def _payload_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        nested = [_payload_text(item) for item in value]
        return " ".join(item for item in nested if item) or None
    if isinstance(value, dict):
        error = value.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        content = value.get("content")
        if isinstance(content, list):
            nested = [_payload_text(item) for item in content]
            text = " ".join(item for item in nested if item)
            if text:
                return text
        for key in ("message", "result", "text", "detail", "stderr", "stdout"):
            if key in value:
                text = _payload_text(value[key])
                if text:
                    return text
    return None


def _evidence_texts(evidence: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for key in ("message", "result", "error", "detail", "stderr", "stdout"):
        value = evidence.get(key)
        text = _payload_text(value)
        if text:
            texts.append(text)
    return texts


def _dedupe(values: Any) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _adapter_label(*, adapter_id: str | None, adapter_kind: str | None) -> str:
    value = str(adapter_kind or adapter_id or "Worker")
    labels = {"claude_code": "Claude Code", "codex": "Codex", "opencode": "OpenCode"}
    return labels.get(value, value.replace("_", " ").title())


def redact_native_cli_text(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("***REDACTED***", redacted)
    return redacted


def redact_cli_value(value: str) -> str:
    """Redact one CLI-derived value before it is persisted as evidence.

    Shared by Worker adapter evidence and pi orchestrator discovery evidence so
    both persist through one redaction path.
    """
    redacted = redact_native_cli_text(_SESSION_KEY_PATTERN.sub("***REDACTED***", value))
    # A value that merely mentions a secret without matching a pattern is still
    # not safe to persist verbatim.
    if "secret" in value.lower() and redacted == value:
        return "***REDACTED***"
    return redacted


def _bounded(text: str, limit: int) -> str:
    normalized = " ".join(str(text).split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(limit - 1, 0)].rstrip()}…"
