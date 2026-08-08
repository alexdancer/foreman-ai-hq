import json
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from foreman_ai_hq import db
from foreman_ai_hq.app import create_app
from foreman_ai_hq.native_usage import parse_native_usage_evidence
from foreman_ai_hq.settings import Settings
from foreman_ai_hq.worker_adapters import SENTINEL_RESPONSE, verify_worker_adapter

ROOT = Path(__file__).resolve().parents[2]
PORTAL_TOKEN = "test-portal-token"


def _auth_headers():
    return {"Authorization": f"Bearer {PORTAL_TOKEN}"}


def _client(tmp_path):
    settings = Settings(
        database_path=tmp_path / "harness.db",
        guardrails_path=ROOT / "guardrails.yaml",
        portal_auth_required=True,
    )
    return TestClient(create_app(settings))


class FakeRunner:
    def __init__(self, stdout=SENTINEL_RESPONSE, returncode=0, stderr=""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr
        self.calls = []

    def __call__(self, plan):
        self.calls.append(plan)
        return {"returncode": self.returncode, "stdout": self.stdout, "stderr": self.stderr}


def _codex_native_stdout(
    *, sentinel: bool = True, usage: dict | None = None, model: str | None = None, thread_model: str | None = None
) -> str:
    thread_event = {"type": "thread.started", "thread_id": "thread_2099_demo_codex"}
    if thread_model:
        thread_event["model"] = thread_model
    events = [json.dumps(thread_event)]
    if sentinel:
        events.append(json.dumps({"type": "item.completed", "item": {"text": SENTINEL_RESPONSE}}))
    payload = {
        "type": "turn.completed",
        "usage": usage
        or {
            "input_tokens": 25,
            "cached_input_tokens": 10,
            "output_tokens": 7,
            "reasoning_output_tokens": 3,
        },
    }
    if model:
        payload["model"] = model
    events.append(json.dumps(payload))
    return "\n".join(events)


def test_verify_worker_adapter_uses_fake_runner_sentinel_and_requires_token_row(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "opencode",
        workdir=str(tmp_path),
        config={"verification_template": ["opencode", "run", "{prompt}"]},
        supported_models=["opencode/gpt-5.1"],
    )
    runner = FakeRunner()

    result = verify_worker_adapter(
        db_path,
        "opencode",
        model="opencode/gpt-5.1",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=runner,
        token_recorder=lambda session_id: db.record_token_turn(
            db_path,
            session_id=session_id,
            usage_kind="adapter_verification",
            model="opencode/gpt-5.1",
            prompt_tokens=5,
            completion_tokens=1,
            cost=0,
            raw_usage={"total_tokens": 6},
        ),
    )

    adapter = db.get_worker_adapter(db_path, "opencode")
    session = db.get_session(db_path, result.session_id)
    artifact = db.build_session_artifact(db_path, result.session_id)
    assert result.passed is True
    assert session["status"] == "completed"
    assert adapter["verification_status"] == "verified"
    assert adapter["verification_evidence"]["tracking_mode"] == "proxy_governed"
    assert adapter["verification_evidence"]["tracking_authoritative"] is True
    assert adapter["verification_evidence"]["sentinel_matched"] is True
    assert artifact["token_log"][0]["usage_kind"] == "adapter_verification"
    assert artifact["token_log"][0]["model"] == "opencode/gpt-5.1"
    assert len(runner.calls) == 1
    assert runner.calls[0].env["FOREMAN_AI_HQ_SESSION_API_KEY"].startswith("sk_sess_")
    assert runner.calls[0].env["OPENAI_BASE_URL"] == "http://127.0.0.1:8000/v1"
    assert runner.calls[0].env["OPENAI_API_KEY"] == runner.calls[0].env["FOREMAN_AI_HQ_SESSION_API_KEY"]
    assert runner.calls[0].command == [
        "opencode",
        "run",
        "Verification only. Do not read files, write files, run tools, or inspect the repository. Reply exactly FOREMAN_AI_HQ_ADAPTER_OK",
    ]
    assert runner.calls[0].cwd == tmp_path
    assert "sk_sess_" not in str(adapter["verification_evidence"])


def test_verify_worker_adapter_fails_when_token_row_missing_even_if_sentinel_matches(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "codex",
        workdir=str(tmp_path),
        config={"verification_template": ["codex", "--prompt", "{prompt}"]},
        supported_models=["gpt-5.6-terra"],
    )

    result = verify_worker_adapter(
        db_path,
        "codex",
        model="gpt-5.6-terra",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=FakeRunner(),
    )

    adapter = db.get_worker_adapter(db_path, "codex")
    session = db.get_session(db_path, result.session_id)
    assert result.passed is False
    assert session["status"] == "failed"
    assert "No adapter_verification token row was recorded for selected model." in result.reasons
    assert adapter["verification_status"] == "failed"
    assert adapter["verification_evidence"]["tracking_mode"] == "observed_only"
    assert adapter["verification_evidence"]["tracking_authoritative"] is False
    assert adapter["verification_evidence"]["sentinel_matched"] is True


def test_direct_proxy_token_row_without_adapter_process_does_not_mark_launchable(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    session = db.create_session(
        db_path,
        task_description="Direct proxy call",
        model="opencode/gpt-5.1",
        session_key_hash="hash-direct",
        guardrail_overrides={},
    )
    db.record_token_turn(
        db_path,
        session_id=session["id"],
        usage_kind="adapter_verification",
        model="opencode/gpt-5.1",
        prompt_tokens=1,
        completion_tokens=1,
        cost=0,
        raw_usage={"total_tokens": 2},
    )

    adapter = db.get_worker_adapter(db_path, "opencode")

    assert adapter["verification_status"] == "unverified"
    assert db.has_verified_worker_adapter(db_path) is False


def test_verify_worker_adapter_does_not_pass_provider_api_key_to_worker_env(tmp_path, monkeypatch):
    monkeypatch.setenv("PROVIDER_API_KEY", "provider-secret")
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "opencode",
        workdir=str(tmp_path),
        config={"verification_template": ["opencode", "run", "{prompt}"]},
        supported_models=["opencode/gpt-5.1"],
    )
    runner = FakeRunner()

    verify_worker_adapter(
        db_path,
        "opencode",
        model="opencode/gpt-5.1",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=runner,
        token_recorder=lambda session_id: db.record_token_turn(
            db_path,
            session_id=session_id,
            usage_kind="adapter_verification",
            model="opencode/gpt-5.1",
            prompt_tokens=5,
            completion_tokens=1,
            cost=0,
            raw_usage={"total_tokens": 6},
        ),
    )

    assert "PROVIDER_API_KEY" not in runner.calls[0].env
    assert "provider-secret" not in str(runner.calls[0].env)


def test_verify_worker_adapter_fails_for_wrong_sentinel_without_real_cli(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "claude_code",
        workdir=str(tmp_path),
        config={"verification_template": ["claude", "-p", "{prompt}"], "allowed_models_configured": True},
        supported_models=["claude-opus-4-8"],
    )

    result = verify_worker_adapter(
        db_path,
        "claude_code",
        model="claude-opus-4-8",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=FakeRunner(stdout="not ok"),
        token_recorder=lambda session_id: db.record_token_turn(
            db_path,
            session_id=session_id,
            usage_kind="adapter_verification",
            model="claude-opus-4-8",
            prompt_tokens=5,
            completion_tokens=1,
            cost=0,
            raw_usage={"total_tokens": 6},
        ),
    )

    assert result.passed is False
    assert "Adapter did not return exact verification sentinel." in result.reasons


def test_verify_worker_adapter_fails_fast_without_runner_when_model_unsupported(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "codex",
        workdir=str(tmp_path),
        config={"verification_template": ["codex", "--prompt", "{prompt}"]},
        supported_models=["gpt-5.6-terra"],
    )
    runner = FakeRunner()

    result = verify_worker_adapter(
        db_path,
        "codex",
        model="unsupported-model",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=runner,
    )

    adapter = db.get_worker_adapter(db_path, "codex")
    session = db.get_session(db_path, result.session_id)
    assert result.passed is False
    assert session["status"] == "failed"
    assert "Selected model is not supported by this adapter." in result.reasons
    assert runner.calls == []
    assert adapter["verification_status"] == "failed"
    assert adapter["verification_evidence"]["preflight_failed"] is True


def test_verify_worker_adapter_marks_failed_evidence_when_cli_is_missing(tmp_path, monkeypatch):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "codex",
        workdir=str(tmp_path),
        config={"verification_template": ["missing-codex", "--api-key", "abc123", "--prompt", "{prompt}"]},
        supported_models=["gpt-5.6-terra"],
    )

    def fake_run(*args, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", args[0][0])

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = verify_worker_adapter(
        db_path,
        "codex",
        model="gpt-5.6-terra",
        proxy_url="http://127.0.0.1:8000/v1",
    )

    adapter = db.get_worker_adapter(db_path, "codex")
    session = db.get_session(db_path, result.session_id)
    serialized = str(adapter["verification_evidence"])
    assert result.passed is False
    assert "Adapter verification command failed." in result.reasons
    assert adapter["verification_status"] == "failed"
    assert session["status"] == "failed"
    assert adapter["verification_evidence"]["returncode"] != 0
    assert "Failed to launch command" in adapter["verification_evidence"]["stderr"]
    assert "abc123" not in serialized


def test_verify_worker_adapter_attaches_claude_code_login_diagnostic(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "claude_code",
        workdir=str(tmp_path),
        config={"allowed_models_configured": True},
        supported_models=["claude-opus-4-8"],
    )
    stdout = json.dumps({"type": "error", "message": "Not logged in · Please run /login", "is_error": True})

    result = verify_worker_adapter(
        db_path,
        "claude_code",
        model="claude-opus-4-8",
        proxy_url="http://127.0.0.1:8000/v1",
        tracking_mode="native_usage",
        runner=FakeRunner(stdout=stdout, returncode=1),
    )

    evidence = db.get_worker_adapter(db_path, "claude_code")["verification_evidence"]
    assert result.passed is False
    assert evidence["tracking_authoritative"] is False
    assert evidence["diagnostic"]["summary"] == "Not logged in · Please run /login"
    assert evidence["diagnostic"]["next_action"] == "Run `/login` in Claude Code, then verify the adapter again."
    assert evidence["diagnostic"]["setup_href"] == "/settings/workers"


def test_verify_worker_adapter_returns_sanitized_evidence(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "opencode",
        workdir=str(tmp_path),
        config={"verification_template": ["opencode", "--api-key", "secret-value", "{prompt}"]},
        supported_models=["opencode/gpt-5.1"],
    )

    result = verify_worker_adapter(
        db_path,
        "opencode",
        model="opencode/gpt-5.1",
        proxy_url="http://127.0.0.1:8000/v1",
        runner=FakeRunner(stdout="api_key=abc123 secret-output", stderr="Bearer abc.def"),
    )

    stored = db.get_worker_adapter(db_path, "opencode")["verification_evidence"]
    assert result.evidence == stored
    serialized = str(result.evidence)
    assert "secret" not in serialized
    assert "api_key=abc123" not in serialized
    assert "Bearer abc.def" not in serialized
    assert "sk_sess_" not in serialized
    assert "***REDACTED***" in serialized


def test_verify_worker_adapter_observed_only_records_diagnostic_not_authority(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "opencode",
        workdir=str(tmp_path),
        config={"native_verification_template": ["opencode", "run", "--format", "json", "{prompt}"]},
        supported_models=["opencode/gpt-5.1"],
    )
    runner = FakeRunner(stdout=json.dumps({"type": "message", "content": SENTINEL_RESPONSE}))

    result = verify_worker_adapter(
        db_path,
        "opencode",
        model="opencode/gpt-5.1",
        proxy_url="http://127.0.0.1:8000/v1",
        tracking_mode="observed_only",
        runner=runner,
    )

    adapter = db.get_worker_adapter(db_path, "opencode")
    assert result.passed is True
    assert adapter["verification_status"] == "verified"
    assert adapter["verification_evidence"]["tracking_mode"] == "observed_only"
    assert adapter["verification_evidence"]["tracking_authoritative"] is False
    assert db.has_adapter_verification_token(db_path, session_id=result.session_id, model="opencode/gpt-5.1") is False


def test_parse_claude_code_native_usage_counts_cache_tokens_and_cost():
    stdout = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "session_id": "session_2099_demo_claude",
            "total_cost_usd": 0.0065403,
            "usage": {
                "input_tokens": 3,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 21571,
                "output_tokens": 4,
            },
            "modelUsage": {
                "claude-sonnet-4-6": {
                    "inputTokens": 3,
                    "outputTokens": 4,
                    "cacheReadInputTokens": 21571,
                    "cacheCreationInputTokens": 0,
                    "costUSD": 0.0065403,
                }
            },
        }
    )

    evidence = parse_native_usage_evidence(stdout, model="sonnet", returncode=0)

    assert evidence is not None
    assert evidence.prompt_tokens == 21574
    assert evidence.completion_tokens == 4
    assert evidence.total_tokens == 21578
    assert evidence.cost == 0.0065403
    assert evidence.raw_usage["source"]["modelUsage"]["claude-sonnet-4-6"]["costUSD"] == 0.0065403


def test_parse_claude_code_native_usage_requires_cost_evidence():
    stdout = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "session_id": "session_2099_demo_claude",
            "usage": {"input_tokens": 3, "cache_read_input_tokens": 21, "output_tokens": 4},
        }
    )

    evidence = parse_native_usage_evidence(stdout, model="sonnet", returncode=0)

    assert evidence is None


def test_native_usage_preserves_opencode_and_claude_tokens_with_invalid_costs(
    tmp_path,
):
    cases = [
        (
            "opencode/gpt-5.1",
            {
                "type": "usage",
                "model": "opencode/gpt-5.1",
                "run_id": "run_invalid_cost",
                "usage": {
                    "input_tokens": 7,
                    "output_tokens": 2,
                    "total_tokens": 9,
                    "cost_usd": -0.01,
                },
            },
            9,
        ),
        (
            "sonnet",
            {
                "type": "result",
                "subtype": "success",
                "session_id": "session_invalid_cost",
                "usage": {"input_tokens": 3, "output_tokens": 4},
                "modelUsage": {
                    "claude-sonnet-4-6": {"costUSD": float("nan")}
                },
            },
            7,
        ),
    ]
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)

    for index, (model, payload, expected_tokens) in enumerate(cases):
        evidence = parse_native_usage_evidence(json.dumps(payload), model=model)

        assert evidence is not None
        assert evidence.total_tokens == expected_tokens
        assert evidence.cost == 0.0
        assert evidence.raw_usage["cost_unavailable"] is True
        json.dumps(evidence.raw_usage, allow_nan=False)
        if model == "opencode/gpt-5.1":
            assert evidence.raw_usage["usage"]["cost_usd"] is None
            assert evidence.raw_usage["source"]["usage"]["cost_usd"] is None
        else:
            assert evidence.raw_usage["source"]["modelUsage"]["claude-sonnet-4-6"]["costUSD"] is None

        session = db.create_session(
            db_path,
            task_description=f"invalid native cost {index}",
            model=model,
            session_key_hash=f"invalid-native-cost-{index}",
            guardrail_overrides={},
            status="completed",
        )
        db.record_token_turn(
            db_path,
            session_id=session["id"],
            usage_kind="adapter_verification",
            model=model,
            prompt_tokens=evidence.prompt_tokens,
            completion_tokens=evidence.completion_tokens,
            cost=evidence.cost,
            raw_usage=evidence.raw_usage,
        )
        turn = db.build_session_artifact(db_path, session["id"])["token_log"][0]
        assert turn["total_tokens"] == expected_tokens
        assert turn["cost"] is None
        assert turn["raw_usage"]["cost_unavailable"] is True


def test_invalid_native_cost_serializes_through_verify_and_artifact_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    stdout = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "session_id": "session_invalid_cost_route",
            "result": SENTINEL_RESPONSE,
            "usage": {"input_tokens": 3, "output_tokens": 4},
            "modelUsage": {"claude-sonnet-4-6": {"costUSD": "$Infinity"}},
        }
    )

    with _client(tmp_path) as client:
        db.update_worker_adapter(
            tmp_path / "harness.db",
            "claude_code",
            workdir=str(tmp_path),
            supported_models=["sonnet"],
        )
        client.app.state.worker_adapter_verification_runner = FakeRunner(stdout=stdout)
        response = client.post(
            "/settings/workers/claude_code/verify",
            headers=_auth_headers(),
            json={"model": "sonnet", "tracking_mode": "native_usage"},
        )
        artifact = client.get(
            f"/session/{response.json()['session_id']}/artifact",
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    response_usage = response.json()["evidence"]["native_usage"]
    assert response_usage["cost_unavailable"] is True
    assert response_usage["source"]["modelUsage"]["claude-sonnet-4-6"]["costUSD"] is None
    assert artifact.status_code == 200
    turn = artifact.json()["token_log"][0]
    assert turn["total_tokens"] == 7
    assert turn["cost"] is None
    assert turn["raw_usage"]["cost_unavailable"] is True
    assert turn["raw_usage"]["source"]["modelUsage"]["claude-sonnet-4-6"]["costUSD"] is None


def test_native_usage_sanitizes_formatted_cost_values():
    cases = [
        ("$-0.01", None, 0.0, True),
        ("$NaN", None, 0.0, True),
        ("-$1,000", None, 0.0, True),
        ("$0.00", "$0.00", 0.0, False),
        ("$1,234.50", "$1,234.50", 1234.5, False),
        ("provider estimate unavailable", "provider estimate unavailable", 0.0, True),
    ]

    for raw_cost, expected_raw, expected_cost, unavailable in cases:
        payload = {
            "type": "usage",
            "model": "opencode/gpt-5.1",
            "run_id": "run_formatted_cost",
            "usage": {
                "input_tokens": 7,
                "output_tokens": 2,
                "total_tokens": 9,
                "cost_usd": raw_cost,
            },
        }

        evidence = parse_native_usage_evidence(json.dumps(payload), model="opencode/gpt-5.1")

        assert evidence is not None
        assert evidence.cost == expected_cost
        assert evidence.raw_usage["usage"]["cost_usd"] == expected_raw
        assert evidence.raw_usage["source"]["usage"]["cost_usd"] == expected_raw
        assert evidence.raw_usage.get("cost_unavailable", False) is unavailable
        json.dumps(evidence.raw_usage, allow_nan=False)


def test_parse_codex_turn_completed_usage_accepts_costless_run_bound_tokens():
    evidence = parse_native_usage_evidence(_codex_native_stdout(), model="5.4", returncode=0)

    assert evidence is not None
    assert evidence.prompt_tokens == 25
    assert evidence.completion_tokens == 7
    assert evidence.total_tokens == 35
    assert evidence.cost == 0.0
    assert evidence.raw_usage["run_binding"] == {"thread_id": "thread_2099_demo_codex"}
    assert evidence.raw_usage["cost_unavailable"] is True


def test_parse_codex_turn_completed_usage_accepts_gpt_prefixed_chatgpt_models():
    evidence = parse_native_usage_evidence(_codex_native_stdout(), model="gpt-5.6-terra", returncode=0)

    assert evidence is not None
    assert evidence.raw_usage["model"] == "gpt-5.6-terra"


def test_parse_codex_turn_completed_usage_accepts_gpt_5_5_model():
    evidence = parse_native_usage_evidence(_codex_native_stdout(), model="gpt-5.5", returncode=0)

    assert evidence is not None
    assert evidence.raw_usage["model"] == "gpt-5.5"


def test_parse_codex_turn_completed_usage_rejects_bare_5_5_model():
    evidence = parse_native_usage_evidence(_codex_native_stdout(), model="5.5", returncode=0)

    assert evidence is None


def test_parse_codex_turn_completed_usage_rejects_unbound_tokens():
    stdout = json.dumps(
        {
            "type": "turn.completed",
            "usage": {"input_tokens": 25, "cached_input_tokens": 10, "output_tokens": 7},
        }
    )

    evidence = parse_native_usage_evidence(stdout, model="5.4", returncode=0)

    assert evidence is None


def test_parse_codex_turn_completed_usage_rejects_mismatched_model():
    evidence = parse_native_usage_evidence(_codex_native_stdout(model="5.5"), model="5.4", returncode=0)

    assert evidence is None


def test_parse_codex_turn_completed_usage_rejects_mismatched_thread_model():
    evidence = parse_native_usage_evidence(_codex_native_stdout(thread_model="5.5"), model="5.4", returncode=0)

    assert evidence is None


def test_parse_codex_turn_completed_usage_rejects_failed_costless_run():
    evidence = parse_native_usage_evidence(
        _codex_native_stdout(),
        model="5.4",
        returncode=1,
        allow_failed_returncode=True,
    )

    assert evidence is None


def test_parse_claude_code_native_usage_rejects_unrelated_model_usage_cost():
    stdout = json.dumps(
        {
            "type": "result",
            "session_id": "session_2099_demo_claude",
            "usage": {"input_tokens": 3, "cache_read_input_tokens": 21, "output_tokens": 4},
            "modelUsage": {"claude-haiku-4-6": {"costUSD": 0.001}},
        }
    )

    evidence = parse_native_usage_evidence(stdout, model="sonnet", returncode=0)

    assert evidence is None


def test_parse_native_usage_rejects_unrelated_model_usage_with_top_level_cost():
    stdout = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "session_id": "session_2099_demo_claude",
            "total_cost_usd": 0.05,
            "usage": {"input_tokens": 3, "output_tokens": 4},
            "modelUsage": {"claude-haiku-4-6": {"costUSD": 0.001}},
        }
    )

    evidence = parse_native_usage_evidence(stdout, model="sonnet", returncode=0)

    assert evidence is None


def test_parse_native_usage_rejects_missing_model_evidence():
    stdout = json.dumps(
        {
            "session_id": "session_2099_demo_claude",
            "total_cost_usd": 0.01,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
    )

    evidence = parse_native_usage_evidence(stdout, model="sonnet", returncode=0)

    assert evidence is None


def test_verify_claude_code_native_usage_records_cache_inclusive_authority(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(db_path, "claude_code", workdir=str(tmp_path), supported_models=["sonnet"])
    stdout = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "session_id": "session_2099_demo_claude",
            "result": SENTINEL_RESPONSE,
            "total_cost_usd": 0.0065403,
            "usage": {
                "input_tokens": 3,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 21571,
                "output_tokens": 4,
            },
            "modelUsage": {"claude-sonnet-4-6": {"costUSD": 0.0065403}},
        }
    )

    result = verify_worker_adapter(
        db_path,
        "claude_code",
        model="sonnet",
        proxy_url="http://127.0.0.1:8000/v1",
        tracking_mode="native_usage",
        runner=FakeRunner(stdout=stdout),
    )

    adapter = db.get_worker_adapter(db_path, "claude_code")
    artifact = db.build_session_artifact(db_path, result.session_id)
    assert result.passed is True
    assert adapter["verification_evidence"]["tracking_mode"] == "native_usage"
    assert adapter["verification_evidence"]["tracking_authoritative"] is True
    turn = artifact["token_log"][0]
    assert turn["usage_kind"] == "adapter_verification"
    assert turn["prompt_tokens"] == 21574
    assert turn["completion_tokens"] == 4
    assert turn["total_tokens"] == 21578
    assert turn["cost"] == 0.0065403
    assert turn["raw_usage"]["usage_source"] == "native_usage"


def test_verify_worker_adapter_native_usage_records_authoritative_token_row(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "opencode",
        workdir=str(tmp_path),
        config={"native_verification_template": ["opencode", "run", "--model", "{model}", "--format", "json", "{prompt}"]},
        supported_models=["opencode/gpt-5.1"],
    )
    stdout = "\n".join(
        [
            json.dumps({"type": "message", "content": SENTINEL_RESPONSE}),
            json.dumps(
                {
                    "type": "usage",
                    "model": "opencode/gpt-5.1",
                    "run_id": "run_2099_demo_native_verification",
                    "usage": {
                        "input_tokens": 7,
                        "output_tokens": 2,
                        "total_tokens": 9,
                        "cost_usd": 0.001,
                    },
                }
            ),
        ]
    )
    runner = FakeRunner(stdout=stdout)

    result = verify_worker_adapter(
        db_path,
        "opencode",
        model="opencode/gpt-5.1",
        proxy_url="http://127.0.0.1:8000/v1",
        tracking_mode="native_usage",
        runner=runner,
    )

    adapter = db.get_worker_adapter(db_path, "opencode")
    artifact = db.build_session_artifact(db_path, result.session_id)
    assert result.passed is True
    assert adapter["verification_status"] == "verified"
    assert adapter["verification_evidence"]["tracking_mode"] == "native_usage"
    assert adapter["verification_evidence"]["tracking_authoritative"] is True
    assert adapter["verification_evidence"]["native_usage"]["usage"]["total_tokens"] == 9
    assert artifact["token_log"][0]["usage_kind"] == "adapter_verification"
    assert artifact["token_log"][0]["prompt_tokens"] == 7
    assert artifact["token_log"][0]["completion_tokens"] == 2
    assert artifact["token_log"][0]["raw_usage"]["usage_source"] == "native_usage"
    assert runner.calls[0].env == {}
    assert runner.calls[0].command == [
        "opencode",
        "run",
        "--dir",
        str(tmp_path),
        "--model",
        "opencode/gpt-5.1",
        "--format",
        "json",
        "Verification only. Do not read files, write files, run tools, or inspect the repository. Reply exactly FOREMAN_AI_HQ_ADAPTER_OK",
    ]


def test_verify_codex_native_usage_records_authoritative_costless_token_row(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "codex",
        workdir=str(tmp_path),
        config={"command": "codex"},
        supported_models=["gpt-5.6-terra"],
    )
    runner = FakeRunner(stdout=_codex_native_stdout())

    result = verify_worker_adapter(
        db_path,
        "codex",
        model="gpt-5.6-terra",
        proxy_url="http://127.0.0.1:8000/v1",
        tracking_mode="native_usage",
        runner=runner,
    )

    adapter = db.get_worker_adapter(db_path, "codex")
    artifact = db.build_session_artifact(db_path, result.session_id)
    turn = artifact["token_log"][0]
    assert result.passed is True
    assert adapter["verification_status"] == "verified"
    assert adapter["verification_evidence"]["tracking_mode"] == "native_usage"
    assert adapter["verification_evidence"]["tracking_authoritative"] is True
    assert adapter["verification_evidence"]["native_usage"]["cost_unavailable"] is True
    assert turn["usage_kind"] == "adapter_verification"
    assert turn["model"] == "gpt-5.6-terra"
    assert turn["prompt_tokens"] == 25
    assert turn["completion_tokens"] == 7
    assert turn["total_tokens"] == 35
    assert turn["cost"] is None
    assert turn["raw_usage"]["usage"]["cached_input_tokens"] == 10
    assert turn["raw_usage"]["usage_source"] == "native_usage"
    assert runner.calls[0].command == [
        "codex",
        "exec",
        "--json",
        "--skip-git-repo-check",
        "-m",
        "gpt-5.6-terra",
        "Verification only. Do not read files, write files, run tools, or inspect the repository. Reply exactly FOREMAN_AI_HQ_ADAPTER_OK",
    ]
    assert runner.calls[0].metadata["project_root"] == str(tmp_path)


def test_verify_native_usage_surfaces_cli_error_result(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(db_path, "claude_code", workdir=str(tmp_path), supported_models=["claude-sonnet-4-6"])
    stdout = "\n".join(
        [
            json.dumps(
                {
                    "type": "assistant",
                    "error": "authentication_failed",
                    "message": {"content": [{"type": "text", "text": "Not logged in · Please run /login"}]},
                }
            ),
            json.dumps({"type": "result", "is_error": True, "result": "Not logged in · Please run /login"}),
        ]
    )

    result = verify_worker_adapter(
        db_path,
        "claude_code",
        model="claude-sonnet-4-6",
        proxy_url="http://127.0.0.1:8000/v1",
        tracking_mode="native_usage",
        runner=FakeRunner(stdout=stdout, returncode=1),
    )

    assert result.passed is False
    assert "Adapter CLI reported: Not logged in · Please run /login" in result.reasons


def test_verify_native_usage_surfaces_stderr_cli_error_after_stdout_event(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(db_path, "claude_code", workdir=str(tmp_path), supported_models=["claude-sonnet-4-6"])

    result = verify_worker_adapter(
        db_path,
        "claude_code",
        model="claude-sonnet-4-6",
        proxy_url="http://127.0.0.1:8000/v1",
        tracking_mode="native_usage",
        runner=FakeRunner(
            stdout=json.dumps({"type": "system", "message": "starting"}),
            stderr="Not logged in · Please run /login",
            returncode=1,
        ),
    )

    assert result.passed is False
    assert "Adapter CLI reported: Not logged in · Please run /login" in result.reasons


def test_verify_codex_native_usage_fails_without_usage_evidence(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(db_path, "codex", workdir=str(tmp_path), config={"command": "codex"}, supported_models=["gpt-5.6-terra"])
    result = verify_worker_adapter(
        db_path,
        "codex",
        model="gpt-5.6-terra",
        proxy_url="http://127.0.0.1:8000/v1",
        tracking_mode="native_usage",
        runner=FakeRunner(stdout=json.dumps({"type": "item.completed", "item": {"text": SENTINEL_RESPONSE}})),
    )

    adapter = db.get_worker_adapter(db_path, "codex")
    assert result.passed is False
    assert "No trustworthy native usage evidence was emitted for selected model." in result.reasons
    assert adapter["verification_status"] == "failed"
    assert adapter["verification_evidence"]["tracking_mode"] == "observed_only"
    assert adapter["verification_evidence"]["tracking_authoritative"] is False
    assert not db.has_adapter_verification_token(db_path, session_id=result.session_id, model="gpt-5.6-terra")


def test_verify_worker_adapter_native_usage_accepts_opencode_step_finish_tokens(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "opencode",
        workdir=str(tmp_path),
        config={"native_verification_template": ["opencode", "run", "--model", "{model}", "--format", "json", "{prompt}"]},
        supported_models=["opencode/big-pickle"],
    )
    stdout = "\n".join(
        [
            json.dumps(
                {
                    "type": "text",
                    "sessionID": "ses_demo_2099",
                    "part": {"type": "text", "text": SENTINEL_RESPONSE, "sessionID": "ses_demo_2099"},
                }
            ),
            json.dumps(
                {
                    "type": "step_finish",
                    "sessionID": "ses_demo_2099",
                    "part": {
                        "type": "step-finish",
                        "sessionID": "ses_demo_2099",
                        "messageID": "msg_demo_2099",
                        "model": "opencode/big-pickle",
                        "tokens": {"total": 22245, "input": 22181, "output": 11, "reasoning": 53},
                        "cost": 0,
                    },
                }
            ),
        ]
    )

    result = verify_worker_adapter(
        db_path,
        "opencode",
        model="opencode/big-pickle",
        proxy_url="http://127.0.0.1:8000/v1",
        tracking_mode="native_usage",
        runner=FakeRunner(stdout=stdout),
    )

    adapter = db.get_worker_adapter(db_path, "opencode")
    artifact = db.build_session_artifact(db_path, result.session_id)
    assert result.passed is True
    assert adapter["verification_evidence"]["tracking_mode"] == "native_usage"
    assert adapter["verification_evidence"]["tracking_authoritative"] is True
    assert adapter["verification_evidence"]["native_usage"]["run_binding"] == {"sessionID": "ses_demo_2099"}
    assert artifact["token_log"][0]["prompt_tokens"] == 22181
    assert artifact["token_log"][0]["completion_tokens"] == 11
    assert artifact["token_log"][0]["total_tokens"] == 22245


def test_verify_worker_adapter_native_usage_accepts_opencode_step_finish_without_model(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "opencode",
        workdir=str(tmp_path),
        config={"native_verification_template": ["opencode", "run", "--model", "{model}", "--format", "json", "{prompt}"]},
        supported_models=["openai/gpt-5.4"],
    )
    stdout = "\n".join(
        [
            json.dumps({"type": "text", "sessionID": "ses_demo_2099", "part": {"type": "text", "text": SENTINEL_RESPONSE}}),
            json.dumps(
                {
                    "type": "step_finish",
                    "sessionID": "ses_demo_2099",
                    "part": {
                        "type": "step-finish",
                        "sessionID": "ses_demo_2099",
                        "messageID": "msg_demo_2099",
                        "tokens": {"total": 14766, "input": 7572, "output": 14, "reasoning": 12, "cache": {"write": 0, "read": 7168}},
                        "cost": 0,
                    },
                }
            ),
        ]
    )

    result = verify_worker_adapter(
        db_path,
        "opencode",
        model="openai/gpt-5.4",
        proxy_url="http://127.0.0.1:8000/v1",
        tracking_mode="native_usage",
        runner=FakeRunner(stdout=stdout),
    )

    artifact = db.build_session_artifact(db_path, result.session_id)
    assert result.passed is True
    assert artifact["token_log"][0]["model"] == "openai/gpt-5.4"
    assert artifact["token_log"][0]["prompt_tokens"] == 14740
    assert artifact["token_log"][0]["completion_tokens"] == 14
    assert artifact["token_log"][0]["total_tokens"] == 14766


def test_verify_worker_adapter_native_usage_fails_without_usage_evidence(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "opencode",
        workdir=str(tmp_path),
        config={"native_verification_template": ["opencode", "run", "--format", "json", "{prompt}"]},
        supported_models=["opencode/gpt-5.1"],
    )
    runner = FakeRunner(stdout=json.dumps({"type": "message", "content": SENTINEL_RESPONSE}))

    result = verify_worker_adapter(
        db_path,
        "opencode",
        model="opencode/gpt-5.1",
        proxy_url="http://127.0.0.1:8000/v1",
        tracking_mode="native_usage",
        runner=runner,
    )

    adapter = db.get_worker_adapter(db_path, "opencode")
    assert result.passed is False
    assert "No trustworthy native usage evidence was emitted for selected model." in result.reasons
    assert adapter["verification_evidence"]["tracking_mode"] == "observed_only"
    assert adapter["verification_evidence"]["tracking_authoritative"] is False


def test_verify_worker_adapter_native_usage_rejects_wrong_model_usage(tmp_path):
    db_path = tmp_path / "harness.db"
    db.init_db(db_path)
    db.update_worker_adapter(
        db_path,
        "opencode",
        workdir=str(tmp_path),
        config={"native_verification_template": ["opencode", "run", "--format", "json", "{prompt}"]},
        supported_models=["opencode/gpt-5.1", "opencode/other"],
    )
    stdout = "\n".join(
        [
            json.dumps({"type": "message", "content": SENTINEL_RESPONSE}),
            json.dumps(
                {
                    "type": "usage",
                    "model": "opencode/other",
                    "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                }
            ),
        ]
    )

    result = verify_worker_adapter(
        db_path,
        "opencode",
        model="opencode/gpt-5.1",
        proxy_url="http://127.0.0.1:8000/v1",
        tracking_mode="native_usage",
        runner=FakeRunner(stdout=stdout),
    )

    adapter = db.get_worker_adapter(db_path, "opencode")
    assert result.passed is False
    assert adapter["verification_evidence"]["tracking_mode"] == "observed_only"


def test_worker_adapter_verify_route_requires_auth_uses_injected_runner_and_token_recorder(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    runner = FakeRunner()
    recorded_sessions = []

    def token_recorder(session_id):
        recorded_sessions.append(session_id)
        db.record_token_turn(
            tmp_path / "harness.db",
            session_id=session_id,
            usage_kind="adapter_verification",
            model="gpt-5.6-terra",
            prompt_tokens=5,
            completion_tokens=1,
            cost=0,
            raw_usage={"total_tokens": 6, "api_key": "«redacted:sk_…»"},
        )

    with _client(tmp_path) as client:
        client.app.state.worker_adapter_verification_runner = runner
        client.app.state.worker_adapter_verification_token_recorder = token_recorder
        db.update_worker_adapter(
            tmp_path / "harness.db",
            "codex",
            workdir=str(tmp_path),
            config={
                "verification_template": [
                    "codex",
                    "--prompt",
                    "{prompt}",
                    "--proxy-url",
                    "{proxy_url}",
                    "--session-key",
                    "{session_api_key}",
                ]
            },
            supported_models=["gpt-5.6-terra"],
        )

        unauthorized = client.post(
            "/settings/workers/codex/verify",
            json={"model": "gpt-5.6-terra", "proxy_url": "http://127.0.0.1:8000/v1"},
        )
        response = client.post(
            "/settings/workers/codex/verify",
            headers=_auth_headers(),
            json={"model": "gpt-5.6-terra", "proxy_url": "http://127.0.0.1:8000/v1"},
        )

    body = response.json()
    serialized = str(body)
    assert unauthorized.status_code == 401
    assert response.status_code == 200
    assert body["passed"] is True
    assert body["adapter_id"] == "codex"
    assert len(runner.calls) == 1
    assert len(recorded_sessions) == 1
    assert "sk_sess_" not in serialized
    assert "sk_ses_fake_leak" not in serialized


def test_workers_page_renders_verify_form_without_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        db.update_worker_adapter(
            tmp_path / "harness.db",
            "opencode",
            workdir=str(tmp_path),
            config={
                "env": {"OPENAI_API_KEY": "super-secret-key"},
                "native_verification_template": ["opencode", "run", "--model", "{model}", "--format", "json", "{prompt}"],
            },
            supported_models=["opencode/gpt-5.1"],
        )

        response = client.get("/api/settings/workers?adapter_id=opencode", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_adapter_id"] == "opencode"
    adapter = next(a for a in payload["adapters"] if a["id"] == "opencode")
    assert adapter["configured"] is True
    assert adapter["connection_type"] == "CLI Worker"
    assert adapter["tracking"]["mode"] == "unverified"
    assert adapter["tracking"]["label"] == "Unverified"
    assert any(option["mode"] == "native_usage" for option in adapter["tracking_mode_options"])
    assert adapter["supported_models"] == ["opencode/gpt-5.1"]
    assert adapter["discovered_models"] == []
    assert adapter["launchable"] is False
    assert adapter["diagnostics"] is None
    assert adapter["verification_evidence"] is None
    assert adapter["verification_diagnostic"] is None
    assert "super-secret-key" not in response.text
    assert "sk_sess_" not in response.text


def test_workers_page_separates_api_proxy_worker_from_cli_modes(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        db.update_worker_adapter(
            tmp_path / "harness.db",
            "opencode",
            workdir=str(tmp_path),
            config={
                "verification_template": [
                    "proxy-worker",
                    "--prompt",
                    "{prompt}",
                    "--proxy-url",
                    "{proxy_url}",
                    "--session-key",
                    "{session_api_key}",
                ]
            },
            supported_models=["openai/gpt-5.4-mini"],
        )

        response = client.get("/api/settings/workers?adapter_id=opencode", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_adapter_id"] == "opencode"
    adapter = next(a for a in payload["adapters"] if a["id"] == "opencode")
    assert adapter["configured"] is True
    assert adapter["connection_type"] == "API / Proxy-capable CLI Worker"
    option_modes = {option["mode"] for option in adapter["tracking_mode_options"]}
    assert option_modes == {"proxy_governed", "native_usage", "observed_only"}
    assert any(
        option["mode"] == "proxy_governed" and option["label"] == "API / Proxy: Governed through Harness Proxy"
        for option in adapter["tracking_mode_options"]
    )
    assert adapter["supported_models"] == ["openai/gpt-5.4-mini"]
    assert adapter["discovered_models"] == []
    assert adapter["launchable"] is False
    assert adapter["verification_evidence"] is None


def test_workers_page_does_not_trust_proxy_mode_config_without_proxy_template(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        db.update_worker_adapter(
            tmp_path / "harness.db",
            "opencode",
            workdir=str(tmp_path),
            config={"tracking_modes": ["proxy_governed"], "verification_template": ["opencode", "run", "{prompt}"]},
            supported_models=["opencode/gpt-5.1"],
        )

        response = client.get("/api/settings/workers?adapter_id=opencode", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_adapter_id"] == "opencode"
    adapter = next(a for a in payload["adapters"] if a["id"] == "opencode")
    assert adapter["configured"] is True
    assert adapter["connection_type"] == "CLI Worker"
    option_modes = {option["mode"] for option in adapter["tracking_mode_options"]}
    assert "proxy_governed" not in option_modes
    assert option_modes == {"native_usage", "observed_only"}
    assert adapter["supported_models"] == ["opencode/gpt-5.1"]
    assert adapter["launchable"] is False


def test_workers_page_offers_codex_native_usage_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        db.update_worker_adapter(
            tmp_path / "harness.db",
            "codex",
            workdir=str(tmp_path),
            config={"command": "codex"},
            supported_models=["gpt-5.6-terra"],
        )

        response = client.get("/api/settings/workers?adapter_id=codex", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_adapter_id"] == "codex"
    adapter = next(a for a in payload["adapters"] if a["id"] == "codex")
    assert adapter["configured"] is True
    assert adapter["connection_type"] == "CLI Worker"
    option_modes = {option["mode"] for option in adapter["tracking_mode_options"]}
    assert option_modes == {"native_usage", "observed_only"}
    assert any(
        option["mode"] == "native_usage" and option["label"] == "CLI: Track native usage after run"
        for option in adapter["tracking_mode_options"]
    )
    assert "gpt-5.6-terra" in adapter["discovered_models"]
    assert adapter["supported_models"] == ["gpt-5.6-terra"]
    assert adapter["launchable"] is False


def test_worker_verify_route_rejects_proxy_mode_for_cli_only_adapter(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        db.update_worker_adapter(
            tmp_path / "harness.db",
            "opencode",
            workdir=str(tmp_path),
            config={"verification_template": ["opencode", "run", "{prompt}"]},
            supported_models=["opencode/gpt-5.1"],
        )

        response = client.post(
            "/settings/workers/opencode/verify",
            headers=_auth_headers(),
            json={
                "model": "opencode/gpt-5.1",
                "tracking_mode": "proxy_governed",
                "proxy_url": "http://127.0.0.1:8000/v1",
            },
        )

    assert response.status_code == 422
    assert "not available for this adapter" in response.json()["detail"]


def test_workers_page_normalizes_legacy_native_tracking_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        db.update_worker_adapter(
            tmp_path / "harness.db",
            "opencode",
            workdir=str(tmp_path),
            config={"tracking_modes": ["native"], "verification_template": ["opencode", "run", "{prompt}"]},
            supported_models=["opencode/gpt-5.1"],
        )

        response = client.get("/api/settings/workers?adapter_id=opencode", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_adapter_id"] == "opencode"
    adapter = next(a for a in payload["adapters"] if a["id"] == "opencode")
    assert adapter["configured"] is True
    assert adapter["connection_type"] == "CLI Worker"
    option_modes = {option["mode"] for option in adapter["tracking_mode_options"]}
    assert option_modes == {"native_usage"}
    assert any(
        option["mode"] == "native_usage" and option["label"] == "CLI: Track native usage after run"
        for option in adapter["tracking_mode_options"]
    )
    assert not any(
        option["label"] == "API / Proxy: Governed through Harness Proxy" for option in adapter["tracking_mode_options"]
    )
    assert adapter["supported_models"] == ["opencode/gpt-5.1"]
    assert adapter["launchable"] is False
