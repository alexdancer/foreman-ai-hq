from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from foreman_ai_hq import db
from foreman_ai_hq.guardrails import GuardrailConfig


@dataclass(frozen=True)
class CheckpointResult:
    name: str
    passed: bool
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "details": self.details}


def evaluate_checkpoints(artifact: dict[str, Any], config: GuardrailConfig) -> list[CheckpointResult]:
    # Reports display these in order as the operator checklist.
    return [
        _budget_health(artifact, config),
        _stuck_loop_score(artifact),
        _tool_diversity(artifact, config),
        _timeout_respect(artifact),
    ]


def evaluate_and_record_checkpoints(
    database_path: Path | str,
    session_id: str,
    config: GuardrailConfig,
    artifact: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate checkpoints against a Session Artifact and persist the results, replacing any prior run.

    Callers may supply an already-built artifact so the route and the Worker Run
    completion path share the same evaluation without re-querying the database.
    """
    if artifact is None:
        artifact = db.build_session_artifact(database_path, session_id)
    results = [result.as_dict() for result in evaluate_checkpoints(artifact, config)]
    db.replace_checkpoint_results(database_path, session_id=session_id, checkpoints=results)
    return results


def _budget_health(artifact: dict[str, Any], config: GuardrailConfig) -> CheckpointResult:
    session_tokens = sum(int(turn.get("total_tokens", 0)) for turn in artifact.get("token_log", []))
    if config.session_cap.enabled:
        # A hard session cap overrides fair-share math when operators configure an explicit limit.
        budget_limit = config.session_cap.tokens
        limit_source = "session_cap"
    else:
        budget = artifact.get("budget", {})
        budget_limit = int(budget.get("remaining_daily_tokens", 0) * budget.get("fair_share_factor", 1.0))
        limit_source = "fair_share"
    passed = session_tokens <= budget_limit
    return CheckpointResult(
        name="budget_health",
        passed=passed,
        details={
            "session_tokens": session_tokens,
            "session_cap_tokens": config.session_cap.tokens,
            "budget_limit_tokens": budget_limit,
            "budget_limit_source": limit_source,
        },
    )


def _stuck_loop_score(artifact: dict[str, Any]) -> CheckpointResult:
    count = sum(1 for alarm in artifact.get("alarms", []) if alarm.get("type") == "LOOP_DETECTED")
    return CheckpointResult(
        name="stuck_loop_score",
        passed=count < 3,
        details={"loop_alarm_count": count, "limit": 3},
    )


def _tool_diversity(artifact: dict[str, Any], config: GuardrailConfig) -> CheckpointResult:
    categories = {
        _tool_category(call.get("tool_name"), config)
        for call in artifact.get("tool_trace", [])
        if call.get("tool_name")
    }
    clean_categories = {category for category in categories if category is not None}
    distinct_categories = len(clean_categories)
    red_zone_restricted = any(
        snapshot.get("zone") == "red" and snapshot.get("decision", {}).get("blocked_tools")
        for snapshot in artifact.get("guardrail_snapshots", [])
    )
    # Red-zone restrictions may lower tool variety because governance already narrowed choices.
    passed = distinct_categories >= 3 or red_zone_restricted
    return CheckpointResult(
        name="tool_diversity",
        passed=passed,
        details={
            "distinct_categories": distinct_categories,
            "categories": sorted(clean_categories),
            "red_zone_restricted": red_zone_restricted,
        },
    )


def _timeout_respect(artifact: dict[str, Any]) -> CheckpointResult:
    count = sum(1 for alarm in artifact.get("alarms", []) if alarm.get("type") == "SESSION_TIMEOUT")
    return CheckpointResult(
        name="timeout_respect",
        passed=count == 0,
        details={"timeout_alarm_count": count},
    )


def _tool_category(tool_name: str | None, config: GuardrailConfig) -> str | None:
    if tool_name is None:
        return None
    for category, tools in {
        "file_io": {"read_file", "write_file", "patch", "search_files"},
        "shell": {"terminal", "process"},
        "web": {"web_search", "web_extract", "browser_navigate", "browser_snapshot", "browser_click"},
        "vision": {"vision_analyze", "browser_vision"},
        "code_exec": {"execute_code"},
        "delegation": {"delegate_task"},
    }.items():
        if tool_name in tools and category in config.tool_categories:
            return category
    return "other"
