from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from foreman_ai_hq import db
from foreman_ai_hq.adapter_readiness import evaluate_adapter_readiness


@dataclass(frozen=True)
class LaunchGuardrailResult:
    passed: bool
    launchable: bool
    reasons: list[str]
    adapter: dict[str, Any] | None = None


def evaluate_launch_guardrails(
    database_path: Path | str,
    *,
    adapter_id: str,
    model: str,
    project_root: str | None = None,
    session_api_key: str | None,
    proxy_url: str | None,
    read_only: bool = False,
) -> LaunchGuardrailResult:
    try:
        adapter = db.get_worker_adapter(database_path, adapter_id)
    except KeyError:
        return LaunchGuardrailResult(False, False, ["Worker adapter not found."], None)

    readiness = evaluate_adapter_readiness(
        adapter,
        model=model,
        project_root=project_root,
        session_api_key=session_api_key,
        proxy_url=proxy_url,
        include_launch_credentials=True,
    )

    reasons = list(readiness.reasons)

    # Launch uses the stricter board-readiness path because it includes the credentials needed to start a Worker.
    return LaunchGuardrailResult(readiness.launchable_for_board, readiness.launchable_for_board, reasons, adapter)
