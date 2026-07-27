"""Refuse orchestration work when the Orchestrator Model is not configured.

Configuration is decided from persisted state alone — a stored provider-qualified
model that appears in pi's last discovered inventory. Nothing here shells out to pi,
which is what lets a Recorded Demo Run seed the same evidence as ordinary scenario
state and still travel the production code path with no environment bypass.

The gate deliberately covers only work that spends or launches. Sign-in, every
settings surface, and read-only evidence stay reachable, so an expired provider
token cannot lock an operator out of their own audit trail or out of the page they
need in order to fix the configuration.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from foreman_ai_hq.pi_adapter import resolve_orchestrator_model

ORCHESTRATOR_NOT_CONFIGURED_DETAIL = (
    "Orchestrator Model is not configured. Choose a model from pi's inventory in "
    "Settings → Orchestrator Model."
)


def orchestrator_is_configured(request: Request) -> bool:
    settings = request.app.state.settings
    return resolve_orchestrator_model(settings.database_path, settings.orchestrator_model) is not None


def require_configured_orchestrator(request: Request) -> None:
    """FastAPI dependency: 503 unless a discovered model is configured.

    503 rather than 403 because this is an unconfigured service the operator can
    fix, not a permission the caller lacks.
    """
    if not orchestrator_is_configured(request):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ORCHESTRATOR_NOT_CONFIGURED_DETAIL,
        )
