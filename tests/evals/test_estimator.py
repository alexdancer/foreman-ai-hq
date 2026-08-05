"""Behavioral evals for the Estimator LLM.

Proves the estimator returns structured output, tracks usage as
estimation tokens, and fails into Blocked tasks without heuristic fallback.
"""

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from foreman_ai_hq import db, estimation
from foreman_ai_hq.app import create_app
from foreman_ai_hq.estimation import (
    EstimatorUnavailableError,
    EstimatorValidationError,
    EstimateResult,
    estimate_task,
)
from foreman_ai_hq.guardrails import load_guardrails
from foreman_ai_hq.settings import Settings
from tests.fake_orchestrator import FakeOrchestratorJobRunner
from foreman_ai_hq.task_breakdown import (
    TASK_BREAKDOWN_MAX_TOKENS,
    TASK_BREAKDOWN_TIMEOUT_SECONDS,
    TaskBreakdownResult,
    TaskBreakdownValidationError,
    breakdown_task_source,
    validate_breakdown_result,
)

ROOT = Path(__file__).resolve().parents[2]
PORTAL_TOKEN = "test-portal-token"

MARKDOWN_EVAL_FIXTURES = {
    "repo_aware": """# DEMO_TASK_2099 repo-aware estimator input

Repository: DEMO_REPO_2099_TOKEN_TRACKER
Date: 2099-04-01

- [ ] Add DEMO_ROUTE_2099_budget_alarm fixture coverage
- [ ] Update DEMO_TEMPLATE_2099_session_report visibility
""".strip(),
    "phased": """# DEMO_TASK_2099 phased markdown task

- [ ] Phase DEMO_PHASE_2099_A: parse markdown intake
- [ ] Phase DEMO_PHASE_2099_B: decompose checklist tasks
- [ ] Phase DEMO_PHASE_2099_C: verify budget dashboard copy
""".strip(),
    "complex_rejection": """# DEMO_TASK_2099 complex manual estimate case

Need to rewrite DEMO_SYSTEM_2099_UNKNOWN with missing acceptance criteria by 2099-05-01.
""".strip(),
}


def _auth_headers():
    return {"Authorization": f"Bearer {PORTAL_TOKEN}"}


class FakeEstimatorLLM:
    """Fake LLM that returns structured estimate JSON or raises on command."""

    def __init__(self, *, content=None, exc=None, usage=None):
        self.content = content or {
            "drivers": {
                "files_to_read": 2,
                "files_to_modify": 1,
                "expected_turns": 3,
                "needs_test_run": True,
            },
            "shadow_token_estimate": 11_000,
            "complexity": "modest",
            "confidence": 0.82,
            "investigation_recommended": False,
            "rationale": "Endpoint plus tests is a modest task.",
            "assumptions": ["No schema migration needed."],
            "risk_flags": ["Integration tests may expand scope"],
            "budget_note": "Within normal daily budget.",
            "source": "llm",
        }
        self.exc = exc
        self.usage = usage or {"prompt_tokens": 111, "completion_tokens": 22, "total_tokens": 133}
        self.requests = []

    async def acompletion(self, request):
        self.requests.append(request)
        if self.exc:
            raise self.exc
        return {
            "choices": [{"message": {"content": json.dumps(self.content)}}],
            "usage": self.usage,
        }




class FakeSequentialLLM:
    def __init__(self, contents):
        self.contents = list(contents)
        self.requests = []
        self.usage = {"prompt_tokens": 111, "completion_tokens": 22, "total_tokens": 133}

    async def acompletion(self, request):
        self.requests.append(request)
        if not self.contents:
            raise AssertionError("unexpected LLM request")
        return {
            "choices": [{"message": {"content": json.dumps(self.contents.pop(0))}}],
            "usage": self.usage,
        }


class FakeRawContentLLM:
    def __init__(self, content):
        self.content = content
        self.requests = []
        self.usage = {"prompt_tokens": 111, "completion_tokens": 22, "total_tokens": 133}

    async def acompletion(self, request):
        self.requests.append(request)
        return {
            "choices": [{"message": {"content": self.content}}],
            "usage": self.usage,
        }


def _breakdown_content(*titles):
    return {
        "decision": "proposed_task_breakdown" if len(titles) > 1 else "single_task",
        "candidates": [
            {
                "kind": "implementation",
                "title": title,
                "objective": f"Deliver {title} as one independently verifiable slice.",
                "prompt": f"Implement {title}",
                "acceptance_criteria": f"{title} has tests.",
                "constraints": [],
                "proof": f"Run targeted tests proving {title}.",
                "why_this_task_exists": f"{title} maps to a distinct behavior from the source contract.",
                "why_not_smaller": "Smaller subtasks would split implementation from proof.",
                "why_not_larger": "Larger tasks would mix sibling source requirements.",
                "dependencies": [],
                "likely_entry_points": ["tests/evals/test_estimator.py"],
                "execution_mode": "AFK",
                "hitl_reason": "",
                "human_in_loop": False,
            }
            for title in titles
        ],
        "rejected_items": [
            {"text": "Date: 2099-04-01", "reason": "context metadata, not a task"}
        ],
        "global_contract_summary": "Accepted slices must collectively preserve DEMO_TASK_2099 output invariants.",
        "global_constraints": ["Do not add network dependencies."],
        "verification": ["Run pytest."],
        "non_goals": [],
        "recommended_sequence": list(titles),
        "confidence": 0.88,
        "rationale": "Task candidates are vertical slices derived from Markdown evidence.",
        "source": "llm",
    }


def _client_with_llm(tmp_path, llm):
    settings = Settings(
        database_path=tmp_path / "harness.db",
        guardrails_path=ROOT / "guardrails.yaml",
        orchestrator_model="openai/gpt-4.1-mini",
        operator_config={},
    )
    app = create_app(settings)
    app.state.llm_client = llm
    app.state.orchestrator_job_runner = FakeOrchestratorJobRunner(llm)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_eval_estimator_returns_all_required_fields():
    """Estimator LLM response is parsed into EstimateResult with all required fields."""
    config = load_guardrails(ROOT / "guardrails.yaml")
    llm = FakeEstimatorLLM()
    result, response = await estimate_task(
        "Add a new REST endpoint with tests",
        config,
        job_runner=FakeOrchestratorJobRunner(llm),
        estimator_model="gpt-4o-mini",
    )

    assert isinstance(result, EstimateResult)
    assert result.token_estimate == 12_345
    assert result.complexity == "modest"
    assert result.confidence == 0.82
    assert result.rationale
    assert isinstance(result.assumptions, list)
    assert isinstance(result.risk_flags, list)
    assert result.budget_note
    assert result.source == "driver_arithmetic"
    assert result.drivers == {
        "files_to_read": 2,
        "files_to_modify": 1,
        "expected_turns": 3,
        "needs_test_run": True,
    }
    assert result.shadow_token_estimate == 11_000
    assert abs(result.estimate_disagreement - 1345 / 12345) < 1e-9
    assert result.coefficient_provenance["g"] == "seed"
    assert result.coefficient_provenance["p"].startswith("fitted")


@pytest.mark.asyncio
async def test_eval_estimator_as_dict_has_expected_keys():
    """EstimateResult.as_dict() returns all expected keys."""
    config = load_guardrails(ROOT / "guardrails.yaml")
    llm = FakeEstimatorLLM()
    result, _ = await estimate_task("Fix a typo", config, job_runner=FakeOrchestratorJobRunner(llm), estimator_model="gpt-4o-mini")

    d = result.as_dict()
    assert set(d.keys()) == {
        "token_estimate", "complexity", "confidence",
        "rationale", "assumptions", "risk_flags", "budget_note", "source",
        "drivers", "shadow_token_estimate", "estimate_disagreement",
        "coefficient_provenance", "investigation_recommended",
    }


@pytest.mark.asyncio
async def test_eval_estimator_token_estimate_is_positive_integer():
    """Token estimate must be a positive integer computed from the drivers."""
    config = load_guardrails(ROOT / "guardrails.yaml")
    llm = FakeEstimatorLLM(content={
        "drivers": {
            "files_to_read": 1,
            "files_to_modify": 0,
            "expected_turns": 2,
            "needs_test_run": False,
        },
        "shadow_token_estimate": 5_000,
        "complexity": "simple",
        "confidence": 0.95,
        "investigation_recommended": False,
        "rationale": "Trivial fix.",
        "assumptions": [],
        "risk_flags": [],
        "budget_note": "",
        "source": "llm",
    })
    result, _ = await estimate_task("Fix a trailing comma", config, job_runner=FakeOrchestratorJobRunner(llm), estimator_model="gpt-4o-mini")
    assert result.token_estimate > 0
    assert isinstance(result.token_estimate, int)


@pytest.mark.asyncio
async def test_eval_task_breakdown_accepts_common_model_json_variants():
    """Task Breakdown Agent tolerates harmless JSON-shape drift from real models."""
    llm = FakeSequentialLLM(
        [
            {
                "decision": "single_task",
                "candidates": [
                    {
                        "kind": "implementation",
                        "title": "Run DEMO_2099 comparison",
                        "objective": "Run DEMO_2099 comparison as one reviewed vertical slice.",
                        "prompt": "Run the comparison demo from the uploaded Markdown.",
                        "acceptance_criteria": ["Portal shows reviewed candidate.", "pytest passes."],
                        "constraints": "Do not add network dependencies.",
                        "proof": "Run pytest and inspect the Portal candidate.",
                        "why_this_task_exists": "The Markdown describes one executable comparison behavior.",
                        "why_not_smaller": "Splitting run and inspection would separate the proof from the task.",
                        "why_not_larger": "There is no sibling implementation slice to merge.",
                        "dependencies": [],
                        "likely_entry_points": ["tests/evals/test_estimator.py"],
                        "execution_mode": "HITL",
                        "hitl_reason": "Operator reviews the Portal candidate after execution.",
                        "human_in_loop": True,
                    }
                ],
                "rejected_items": [],
                "global_contract_summary": "The DEMO_2099 comparison must stay synthetic and verified.",
                "global_constraints": [],
                "verification": ["Run pytest."],
                "non_goals": [],
                "recommended_sequence": ["Run DEMO_2099 comparison"],
                "confidence": 0.84,
                "rationale": "The uploaded Markdown describes one vertical slice.",
                "source": "llm",
                "notes": "Harmless extra provider/model field.",
            }
        ]
    )

    result, _ = await breakdown_task_source(
        "# DEMO_TASK_2099 comparison\n\n- [ ] Run comparison\n- [ ] Run pytest.",
        job_runner=FakeOrchestratorJobRunner(llm),
        task_breakdown_model="gpt-5.4-mini",
    )

    assert isinstance(result, TaskBreakdownResult)
    assert result.global_contract_summary == "The DEMO_2099 comparison must stay synthetic and verified."
    assert result.candidates[0].kind == "implementation"
    assert result.candidates[0].acceptance_criteria == "Portal shows reviewed candidate.\npytest passes."
    assert result.candidates[0].constraints == ["Do not add network dependencies."]


@pytest.mark.asyncio
async def test_task_breakdown_rejects_fenced_json_without_submit_call():
    content = _breakdown_content("Stabilize DEMO_TASK_2099 Claude breakdown")
    llm = FakeRawContentLLM(f"```json\n{json.dumps(content)}\n```")

    with pytest.raises(TaskBreakdownValidationError, match="did not call submit_breakdown"):
        await breakdown_task_source(
            "# DEMO_TASK_2099 Claude breakdown\n\n- [ ] Stabilize Claude JSON output",
            job_runner=FakeOrchestratorJobRunner(llm),
            task_breakdown_model="claude-sonnet-4-6",
        )


@pytest.mark.asyncio
async def test_task_breakdown_request_uses_explicit_large_output_cap():
    llm = FakeSequentialLLM([_breakdown_content("Check DEMO_TASK_2099 request cap")])

    await breakdown_task_source(
        "# DEMO_TASK_2099 Claude breakdown\n\n- [ ] Check request cap",
        job_runner=FakeOrchestratorJobRunner(llm),
        task_breakdown_model="claude-sonnet-4-6",
    )

    assert llm.requests[0]["max_tokens"] == TASK_BREAKDOWN_MAX_TOKENS
    assert llm.requests[0]["max_tokens"] >= 16_384
    assert llm.requests[0]["timeout_seconds"] == TASK_BREAKDOWN_TIMEOUT_SECONDS


@pytest.mark.asyncio
async def test_task_breakdown_system_prompt_includes_task_slicing_policy_schema():
    llm = FakeSequentialLLM([_breakdown_content("Slice DEMO_TASK_2099 policy")])

    await breakdown_task_source(
        "# DEMO_TASK_2099 policy\n\n- [ ] Slice with proof\n- [ ] Do not split setup prose.",
        job_runner=FakeOrchestratorJobRunner(llm),
        task_breakdown_model="claude-sonnet-4-6",
    )

    system_prompt = llm.requests[0]["messages"][0]["content"]
    assert "Task Slicing Policy:" in system_prompt
    assert "Create the fewest Orchestration Board Tasks" in system_prompt
    assert "Markdown bullets are evidence, not automatic Tasks" in system_prompt
    assert "why_not_smaller" in system_prompt
    assert "why_not_larger" in system_prompt
    assert "execution_mode: AFK or HITL" in system_prompt
    assert "source_text contract-authoritative" in system_prompt


def test_task_breakdown_rejects_execution_mode_human_loop_mismatch():
    with pytest.raises(TaskBreakdownValidationError, match="human_in_loop must match execution_mode"):
        validate_breakdown_result(
            {
                "decision": "single_task",
                "candidates": [
                    {
                        "kind": "implementation",
                        "title": "DEMO_TASK_2099 inconsistent candidate",
                        "objective": "Demonstrate inconsistent execution metadata.",
                        "prompt": "Implement the inconsistent DEMO candidate.",
                        "acceptance_criteria": "Tests pass.",
                        "constraints": [],
                        "proof": "Run pytest.",
                        "why_this_task_exists": "It exercises validation.",
                        "why_not_smaller": "No smaller meaningful slice exists.",
                        "why_not_larger": "No larger task is needed.",
                        "dependencies": [],
                        "likely_entry_points": [],
                        "execution_mode": "AFK",
                        "hitl_reason": "",
                        "human_in_loop": True,
                    }
                ],
                "rejected_items": [],
                "global_contract_summary": "Validation summary.",
                "global_constraints": [],
                "verification": [],
                "non_goals": [],
                "recommended_sequence": ["DEMO_TASK_2099 inconsistent candidate"],
                "confidence": 0.8,
                "rationale": "Invalid execution metadata must fail.",
                "source": "llm",
            }
        )


def test_task_breakdown_rejects_invalid_execution_mode():
    with pytest.raises(TaskBreakdownValidationError, match="execution_mode must be AFK or HITL"):
        validate_breakdown_result(
            {
                "decision": "single_task",
                "candidates": [
                    {
                        "kind": "implementation",
                        "title": "DEMO_TASK_2099 invalid execution mode",
                        "objective": "Demonstrate invalid execution mode metadata.",
                        "prompt": "Implement the invalid DEMO candidate.",
                        "acceptance_criteria": "Tests pass.",
                        "constraints": [],
                        "proof": "Run pytest.",
                        "why_this_task_exists": "It exercises validation.",
                        "why_not_smaller": "No smaller meaningful slice exists.",
                        "why_not_larger": "No larger task is needed.",
                        "dependencies": [],
                        "likely_entry_points": [],
                        "execution_mode": "AUTOPILOT",
                        "hitl_reason": "",
                        "human_in_loop": False,
                    }
                ],
                "rejected_items": [],
                "global_contract_summary": "Validation summary.",
                "global_constraints": [],
                "verification": [],
                "non_goals": [],
                "recommended_sequence": ["DEMO_TASK_2099 invalid execution mode"],
                "confidence": 0.8,
                "rationale": "Invalid execution metadata must fail.",
                "source": "llm",
            }
        )


def test_task_breakdown_rejects_missing_policy_evidence_for_fresh_candidates():
    with pytest.raises(TaskBreakdownValidationError, match="candidate objective is required"):
        validate_breakdown_result(
            {
                "decision": "single_task",
                "candidates": [
                    {
                        "kind": "implementation",
                        "title": "DEMO_TASK_2099 missing policy evidence",
                        "prompt": "Implement the incomplete DEMO candidate.",
                        "acceptance_criteria": "Tests pass.",
                        "constraints": [],
                        "execution_mode": "AFK",
                        "hitl_reason": "",
                        "human_in_loop": False,
                    }
                ],
                "rejected_items": [],
                "global_contract_summary": "Validation summary.",
                "global_constraints": [],
                "verification": [],
                "non_goals": [],
                "recommended_sequence": ["DEMO_TASK_2099 missing policy evidence"],
                "confidence": 0.8,
                "rationale": "Fresh candidates must carry policy evidence.",
                "source": "llm",
            }
        )


def test_task_breakdown_rejects_empty_supplied_policy_evidence():
    with pytest.raises(TaskBreakdownValidationError, match="why_not_smaller must be non-empty"):
        validate_breakdown_result(
            {
                "decision": "single_task",
                "candidates": [
                    {
                        "kind": "implementation",
                        "title": "DEMO_TASK_2099 empty rationale",
                        "objective": "Demonstrate empty policy evidence rejection.",
                        "prompt": "Implement the invalid DEMO candidate.",
                        "acceptance_criteria": "Tests pass.",
                        "constraints": [],
                        "proof": "Run pytest.",
                        "why_this_task_exists": "It exercises validation.",
                        "why_not_smaller": "",
                        "why_not_larger": "No larger task is needed.",
                        "dependencies": [],
                        "likely_entry_points": [],
                        "execution_mode": "AFK",
                        "hitl_reason": "",
                        "human_in_loop": False,
                    }
                ],
                "rejected_items": [],
                "global_contract_summary": "Validation summary.",
                "global_constraints": [],
                "verification": [],
                "non_goals": [],
                "recommended_sequence": ["DEMO_TASK_2099 empty rationale"],
                "confidence": 0.8,
                "rationale": "Empty policy evidence must fail.",
                "source": "llm",
            }
        )


def test_task_breakdown_rejects_afk_candidate_with_hitl_reason():
    content = _breakdown_content("DEMO_TASK_2099 stale HITL reason")
    content["candidates"][0]["hitl_reason"] = "Operator must approve this first."

    with pytest.raises(TaskBreakdownValidationError, match="hitl_reason must be empty for AFK"):
        validate_breakdown_result(content)


@pytest.mark.asyncio
async def test_task_breakdown_preserves_policy_rejections_for_non_task_markdown_bullets():
    content = _breakdown_content("Implement DEMO_VERTICAL_2099 slice")
    content["rejected_items"] = [
        {"text": "Do not add network dependencies.", "reason": "constraint, not a task"},
        {"text": "Run pytest.", "reason": "verification note, not a task"},
        {"text": "Create database layer first.", "reason": "horizontal layer bullet, not an independently verifiable task"},
        {"text": "Prepare for future multi-tenant support.", "reason": "speculative future-proofing, not current task scope"},
    ]
    llm = FakeSequentialLLM([content])

    result, _ = await breakdown_task_source(
        "# DEMO_TASK_2099 slicing\n\n- [ ] Do not add network dependencies.\n- [ ] Run pytest.\n- [ ] Create database layer first.\n- [ ] Prepare for future multi-tenant support.",
        job_runner=FakeOrchestratorJobRunner(llm),
        task_breakdown_model="claude-sonnet-4-6",
    )

    reasons = {item.reason for item in result.rejected_items}
    assert "constraint, not a task" in reasons
    assert "verification note, not a task" in reasons
    assert "horizontal layer bullet, not an independently verifiable task" in reasons
    assert "speculative future-proofing, not current task scope" in reasons


@pytest.mark.asyncio
async def test_task_breakdown_rejects_incomplete_fenced_json_response():
    content = json.dumps(_breakdown_content("Reject DEMO_TASK_2099 truncation"))
    llm = FakeRawContentLLM(f"```json\n{content[:-20]}")

    with pytest.raises(TaskBreakdownValidationError, match="did not call submit_breakdown"):
        await breakdown_task_source(
            "# DEMO_TASK_2099 Claude breakdown\n\n- [ ] Reject truncated JSON",
            job_runner=FakeOrchestratorJobRunner(llm),
            task_breakdown_model="claude-sonnet-4-6",
        )


@pytest.mark.asyncio
async def test_task_breakdown_rejects_prose_wrapped_fenced_json_response():
    content = _breakdown_content("Reject DEMO_TASK_2099 wrapper")
    llm = FakeRawContentLLM(f"Here is the breakdown:\n```json\n{json.dumps(content)}\n```")

    with pytest.raises(TaskBreakdownValidationError, match="did not call submit_breakdown"):
        await breakdown_task_source(
            "# DEMO_TASK_2099 Claude breakdown\n\n- [ ] Reject prose wrapper",
            job_runner=FakeOrchestratorJobRunner(llm),
            task_breakdown_model="claude-sonnet-4-6",
        )


def test_task_breakdown_candidate_kind_defaults_for_legacy_records():
    result = validate_breakdown_result(
        {
            "decision": "single_task",
            "candidates": [
                {
                    "title": "DEMO_TASK_2099 legacy candidate",
                    "prompt": "Implement the legacy DEMO candidate.",
                    "acceptance_criteria": "Tests pass.",
                    "constraints": [],
                    "human_in_loop": True,
                }
            ],
            "rejected_items": [],
            "global_contract_summary": "Legacy breakdown summary.",
            "global_constraints": [],
            "verification": [],
            "non_goals": [],
            "recommended_sequence": ["DEMO_TASK_2099 legacy candidate"],
            "confidence": 0.8,
            "rationale": "Legacy records did not store kind.",
            "source": "llm",
        },
        allow_legacy_candidate_defaults=True,
    )

    assert result.candidates[0].kind == "implementation"
    assert result.candidates[0].objective == "Implement the legacy DEMO candidate."
    assert result.candidates[0].proof == "Tests pass."
    assert result.candidates[0].why_not_smaller == (
        "Smaller substeps would not be independently useful and verifiable."
    )
    assert result.candidates[0].execution_mode == "HITL"
    assert result.candidates[0].hitl_reason == "Requires operator review or judgment before completion."


def test_task_breakdown_rejects_invalid_candidate_kind():
    with pytest.raises(TaskBreakdownValidationError, match="candidate kind"):
        validate_breakdown_result(
            {
                "decision": "single_task",
                "candidates": [
                    {
                        "kind": "whole_task_rerun",
                        "title": "DEMO_TASK_2099 invalid candidate",
                        "prompt": "Do the DEMO task.",
                        "acceptance_criteria": "Tests pass.",
                        "constraints": [],
                        "human_in_loop": True,
                    }
                ],
                "rejected_items": [],
                "global_contract_summary": "Invalid candidate summary.",
                "global_constraints": [],
                "verification": [],
                "non_goals": [],
                "recommended_sequence": ["DEMO_TASK_2099 invalid candidate"],
                "confidence": 0.8,
                "rationale": "Invalid kind must fail.",
                "source": "llm",
            }
        )


# ---------------------------------------------------------------------------
# Estimator failures → Blocked
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_eval_estimator_unavailable_raises_typed_error():
    """LLM call failure raises EstimatorUnavailableError, not a generic exception."""
    config = load_guardrails(ROOT / "guardrails.yaml")
    llm = FakeEstimatorLLM(exc=RuntimeError("connection refused"))

    with pytest.raises(EstimatorUnavailableError, match="connection refused"):
        await estimate_task("Task", config, job_runner=FakeOrchestratorJobRunner(llm), estimator_model="gpt-4o-mini")


@pytest.mark.asyncio
async def test_eval_estimator_invalid_json_raises_validation_error():
    """Non-JSON response raises EstimatorValidationError."""
    config = load_guardrails(ROOT / "guardrails.yaml")
    llm = FakeEstimatorLLM(content="not valid json")  # string, not dict

    with pytest.raises(EstimatorValidationError, match="did not call submit_estimate"):
        await estimate_task("Task", config, job_runner=FakeOrchestratorJobRunner(llm), estimator_model="gpt-4o-mini")


def test_eval_estimator_does_not_swallow_strict_calibration_validation_errors(monkeypatch):
    def fail_selection(**_kwargs):
        raise ValueError("strict DEMO_2099 calibration catalog is invalid")

    monkeypatch.setattr(estimation, "build_calibration_selection", fail_selection)

    with pytest.raises(ValueError, match="strict DEMO_2099 calibration catalog is invalid"):
        estimation._build_calibration_context(
            "Add DEMO_TASK_2099 estimator coverage",
            project_root=None,
            project_profile=None,
        )


# ---------------------------------------------------------------------------
# Markdown task intake / decomposition behavior
# ---------------------------------------------------------------------------


class EstimatorMarkdownFakeDataInvariantTests:
    """Markdown estimator fixtures must stay obviously synthetic."""

    __test__ = True

    def test_markdown_eval_fixture_values_are_demo_synthetic(self) -> None:
        text = "\n".join(MARKDOWN_EVAL_FIXTURES.values())
        assert "DEMO" in text
        assert "2099" in text
        real_years = re.findall(r"\b20(?:2[0-8])\b", text)
        assert real_years == []
        suspicious_values = [
            value for value in re.findall(r"\b[A-Z][A-Za-z0-9_-]*_\d{4}[A-Za-z0-9_-]*\b", text) if "DEMO" not in value
        ]
        assert suspicious_values == []
