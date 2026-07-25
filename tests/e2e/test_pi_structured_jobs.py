"""Structured jobs against a real pi: prove the tracked submit extensions load and run.

Every other structured-job test stubs ``create_subprocess_exec``, so pi never executes
the tracked ``.ts`` extensions.  A bad import or tool definition in ``submit-estimate.ts``
/ ``submit-breakdown.ts`` would break estimation and task breakdown in production with
the rest of the suite green.  These tests are the only thing that runs them.
"""

from __future__ import annotations

import shutil

import pytest

from foreman_ai_hq import db
from foreman_ai_hq.pi_adapter import PiAuthRequired, run_pi_structured_job
from foreman_ai_hq.task_breakdown import validate_breakdown_result

# Generous relative to the ~20s these jobs take, so a slow provider fails loudly as a
# timeout with its diagnostics rather than hanging the suite.
JOB_TIMEOUT = 240


def _skip_without_pi() -> None:
    if not shutil.which("pi"):
        pytest.skip("pi CLI not installed")


@pytest.mark.asyncio
async def test_real_estimation_job_submits_drivers_and_records_native_usage(tmp_path) -> None:
    _skip_without_pi()

    database_path = tmp_path / "harness.db"
    db.init_db(database_path)

    try:
        job = await run_pi_structured_job(
            database_path,
            instructions="Estimate the structural drivers for this task. Do not read the repository.",
            input_payload={"description": "Add a one-line comment to README.md"},
            model="openai-codex/gpt-5.4",
            persona_filename="estimator.md",
            extension_filename="submit-estimate.ts",
            submit_tool="submit_estimate",
            usage_kind="estimation",
            task_description="e2e estimation",
            timeout=JOB_TIMEOUT,
        )
    except PiAuthRequired:
        pytest.skip("pi provider authentication not configured")

    drivers = job.arguments["drivers"]
    assert set(drivers) == {"files_to_read", "files_to_modify", "expected_turns", "needs_test_run"}
    assert isinstance(job.arguments["confidence"], (int, float))
    assert isinstance(job.arguments["investigation_recommended"], bool)
    # The drivers are the contract; a raw product magnitude must not come back.
    assert "token_estimate" not in job.arguments

    assert job.session["status"] == "completed"
    token_log = db.build_session_artifact(database_path, job.session["id"])["token_log"]
    assert len(token_log) == 1
    assert token_log[0]["usage_kind"] == "estimation"
    assert token_log[0]["raw_usage"]["usage_source"] == "native_usage"


@pytest.mark.asyncio
async def test_real_breakdown_job_submits_the_review_contract(tmp_path) -> None:
    _skip_without_pi()

    database_path = tmp_path / "harness.db"
    db.init_db(database_path)

    try:
        job = await run_pi_structured_job(
            database_path,
            instructions="Break this down into the fewest independently executable slices.",
            input_payload={"source_text": "Add a health endpoint and a test for it."},
            model="openai-codex/gpt-5.4",
            persona_filename="task_breakdown.md",
            extension_filename="submit-breakdown.ts",
            submit_tool="submit_breakdown",
            usage_kind="task_breakdown",
            task_description="e2e breakdown",
            timeout=JOB_TIMEOUT,
            # Task Breakdown Review's own validator: the submitted arguments must satisfy
            # the downstream contract, not merely the tool schema.
            result_validator=validate_breakdown_result,
        )
    except PiAuthRequired:
        pytest.skip("pi provider authentication not configured")

    assert job.arguments["decision"] in {"single_task", "proposed_task_breakdown"}
    assert job.validated.candidates

    assert job.session["status"] == "completed"
    token_log = db.build_session_artifact(database_path, job.session["id"])["token_log"]
    assert len(token_log) == 1
    assert token_log[0]["usage_kind"] == "task_breakdown"
    assert token_log[0]["raw_usage"]["usage_source"] == "native_usage"
