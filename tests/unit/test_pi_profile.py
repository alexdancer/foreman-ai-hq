from foreman_ai_hq.pi_adapter import DEFAULT_PROFILE_DIR


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
