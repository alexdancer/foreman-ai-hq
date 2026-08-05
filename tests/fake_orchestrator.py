from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from foreman_ai_hq import db
from foreman_ai_hq.llm import extract_usage, resolve_cost, response_to_dict
from foreman_ai_hq.pi_adapter import (
    PiStructuredJobError,
    PiStructuredJobResult,
    PiStructuredOutputError,
)
from foreman_ai_hq.task_breakdown import TASK_BREAKDOWN_MAX_TOKENS


class FakeOrchestratorJobRunner:
    """Adapt legacy fake model responses to submitted pi job arguments."""

    def __init__(self, llm: Any):
        self.llm = llm

    async def __call__(
        self,
        database_path: Path | str | None,
        *,
        instructions: str,
        input_payload: dict[str, Any],
        model: str,
        submit_tool: str,
        usage_kind: str,
        task_description: str,
        timeout: float,
        session_id: str | None = None,
        result_validator: Any = None,
        **_kwargs: Any,
    ) -> PiStructuredJobResult:
        session = None
        if database_path is not None:
            if session_id:
                session = db.get_session(database_path, session_id)
            else:
                session, _ = db.create_planning_session(
                    database_path,
                    task_description=task_description,
                    model=model,
                    tracking_mode="native_usage",
                )

        request = {
            "model": model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": json.dumps(input_payload, sort_keys=True)},
            ],
            "temperature": 0,
        }
        if usage_kind == "task_breakdown":
            request.update(max_tokens=TASK_BREAKDOWN_MAX_TOKENS, timeout_seconds=timeout)

        try:
            response = await self.llm.acompletion(request)
        except Exception as exc:
            if session is not None:
                db.update_session_status(database_path, session["id"], "failed")
            raise PiStructuredJobError(
                str(exc), session_id=session["id"] if session is not None else None
            ) from exc

        if session is not None:
            usage = extract_usage(response)
            raw_usage: dict[str, Any] = {**usage, "usage_source": "native_usage", "tracking_mode": "native_usage"}
            if usage_kind == "reporting":
                raw_usage.update(
                    {
                        "spend_category": "reporting_summary",
                        "usage_source": "control_plane",
                        "reporting_kind": "agent_review",
                        "response": response_to_dict(response),
                    }
                )
            elif usage_kind == "estimation":
                raw_usage["spend_category"] = "control_plane"
            elif usage_kind == "task_breakdown":
                raw_usage["spend_category"] = "task_breakdown"
            db.record_token_turn(
                database_path,
                session_id=session["id"],
                usage_kind=usage_kind,
                model=model,
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                cost=resolve_cost(model, response),
                raw_usage=raw_usage,
            )

        body = response_to_dict(response)
        try:
            content = body["choices"][0]["message"]["content"]
            arguments = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            if session is not None:
                db.update_session_status(database_path, session["id"], "failed")
            raise PiStructuredOutputError(
                f"fake pi job did not call {submit_tool} with object arguments",
                session_id=session["id"] if session is not None else None,
            ) from exc
        if not isinstance(arguments, dict):
            if session is not None:
                db.update_session_status(database_path, session["id"], "failed")
            raise PiStructuredOutputError(
                f"fake pi job did not call {submit_tool} with object arguments",
                session_id=session["id"] if session is not None else None,
            )

        try:
            validated = result_validator(arguments) if result_validator else arguments
        except Exception as exc:
            if session is not None:
                db.update_session_status(database_path, session["id"], "failed")
            raise PiStructuredOutputError(
                str(exc), session_id=session["id"] if session is not None else None
            ) from exc

        if session is None:
            session = {
                "id": "fake-orchestrator-session",
                "status": "completed",
                "guardrail_overrides": {
                    "session_kind": "planning",
                    "tracking_mode": "native_usage",
                },
            }
        else:
            session = db.update_session_status(database_path, session["id"], "completed")
        return PiStructuredJobResult(
            arguments=arguments, validated=validated, session=session, args=[submit_tool]
        )
