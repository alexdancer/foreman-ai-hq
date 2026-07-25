from foreman_ai_hq.pi_adapter import DEFAULT_EXTENSIONS_DIR, DEFAULT_PROFILE_DIR


def test_orchestrator_persona_is_tracked_and_safe():
    persona_path = DEFAULT_PROFILE_DIR / "orchestrator.md"
    assert persona_path.is_file()

    text = persona_path.read_text(encoding="utf-8")

    # Planning contract encoded in the persona.
    lowered = text.lower()
    assert "one question per turn" in lowered
    assert "lead" in lowered
    assert "recommendation" in lowered
    assert "planning" in lowered
    assert "spec" in lowered

    # Stable marker for e2e verification.
    assert "FOREMAN_AI_HQ_ORCHESTRATOR_V1" in text

    # No secret material.
    assert "sk_" not in text
    assert "api_key" not in text.lower()
    assert "bearer" not in text.lower()


def test_structured_job_personas_and_submit_extensions_are_tracked_and_safe():
    estimator = (DEFAULT_PROFILE_DIR / "estimator.md").read_text(encoding="utf-8")
    breakdown = (DEFAULT_PROFILE_DIR / "task_breakdown.md").read_text(encoding="utf-8")
    submit_estimate = (DEFAULT_EXTENSIONS_DIR / "submit-estimate.ts").read_text(encoding="utf-8")
    submit_breakdown = (DEFAULT_EXTENSIONS_DIR / "submit-breakdown.ts").read_text(encoding="utf-8")

    assert "submit_estimate" in estimator
    assert "read_curated_input" in estimator
    assert "submit_breakdown" in breakdown
    assert "read_curated_input" in breakdown
    assert "investigation_recommended" in submit_estimate
    assert "terminate: true" in submit_estimate
    assert "additionalProperties: false" in submit_estimate
    assert 'join(process.cwd(), "job-input.json")' in submit_estimate
    assert "acceptance_verification" in submit_breakdown
    assert "terminate: true" in submit_breakdown
    assert "additionalProperties: false" in submit_breakdown
    assert 'join(process.cwd(), "job-input.json")' in submit_breakdown
    for text in (estimator, breakdown, submit_estimate, submit_breakdown):
        assert "sk_live" not in text
        assert "sk_test" not in text
        assert "api_key=" not in text.lower()
        assert "bearer " not in text.lower()
