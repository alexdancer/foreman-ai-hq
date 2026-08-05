"""Orchestrator Model settings: inventory-constrained save, discovery, verification.

The provider/base-URL/API-key surface and its connection test are retired here.
pi owns provider authentication, so the only operator decision left is which model
from pi's own inventory the Orchestrator runs on.
"""

import pytest

from foreman_ai_hq import db
from foreman_ai_hq.operator_config import load_operator_config
from foreman_ai_hq.pi_adapter import (
    ORCHESTRATOR_STATUS_RECORD_ID,
    OrchestratorModelDiscoveryResult,
    OrchestratorVerificationResult,
)
from foreman_ai_hq.routes import portal as portal_routes
from tests.conftest import TEST_ORCHESTRATOR_MODEL, seed_orchestrator_inventory
from tests.portal.helpers import PORTAL_TOKEN, _client, _portal_headers

OTHER_MODEL = "openai-codex/gpt-5.4"


def _discovery(models, *, state="ready"):
    return OrchestratorModelDiscoveryResult(
        state=state,
        models=list(models),
        reasons=[],
        evidence={"state": state, "models": list(models), "discovered_at": "2099-01-01T00:00:00+00:00"},
    )


def _stub_discovery(monkeypatch, models, *, state="ready"):
    monkeypatch.setattr(
        portal_routes, "discover_orchestrator_models", lambda _path: _discovery(models, state=state)
    )


def _save(client, model):
    return client.post(
        "/settings/control-plane",
        headers={**_portal_headers(), "Accept": "application/json"},
        json={"control_plane_model": model},
    )


def test_save_persists_model_and_drives_every_orchestration_job(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.chdir(tmp_path)
    _stub_discovery(monkeypatch, [TEST_ORCHESTRATOR_MODEL, OTHER_MODEL])

    with _client(tmp_path) as client:
        response = _save(client, OTHER_MODEL)
        assert response.status_code == 200, response.text
        settings = client.app.state.settings

    # One model drives every job; saving removes obsolete selectors instead of
    # rewriting them as a second source of truth.
    assert settings.orchestrator_model == OTHER_MODEL
    assert settings.legacy_orchestration_model_overrides == {}
    config = load_operator_config(tmp_path / ".foreman" / "config.toml")
    assert config["orchestrator_model"] == OTHER_MODEL
    assert "estimator_model" not in config
    assert "task_breakdown_model" not in config


def test_save_revalidates_against_a_fresh_inventory(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.chdir(tmp_path)
    # The persisted snapshot still lists it; the live refresh no longer does.
    _stub_discovery(monkeypatch, [OTHER_MODEL])

    with _client(tmp_path) as client:
        seed_orchestrator_inventory(client.app.state.settings.database_path)
        response = _save(client, TEST_ORCHESTRATOR_MODEL)

    assert response.status_code == 422
    assert "no longer in pi's inventory" in response.text


def test_save_rejects_an_unqualified_model(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.chdir(tmp_path)
    _stub_discovery(monkeypatch, ["gpt-5.4"])

    with _client(tmp_path) as client:
        response = _save(client, "gpt-5.4")

    # Rejected at the schema, before any provider could be inferred for it.
    assert response.status_code == 422


def test_save_with_no_authenticated_provider_directs_to_pi_login(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.chdir(tmp_path)
    _stub_discovery(monkeypatch, [], state="needs_authentication")

    with _client(tmp_path) as client:
        response = _save(client, TEST_ORCHESTRATOR_MODEL)

    assert response.status_code == 422
    assert "pi /login" in response.text


def test_save_preserves_discovery_evidence_in_the_status_details(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.chdir(tmp_path)
    _stub_discovery(monkeypatch, [TEST_ORCHESTRATOR_MODEL, OTHER_MODEL])

    with _client(tmp_path) as client:
        database_path = client.app.state.settings.database_path
        assert _save(client, OTHER_MODEL).status_code == 200
        status = db.get_execution_backend_status(database_path, ORCHESTRATOR_STATUS_RECORD_ID)

    # A save must not erase the inventory it just validated against.
    assert status["details"]["model_discovery"]["models"] == [TEST_ORCHESTRATOR_MODEL]
    assert status["details"]["status"] == "needs_verification"
    assert status["online"] is False


def test_discover_route_persists_evidence_and_reports_authentication_state(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    _stub_discovery(monkeypatch, [], state="needs_authentication")

    with _client(tmp_path) as client:
        response = client.post("/settings/control-plane/discover", headers=_portal_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["needs_authentication"] is True
    assert body["models"] == []


def test_verify_route_passes_only_with_sentinel_and_token_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)

    def _passed(database_path, model, **kwargs):
        return OrchestratorVerificationResult(
            passed=True, model=model, session_id="sess_x", reasons=[], evidence={"model": model, "passed": True}
        )

    monkeypatch.setattr(portal_routes, "verify_orchestrator_model", _passed)
    with _client(tmp_path) as client:
        response = client.post("/settings/control-plane/verify", headers=_portal_headers())

    assert response.status_code == 200
    assert response.json()["passed"] is True


def test_verify_route_fails_when_the_sentinel_matched_but_nothing_was_metered(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    reason = "No adapter_verification token turn was recorded for the Orchestrator Model."

    def _unmetered(database_path, model, **kwargs):
        return OrchestratorVerificationResult(
            passed=False, model=model, session_id="sess_x", reasons=[reason], evidence={"model": model, "passed": False}
        )

    monkeypatch.setattr(portal_routes, "verify_orchestrator_model", _unmetered)
    with _client(tmp_path) as client:
        response = client.post("/settings/control-plane/verify", headers=_portal_headers())

    # A matched sentinel alone proves the command ran, not that spend is accounted.
    assert response.status_code == 503
    assert reason in response.json()["error"]


def test_the_retired_connection_test_route_is_gone(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.post("/settings/control-plane/test", headers=_portal_headers())
    assert response.status_code == 404


@pytest.mark.unconfigured_orchestrator
def test_readiness_is_inventory_membership_not_an_exported_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    # The old readiness rule was `bool(os.getenv(api_key_env))`; an exported key
    # must no longer make an unconfigured Orchestrator look ready.
    monkeypatch.setenv("FOREMAN_AI_HQ_CONTROL_API_KEY", "exported-but-irrelevant")

    with _client(tmp_path) as client:
        setup = client.get("/api/setup", headers=_portal_headers())

    step = next(s for s in setup.json()["steps"] if s["name"] == "Control plane model")
    assert step["state"] == "needs setup"


def test_handoff_projects_inventory_and_never_a_curated_list(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/api/settings/control-plane", headers=_portal_headers())

    body = response.json()
    assert response.status_code == 200
    assert body["inventory"]["models"] == [TEST_ORCHESTRATOR_MODEL]
    assert body["configured"] is True
    # No harness-authored list, and no credential fields survive on this surface.
    for retired in ("curated_models", "provider", "base_url", "api_key_env", "api_key_present"):
        assert retired not in body


def test_handoff_flags_per_job_models_that_diverge(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    monkeypatch.setenv("FOREMAN_AI_HQ_ORCHESTRATOR_MODEL", TEST_ORCHESTRATOR_MODEL)

    with _client(tmp_path) as client:
        # Hand-edited legacy values remain visible as migration evidence only.
        object.__setattr__(
            client.app.state.settings,
            "legacy_orchestration_model_overrides",
            {"estimator_model": OTHER_MODEL},
        )
        response = client.get("/api/settings/control-plane", headers=_portal_headers())

    assert response.json()["diverging_jobs"] == {"estimator_model": OTHER_MODEL}
