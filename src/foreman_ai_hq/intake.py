from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from fastapi import Request, UploadFile

from foreman_ai_hq import db
from foreman_ai_hq.pi_adapter import PiStructuredOutputError, run_pi_structured_job
from foreman_ai_hq.project_context import project_task_metadata
from foreman_ai_hq.routes.tasks import (
    _create_task_breakdown_review,
    _estimate_and_create_task,
    _with_single_project_default,
)


_MARKDOWN_PATTERNS = (
    r"(?m)^\s{0,3}#{1,6}\s+",
    r"(?m)^\s{0,3}(?:[-+*]\s+|\d+[.)]\s+|>\s*)",
    r"(?m)^\s{0,3}(?:```|~~~)",
    r"(?m)^\s{0,3}(?:[-*_]\s*){3,}$",
    r"!?\[[^\]]+\]\([^\)]+\)",
    r"(?:\*\*|__)[^\n]+?(?:\*\*|__)",
    r"(?<!\*)\*[^*\n]+\*(?!\*)|(?<![\w_])_[^\n]+?_(?![\w_])",
    r"`+[^`\n]+`+",
    r"~~[^\n]+?~~",
    r"<(?:https?://|mailto:)[^>\n]+>",
    r"(?m)^\s*\|?.+\|.+\n\s*\|?\s*:?-{3,}",
)


def _looks_like_markdown(text: str) -> bool:
    return any(re.search(pattern, text) for pattern in _MARKDOWN_PATTERNS)


def _validate_intake_result(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PiStructuredOutputError("submit_intake must return an object")
    decision = payload.get("decision")
    if decision not in {"single_task", "needs_breakdown"}:
        raise PiStructuredOutputError(
            f"submit_intake.decision must be single_task or needs_breakdown, got {decision!r}"
        )
    reason = payload.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise PiStructuredOutputError("submit_intake.reason must be a non-empty string")
    return {"decision": decision, "reason": reason.strip()}


def _is_markdown_upload(file: UploadFile | None) -> bool:
    if not file or not file.filename:
        return False
    return Path(file.filename).suffix.lower() == ".md"


async def normalize_chat_intake(
    text: str | None,
    file: UploadFile | None,
) -> tuple[str, dict[str, Any]]:
    """Return normalized source text and intake metadata from the chat composer.

    Markdown file attachment takes precedence over typed text. Invalid or empty
    attachments raise ValueError before any model turn is started.
    """
    if file and file.filename:
        filename = Path(file.filename).name
        suffix = Path(filename).suffix.lower()
        if suffix != ".md":
            raise ValueError("Only Markdown .md files can be attached.")
        raw = await file.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Markdown upload must be UTF-8 text.") from exc
        normalized = text.strip()
        if not normalized:
            raise ValueError("Markdown upload is empty.")
        return normalized, {"intake_source": "markdown_upload", "intake_filename": filename}

    if text:
        normalized = text.strip()
        if not normalized:
            raise ValueError("Type a message or attach a Markdown .md file.")
        metadata: dict[str, Any] = {"intake_source": "markdown_paste"} if _looks_like_markdown(normalized) else {"intake_source": "plain_text"}
        return normalized, metadata

    raise ValueError("Type a message or attach a Markdown .md file.")


async def run_intake_decision(
    request: Request,
    source_text: str,
    intake_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Run the orchestrator intake decision job and return {decision, reason}."""
    # Markdown paste and upload always require review; skip the model call.
    if intake_metadata.get("intake_source") in {"markdown_paste", "markdown_upload"}:
        return {
            "decision": "needs_breakdown",
            "reason": "Markdown intake always routes to Task Breakdown Review.",
        }

    settings = request.app.state.settings
    runner = getattr(request.app.state, "orchestrator_job_runner", run_pi_structured_job)
    result = await runner(
        settings.database_path,
        instructions=_intake_decision_prompt(),
        input_payload={"source_text": source_text, "intake_metadata": intake_metadata},
        model=settings.orchestrator_model,
        persona_filename="intake.md",
        extension_filename="submit-intake.ts",
        submit_tool="submit_intake",
        usage_kind="planning",
        task_description=f"intake decision: {source_text[:200]}",
        result_validator=_validate_intake_result,
    )
    return result.validated


def _intake_decision_prompt() -> str:
    return "\n\n".join(
        [
            "You are the Foreman AI HQ intake judge.",
            (
                "Read the curated input once. Decide whether the source describes a single small "
                "Task that can be honestly estimated as one vertical slice, or whether it is "
                "multi-slice, ambiguous, large, or markdown-shaped work that should be reviewed and "
                "broken down first. Call submit_intake exactly once with 'decision' and 'reason'."
            ),
            "Single small Task criteria: one coherent behavior, one codebase seam, independently executable and verifiable, no hidden dependencies, and small enough that an honest estimate does not require pre-investigation.",
            "If the intake source is markdown_paste or markdown_upload, you must choose needs_breakdown.",
        ]
    )


async def process_chat_intake(
    request: Request,
    project_id: str,
    source_text: str,
    intake_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Route chat intake to a Task or Task Breakdown Review and record the decision.

    A source judged needs_breakdown must never produce a single Task.
    """
    database_path = request.app.state.settings.database_path
    project = db.get_connected_project(database_path, project_id)
    project_metadata = project_task_metadata(project)
    intake_metadata = _with_single_project_default(
        database_path,
        {
            **intake_metadata,
            **project_metadata,
        },
    )

    decision = await run_intake_decision(request, source_text, intake_metadata)
    intake_metadata["intake_decision"] = decision["decision"]
    intake_metadata["intake_decision_reason"] = decision["reason"]

    if decision["decision"] == "needs_breakdown":
        breakdown = await _create_task_breakdown_review(request, source_text, intake_metadata)
        return {
            "ok": True,
            "decision": "needs_breakdown",
            "reason": decision["reason"],
            "next_href": f"/task-breakdowns/{breakdown['id']}/review",
            "breakdown_id": breakdown["id"],
        }

    task = await _estimate_and_create_task(
        request,
        source_text,
        extra_metadata=intake_metadata,
    )
    return {
        "ok": True,
        "decision": "single_task",
        "reason": decision["reason"],
        "task_id": task["id"],
    }
