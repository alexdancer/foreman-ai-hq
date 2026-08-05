"""Unit tests for Orchestrator Model inventory discovery and validation.

pi's ``--list-models`` inventory is the sole authority for the Orchestrator Model,
so these tests pin the two properties that authority rests on: the parser accepts
only model rows, and a configured value is usable only when the persisted
inventory still contains it.
"""

from __future__ import annotations

import subprocess

import pytest

from foreman_ai_hq import db
from foreman_ai_hq.pi_adapter import (
    DISCOVERY_FAILED,
    DISCOVERY_NEEDS_AUTHENTICATION,
    DISCOVERY_READY,
    ORCHESTRATOR_STATUS_RECORD_ID,
    discover_orchestrator_models,
    discovered_orchestrator_models,
    is_provider_qualified_model,
    persisted_orchestrator_discovery,
    resolve_orchestrator_model,
    PiOnceResult,
    SENTINEL_RESPONSE,
    orchestrator_verification_is_stale,
    persisted_orchestrator_verification,
    verify_orchestrator_model,
)

# Captured shape of `pi --list-models` on pi 0.82: a fixed-width table with a
# header row, filtered to providers the operator is authenticated with.
PI_MODEL_TABLE = (
    "provider      model                       context  max-out  thinking  images\n"
    "anthropic     claude-opus-5               1M       128K     yes       yes\n"
    "openai-codex  gpt-5.4                     272K     128K     yes       yes\n"
    "openrouter    anthropic/claude-sonnet-5   1M       64K      yes       yes\n"
)
# What pi prints instead of a table when no provider is authenticated.
PI_NO_MODELS_OUTPUT = "No models available. Use /login to log into a provider via OAuth or API key.\n"


def _runner(*, returncode: int = 0, stdout: str = "", stderr: str = ""):
    """Return an injectable runner standing in for a real `pi` binary."""

    def run(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        run.calls.append((command, env))
        return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)

    run.calls = []
    return run


def _discover(tmp_path, runner):
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    return database_path, discover_orchestrator_models(
        database_path, agent_dir=tmp_path / "agent", runner=runner
    )


def test_discovery_parses_the_table_into_provider_qualified_ids(tmp_path) -> None:
    _database_path, result = _discover(tmp_path, _runner(stdout=PI_MODEL_TABLE))

    assert result.state == DISCOVERY_READY
    assert result.passed is True
    assert result.models == [
        "anthropic/claude-opus-5",
        "openai-codex/gpt-5.4",
        "openrouter/anthropic/claude-sonnet-5",
    ]
    # The header row's model column reads "model", which is what rejects it.
    assert "provider/model" not in result.models


def test_discovery_runs_list_models_under_the_pi_agent_dir(tmp_path) -> None:
    runner = _runner(stdout=PI_MODEL_TABLE)

    _discover(tmp_path, runner)

    command, env = runner.calls[0]
    assert command == ["pi", "--list-models"]
    assert env["PI_CODING_AGENT_DIR"] == str(tmp_path / "agent")


def test_empty_inventory_is_the_authenticate_state_not_a_failure(tmp_path) -> None:
    _database_path, result = _discover(tmp_path, _runner(stdout=PI_NO_MODELS_OUTPUT))

    assert result.models == []
    assert result.state == DISCOVERY_NEEDS_AUTHENTICATION
    assert result.needs_authentication is True
    assert result.passed is False
    assert result.evidence["returncode"] == 0
    assert any("pi /login" in reason for reason in result.reasons)


def test_discovery_failure_is_distinct_from_an_empty_inventory(tmp_path) -> None:
    _database_path, failed = _discover(
        tmp_path, _runner(returncode=2, stderr="pi: unknown flag --list-models")
    )
    _database_path, empty = _discover(tmp_path, _runner(stdout=PI_NO_MODELS_OUTPUT))

    assert failed.state == DISCOVERY_FAILED
    assert failed.needs_authentication is False
    assert empty.needs_authentication is True
    # Both are "no models", but they are never the same state.
    assert failed.models == empty.models == []
    assert failed.state != empty.state


def test_an_unlaunchable_pi_is_a_discovery_failure(tmp_path) -> None:
    def explode(_command, _env):
        raise FileNotFoundError("pi")

    _database_path, result = _discover(tmp_path, explode)

    assert result.state == DISCOVERY_FAILED
    assert result.evidence["returncode"] == 127
    assert "FileNotFoundError" in result.evidence["stderr"]


def test_discovery_persists_sanitized_evidence_on_the_orchestrator_status_record(tmp_path) -> None:
    database_path, result = _discover(
        tmp_path,
        _runner(stdout=PI_MODEL_TABLE, stderr="Authorization: Bearer tok_abcdef123"),
    )

    status = db.get_execution_backend_status(database_path, ORCHESTRATOR_STATUS_RECORD_ID)
    evidence = status["details"]["model_discovery"]
    assert evidence["models"] == result.models
    assert evidence["returncode"] == 0
    assert evidence["discovered_at"]
    assert "claude-opus-5" in evidence["stdout"]
    assert "tok_abcdef123" not in evidence["stderr"]
    assert "***REDACTED***" in evidence["stderr"]
    assert persisted_orchestrator_discovery(database_path) == evidence


def test_discovery_merges_into_details_without_claiming_verification(tmp_path) -> None:
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    db.upsert_execution_backend_status(
        database_path,
        ORCHESTRATOR_STATUS_RECORD_ID,
        name="Orchestrator Model",
        online=True,
        details={"status": "verified"},
    )

    discover_orchestrator_models(
        database_path, agent_dir=tmp_path / "agent", runner=_runner(stdout=PI_MODEL_TABLE)
    )

    status = db.get_execution_backend_status(database_path, ORCHESTRATOR_STATUS_RECORD_ID)
    # Listing an inventory is not a verification turn, so it neither sets nor clears online.
    assert status["online"] is True
    assert status["details"]["status"] == "verified"
    assert status["details"]["model_discovery"]["state"] == DISCOVERY_READY


@pytest.mark.parametrize(
    "model",
    [
        "anthropic/claude-opus-5",
        "openai-codex/gpt-5.4",
        "openrouter/anthropic/claude-sonnet-5",
    ],
)
def test_provider_qualified_ids_are_accepted(model: str) -> None:
    assert is_provider_qualified_model(model) is True


@pytest.mark.parametrize(
    "model",
    [
        None,
        "",
        "gpt-5.4",  # bare id: never auto-qualified by guessing a provider
        "claude-opus-5",
        "/gpt-5.4",
        "anthropic/",
        "anthropic/claude-*",  # pi accepts patterns; the setting must not
        "anthropic/*",
        "provider/model",  # the table header
        "No/models",  # the empty-auth guidance line
    ],
)
def test_unqualified_and_pattern_values_are_rejected(model: str | None) -> None:
    assert is_provider_qualified_model(model) is False


def test_resolution_requires_presence_in_persisted_evidence(tmp_path) -> None:
    database_path, _result = _discover(tmp_path, _runner(stdout=PI_MODEL_TABLE))

    assert discovered_orchestrator_models(database_path) == [
        "anthropic/claude-opus-5",
        "openai-codex/gpt-5.4",
        "openrouter/anthropic/claude-sonnet-5",
    ]
    assert resolve_orchestrator_model(database_path, "anthropic/claude-opus-5") == (
        "anthropic/claude-opus-5"
    )
    # Qualified but no longer offered by pi: not configured, never repaired.
    assert resolve_orchestrator_model(database_path, "anthropic/claude-retired-1") is None
    # A bare id is not configured even when the inventory holds the same model.
    assert resolve_orchestrator_model(database_path, "gpt-5.4") is None
    assert resolve_orchestrator_model(database_path, None) is None


@pytest.mark.unconfigured_orchestrator
def test_resolution_without_any_evidence_is_not_configured(tmp_path) -> None:
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)

    assert persisted_orchestrator_discovery(database_path) == {}
    assert discovered_orchestrator_models(database_path) == []
    assert resolve_orchestrator_model(database_path, "anthropic/claude-opus-5") is None


# --- Verification: a real metered turn, not inventory presence -----------------


def _fake_launcher(database_path, *, record_token: bool, stdout: str, returncode: int = 0):
    """Stand in for `launch_pi_once`, optionally recording the metered turn."""

    def launcher(db_path, prompt, *, model, agent_dir=None, timeout=None, usage_kind="planning", **kwargs):
        session, _ = db.create_planning_session(
            db_path,
            task_description="orchestrator verification",
            model=model,
            tracking_mode="native_usage",
        )
        if record_token:
            db.record_token_turn(
                db_path,
                session_id=session["id"],
                usage_kind=usage_kind,
                model=model,
                prompt_tokens=5,
                completion_tokens=2,
                cost=0.0,
                raw_usage={"model": model},
            )
        return session, PiOnceResult(stdout=stdout, stderr="", returncode=returncode, args=["pi"])

    return launcher


def test_verification_passes_only_with_sentinel_and_recorded_token(tmp_path) -> None:
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    model = "anthropic/claude-opus-5"

    result = verify_orchestrator_model(
        database_path,
        model,
        launcher=_fake_launcher(database_path, record_token=True, stdout=SENTINEL_RESPONSE),
    )

    assert result.passed is True
    assert result.reasons == []
    assert persisted_orchestrator_verification(database_path)["passed"] is True


def test_verification_fails_when_sentinel_matched_but_nothing_was_metered(tmp_path) -> None:
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)

    result = verify_orchestrator_model(
        database_path,
        "anthropic/claude-opus-5",
        launcher=_fake_launcher(database_path, record_token=False, stdout=SENTINEL_RESPONSE),
    )

    # A matched sentinel alone proves the command ran, not that spend is accounted.
    assert result.passed is False
    assert any("token turn was recorded" in reason for reason in result.reasons)


def test_verification_fails_when_the_sentinel_does_not_match(tmp_path) -> None:
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)

    result = verify_orchestrator_model(
        database_path,
        "anthropic/claude-opus-5",
        launcher=_fake_launcher(database_path, record_token=True, stdout="something else entirely"),
    )

    assert result.passed is False
    assert any("sentinel" in reason for reason in result.reasons)


def test_verification_refuses_an_unqualified_model_without_starting_a_turn(tmp_path) -> None:
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)

    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("no turn may start for an unqualified model")

    result = verify_orchestrator_model(database_path, "gpt-5.4", launcher=explode)

    assert result.passed is False
    assert result.session_id is None


def test_changing_the_model_makes_existing_verification_stale(tmp_path) -> None:
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    verify_orchestrator_model(
        database_path,
        "anthropic/claude-opus-5",
        launcher=_fake_launcher(database_path, record_token=True, stdout=SENTINEL_RESPONSE),
    )
    evidence = persisted_orchestrator_verification(database_path)

    # Saving a different model does not erase the run that proved the old one; it
    # only stops that run from vouching for the new one.
    assert orchestrator_verification_is_stale(evidence, "openai-codex/gpt-5.4") is True
    assert orchestrator_verification_is_stale(evidence, "anthropic/claude-opus-5") is False
