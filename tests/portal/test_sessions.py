import json
import time
from pathlib import Path

import pytest

from foreman_ai_hq import db
from foreman_ai_hq.project_context import project_task_metadata
from foreman_ai_hq.routes import react_shell
from foreman_ai_hq.task_kind import with_task_kind
from foreman_ai_hq.task_launch import launch_task
from tests.conftest import git_project_profile
from tests.portal.helpers import PORTAL_TOKEN, _client, _portal_headers, _project_metadata


@pytest.fixture(autouse=True)
def _missing_react_build(tmp_path, monkeypatch):
    build_dir = tmp_path / "missing-react-build"
    build_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(react_shell, "react_build_dir", lambda: build_dir)


def test_sessions_index_renders_mockup_style_session_table(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Review live portal", "model": "claude-haiku"},
        ).json()
        db.record_token_turn(
            tmp_path / "harness.db",
            session_id=started["session_id"],
            model="claude-haiku",
            prompt_tokens=80,
            completion_tokens=20,
            cost=0.01,
            raw_usage={"total_tokens": 100},
        )
        # /sessions is now the React shell (or the missing-build recovery page); the
        # row data it renders comes from the JSON handoff, so assert against that
        # directly instead of the retired Jinja markup.
        response = client.get("/api/sessions", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    rows = {row["id"]: row for row in payload["sessions"]}
    row = rows[started["session_id"]]
    # "All sessions" (page heading), "summary before raw report" (an ordering
    # hint), and "table-wrap" (a CSS class) were pure Jinja-mockup presentation
    # with no backend data behind them; the React Sessions view owns that layout.
    assert row["task_preview"] == "Review live portal"
    assert row["token_totals"]["total_tokens"] == 100
    assert row["evidence_counts"]["worker_runs"] == 0
    assert row["evidence_counts"]["worker_events"] == 0
    # "zone:" was just a label prefix; the zone value itself is backend state.
    assert row["current_zone"] == "green"


def test_sessions_index_compacts_long_task_text_preserves_scan_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    long_task = "Review compact sessions " + ("visible summary " * 20) + "FULL_TASK_TAIL_2099"
    with _client(tmp_path) as client:
        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": long_task, "model": "claude-haiku"},
        ).json()
        db.record_token_turn(
            tmp_path / "harness.db",
            session_id=started["session_id"],
            model="claude-haiku",
            prompt_tokens=1234,
            completion_tokens=56,
            cost=0.01,
            raw_usage={"total_tokens": 1290},
        )

        index = client.get("/api/sessions", headers=_portal_headers())
        report = client.get(f"/api/sessions/{started['session_id']}/report", headers=_portal_headers())

    assert index.status_code == 200
    index_payload = index.json()
    rows = {row["id"]: row for row in index_payload["sessions"]}
    row = rows[started["session_id"]]
    # The index row's task_preview is bounded to 240 chars by the handoff itself
    # (session_handoff.sessions_projection), so the tail is genuinely dropped here
    # -- that's backend truncation, not a CSS "compact-text lines-2" clamp (which
    # was purely presentational and is dropped with this migration).
    assert row["task_preview"].startswith("Review compact sessions")
    assert "FULL_TASK_TAIL_2099" not in row["task_preview"]
    assert row["report_href"] == f"/sessions/{started['session_id']}"
    assert row["model"] == "claude-haiku"
    assert row["token_totals"]["prompt_tokens"] == 1234
    assert row["token_totals"]["completion_tokens"] == 56
    assert row["token_totals"]["total_tokens"] == 1290
    assert row["evidence_counts"]["worker_runs"] == 0
    assert row["evidence_counts"]["worker_events"] == 0
    assert row["current_zone"] == "green"
    assert report.status_code == 200
    report_payload = report.json()
    # The full report bounds the task at 20,000 chars, so this short task is
    # returned in full -- the tail that the index compacted away is preserved here.
    assert report_payload["session"]["task"]["preview"].endswith("FULL_TASK_TAIL_2099")
    assert report_payload["session"]["task"]["truncated"] is False


def test_sessions_index_and_report_label_agent_review_accounting(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    db.init_db(tmp_path / "harness.db")
    review_session = db.create_session(
        tmp_path / "harness.db",
        task_description="Agent review for task DEMO_TASK_999",
        model="anthropic/claude-sonnet-4-20250514",
        session_key_hash="a" * 64,
        guardrail_overrides={"spend_category": "agent_review", "task_id": "DEMO_TASK_999"},
        status="completed",
    )
    db.record_token_turn(
        tmp_path / "harness.db",
        session_id=review_session["id"],
        usage_kind="reporting",
        model="anthropic/claude-sonnet-4-20250514",
        prompt_tokens=70,
        completion_tokens=30,
        cost=0.01,
        raw_usage={
            "total_tokens": 100,
            "spend_category": "agent_review",
            "response": {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary": "DEMO review summary 2099.",
                                    "recommendation": "approve",
                                    "findings": [],
                                }
                            )
                        }
                    }
                ]
            },
        },
    )

    with _client(tmp_path) as client:
        index = client.get("/api/sessions", headers=_portal_headers())
        report = client.get(f"/api/sessions/{review_session['id']}/report", headers=_portal_headers())

    assert index.status_code == 200
    index_rows = {row["id"]: row for row in index.json()["sessions"]}
    index_row = index_rows[review_session["id"]]
    assert index_row["kind"] == "Agent Review"
    assert index_row["token_totals"]["total_tokens"] == 100
    assert index_row["evidence_counts"]["worker_runs"] == 0
    assert report.status_code == 200
    report_payload = report.json()
    assert report_payload["session"]["kind"] == "Agent Review"
    # "Review source" was just the Summary label used for Agent Review sessions
    # (SessionReport.jsx); the data behind it is adapter_id/tracking_mode below.
    assert report_payload["summary"]["adapter_id"] == "Control Plane"
    assert report_payload["summary"]["tracking_mode"] == "reporting_summary"
    assert report_payload["summary"]["result"]["preview"] == "approve · DEMO review summary 2099."
    assert report_payload["summary"]["selected_project"]["preview"] == "Agent Review for task DEMO_TASK_999"
    assert "missing Worker Run evidence" not in report_payload["summary"]["missing_labels"]
    breakdown = db.session_token_breakdown(tmp_path / "harness.db", review_session["id"])
    assert breakdown["by_category"]["reporting_summary"] == 100
    assert breakdown["by_source"]["control_plane"] == 100


def test_worker_session_report_shows_related_agent_review_results_and_tokens(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    worker_session = db.create_session(
        database_path,
        task_description="DEMO reviewed worker session 2099",
        model="opencode/gpt-5.5",
        session_key_hash="w" * 64,
        guardrail_overrides={},
        status="completed",
    )
    review_session = db.create_session(
        database_path,
        task_description="Agent review for DEMO_TASK_999",
        model="anthropic/claude-sonnet-4-20250514",
        session_key_hash="r" * 64,
        guardrail_overrides={"spend_category": "agent_review", "task_id": "DEMO_TASK_999"},
        status="completed",
    )
    db.record_token_turn(
        database_path,
        session_id=worker_session["id"],
        model="opencode/gpt-5.5",
        prompt_tokens=300,
        completion_tokens=200,
        cost=0.02,
        raw_usage={"total_tokens": 500, "spend_category": "worker_execution", "usage_source": "harness_proxy"},
    )
    db.record_token_turn(
        database_path,
        session_id=review_session["id"],
        usage_kind="reporting",
        model="anthropic/claude-sonnet-4-20250514",
        prompt_tokens=40,
        completion_tokens=9,
        cost=0.01,
        raw_usage={"total_tokens": 49, "spend_category": "reporting_summary", "usage_source": "control_plane", "reporting_kind": "agent_review"},
    )
    task = db.create_task(
        database_path,
        description="DEMO reviewed worker session 2099",
        status="Review",
        actual_tokens=500,
        session_id=worker_session["id"],
        metadata={
            "agent_review": {
                "status": "completed",
                "summary": "DEMO Agent Review summary 2099",
                "recommendation": "approve",
                "findings": [{"severity": "low", "message": "DEMO finding 2099"}],
                "reviewed_at": "2099-01-02T03:04:05+00:00",
                "review_session_id": review_session["id"],
                "model": "anthropic/claude-sonnet-4-20250514",
                "token_totals": {"prompt_tokens": 40, "completion_tokens": 9, "total_tokens": 49},
            }
        },
    )

    with _client(tmp_path) as client:
        response = client.get(f"/api/sessions/{worker_session['id']}/report", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    review = payload["related_agent_review"]
    assert review is not None  # presence of this block *is* "Agent Review results"
    # "completed · approve" was the joined display string; status and
    # recommendation are the backend fields behind it.
    assert review["status"] == "completed"
    assert review["recommendation"] == "approve"
    assert review["summary"]["preview"] == "DEMO Agent Review summary 2099"
    finding_previews = [item["preview"] for item in review["findings"]["items"]]
    assert any("DEMO finding 2099" in preview for preview in finding_previews)
    assert review["reviewed_at"] == "2099-01-02T03:04:05+00:00"
    assert review["model"] == "anthropic/claude-sonnet-4-20250514"
    assert review["review_total_tokens"] == 49
    assert review["review_session_href"] == f'/sessions/{review_session["id"]}'
    assert payload["tokens"]["provider_totals"]["total_tokens"] == 500
    worker_breakdown = db.session_token_breakdown(database_path, worker_session["id"])
    assert worker_breakdown["by_category"]["worker_execution"] == 500
    assert worker_breakdown["by_category"]["reporting_summary"] == 0
    assert db.get_task(database_path, task["id"])["actual_tokens"] == 500


def test_worker_session_report_shows_failed_agent_review_without_fabricated_zero_tokens(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    worker_session = db.create_session(
        database_path,
        task_description="DEMO failed review worker session 2099",
        model="opencode/gpt-5.5",
        session_key_hash="w" * 64,
        guardrail_overrides={},
        status="completed",
    )
    review_session = db.create_session(
        database_path,
        task_description="Failed Agent review for DEMO_TASK_999",
        model="anthropic/claude-sonnet-4-20250514",
        session_key_hash="r" * 64,
        guardrail_overrides={"spend_category": "agent_review", "task_id": "DEMO_TASK_999"},
        status="failed",
    )
    db.create_task(
        database_path,
        description="DEMO failed review worker session 2099",
        status="Review",
        actual_tokens=500,
        session_id=worker_session["id"],
        metadata={
            "agent_review": {
                "status": "failed",
                "summary": "Agent Review failed; operator can still mark done or block manually.",
                "recommendation": "needs_changes",
                "findings": [],
                "reviewed_at": "2099-01-02T03:04:05+00:00",
                "review_session_id": review_session["id"],
                "model": "anthropic/claude-sonnet-4-20250514",
                "token_totals": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "error": "DEMO provider timeout 2099",
            }
        },
    )

    with _client(tmp_path) as client:
        response = client.get(f"/api/sessions/{worker_session['id']}/report", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    review = payload["related_agent_review"]
    assert review is not None
    # "failed · needs_changes" was the joined display string; status and
    # recommendation are the backend fields behind it.
    assert review["status"] == "failed"
    assert review["recommendation"] == "needs_changes"
    assert review["summary"]["preview"] == "Agent Review failed; operator can still mark done or block manually."
    assert review["error"]["preview"] == "DEMO provider timeout 2099"
    assert review["reviewed_at"] == "2099-01-02T03:04:05+00:00"
    # "review tokens unavailable" is the client's label for a null value here --
    # the review's own token_totals are all zero, but no token_turn was ever
    # recorded for the review session, so review_total_tokens stays None rather
    # than fabricating a "0 review/control-plane tokens" total.
    assert review["review_total_tokens"] is None


def test_session_report_renders_totals_alarm_checkpoint_without_internal_artifact_link(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": "Audit session", "model": "claude-haiku"},
        ).json()
        session_id = started["session_id"]
        db.record_token_turn(
            tmp_path / "harness.db",
            session_id=session_id,
            model="claude-haiku",
            prompt_tokens=300,
            completion_tokens=200,
            cost=0.02,
            raw_usage={"total_tokens": 500},
        )
        db.record_guardrail_snapshot(
            tmp_path / "harness.db",
            session_id=session_id,
            zone="yellow",
            decision={"blocked_tools": ["web_search"], "max_tokens": 2048},
        )
        db.record_alarm(
            tmp_path / "harness.db",
            session_id=session_id,
            alarm={
                "id": "alarm-report-1",
                "type": "CHECKPOINT_FAIL",
                "severity": "MEDIUM",
                "context": {"checkpoint_name": "budget_health"},
                "recommended_action": "Human review required.",
            },
        )
        db.record_checkpoint_result(
            tmp_path / "harness.db",
            session_id=session_id,
            checkpoint={"name": "budget_health", "passed": False, "details": {"reason": "over budget"}},
        )
        task = db.create_task(
            tmp_path / "harness.db",
            description="Audit session",
            status="Running",
            session_id=session_id,
        )
        worker_run = db.create_worker_run(
            tmp_path / "harness.db",
            task_id=task["id"],
            session_id=session_id,
            adapter_id="opencode",
            model="claude-haiku",
            tracking_mode="proxy_governed",
            command_plan={"command": ["opencode"], "env": {}, "metadata": {}},
            metadata={
                "repo_context_brief": {
                    "documents": [{"path": "AGENTS.md", "excerpt": "Use pytest."}],
                    "manifests": ["pyproject.toml"],
                    "text": "Project root: /tmp/demo\n\nRepo instructions/docs:\n- AGENTS.md:\nUse pytest.",
                }
            },
        )
        db.record_worker_run_event(
            tmp_path / "harness.db",
            worker_run_id=worker_run["id"],
            session_id=session_id,
            task_id=task["id"],
            kind="guardrail",
            title="Worker Run failed",
            level="error",
            detail={
                "api_key": "***",
                "documents": ["AGENTS.md"],
                "error_type": "workdir_mismatch",
                "returncode": 124,
                "retryable": True,
            },
        )

        response = client.get(f"/api/sessions/{session_id}/report", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["task"]["preview"] == "Audit session"
    # The projected session object never carries the internal-only fields.
    assert set(payload["session"]) == {"id", "kind", "task", "model", "status", "started_at", "active"}
    assert payload["tokens"]["provider_totals"]["total_tokens"] == 500
    assert any(item["zone"] == "yellow" for item in payload["zone_timeline"]["items"])
    assert payload["alarms"]["items"][0]["type"] == "CHECKPOINT_FAIL"
    assert payload["checkpoints"]["items"][0]["name"] == "budget_health"
    assert payload["checkpoints"]["items"][0]["passed"] is False
    # "Requires review" (a pill) and "review needed" (inline text) were two Jinja
    # labels for the same boolean; the React view keeps only the inline text, so
    # one backend assertion now covers both retired labels.
    assert payload["summary"]["requires_review"] is True
    # "Status / result", "Worker launch", "Usage / guardrails", and "Evidence
    # coverage" were section headings with no data of their own -- dropped.
    assert payload["summary"]["adapter_id"] == "opencode"
    assert payload["summary"]["tracking_mode"] == "proxy_governed"
    # The Jinja "target: " prefix is retired; the launch-target value is backend state.
    assert payload["summary"]["launch_target"]["preview"] == "opencode"
    assert payload["summary"]["evidence_counts"]["worker_runs"] == 1
    assert payload["summary"]["evidence_counts"]["worker_events"] == 1
    assert payload["summary"]["evidence_counts"]["error_events"] == 1
    assert payload["summary"]["selected_project"]["preview"] == "missing project evidence"
    # "Worker Run timeline" (heading) and "raw timeline evidence" /
    # "raw prompt context evidence" (static <summary> labels next to those
    # sections) carried no data of their own in the deleted Jinja template and
    # have no equivalent literal in SessionReport.jsx -- retired, dropped.
    worker_event = payload["worker_timeline"]["items"][0]
    assert worker_event["title"] == "Worker Run failed"
    assert "error_type=workdir_mismatch" in worker_event["detail_summary"]
    assert "returncode=124" in worker_event["detail_summary"]
    assert "retryable=True" in worker_event["detail_summary"]
    assert "control_plane" in payload["tokens"]["normalized"]["by_category"]
    repo_brief = payload["repo_context_briefs"]["items"][0]
    assert repo_brief["documents"]["items"][0]["path"] == "AGENTS.md"
    assert repo_brief["manifests"]["items"][0] == "pyproject.toml"
    # No related Agent Review for this plain Worker session.
    assert payload["related_agent_review"] is None
    serialized = json.dumps(payload)
    assert "/artifact" not in serialized
    assert "session_key_hash" not in serialized
    assert "guardrail_overrides" not in serialized
    assert "api_key" not in serialized
    assert "***" not in serialized


def test_session_report_compacts_summary_but_preserves_full_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    long_task = "Compact report task " + ("summary text " * 24) + "REPORT_TASK_TAIL_2099"
    long_command_tail = "LAUNCH_TARGET_TAIL_2099"
    long_detail_tail = "TIMELINE_DETAIL_TAIL_2099"
    long_result_tail = "ERROR_RESULT_TAIL_2099"
    repo_tail = "REPO_CONTEXT_TAIL_2099"

    with _client(tmp_path) as client:
        started = client.post(
            "/session/start",
            headers={"Authorization": "Bearer test-portal-token"},
            json={"task_description": long_task, "model": "claude-haiku"},
        ).json()
        session_id = started["session_id"]
        db.record_token_turn(
            tmp_path / "harness.db",
            session_id=session_id,
            model="claude-haiku",
            prompt_tokens=50,
            completion_tokens=10,
            cost=0.01,
            raw_usage={"total_tokens": 60},
        )
        task = db.create_task(
            tmp_path / "harness.db",
            description=long_task,
            status="Running",
            session_id=session_id,
            metadata=_project_metadata(tmp_path / "harness.db", tmp_path / "compact-report-project"),
        )
        worker_run = db.create_worker_run(
            tmp_path / "harness.db",
            task_id=task["id"],
            session_id=session_id,
            adapter_id="opencode",
            model="claude-haiku",
            tracking_mode="native_usage",
            command_plan={
                "command": ["opencode", "run", "--dir", str(tmp_path / "compact-report-project"), "x" * 240, long_command_tail],
                "env": {},
                "metadata": {},
            },
            metadata={
                "connected_project_name": "compact-report-project",
                "repo_context_brief": {
                    "documents": [{"path": "AGENTS.md", "excerpt": "Use pytest."}],
                    "manifests": ["pyproject.toml"],
                    "text": "Repo context\n" + ("bounded raw text\n" * 30) + repo_tail,
                },
            },
        )
        db.mark_worker_run_failed(
            tmp_path / "harness.db",
            worker_run["id"],
            error_type="demo_failure",
            error_message=long_result_tail + (" actionable failure detail" * 40),
            returncode=2,
        )
        db.record_worker_run_event(
            tmp_path / "harness.db",
            worker_run_id=worker_run["id"],
            session_id=session_id,
            task_id=task["id"],
            kind="adapter_complete",
            title="Worker Run completed with detailed evidence",
            level="info",
            detail={"custom_payload": ("timeline payload " * 30) + long_detail_tail},
        )

        response = client.get(f"/api/sessions/{session_id}/report", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    # "compact-text lines-2/3" were CSS line-clamp classes -- the Jinja page
    # relied on the browser to visually clip already-bounded preview text; the
    # React BoundedText component does the same with no equivalent class name.
    # "Full task and launch evidence" / "Full launch target" / "Full status/
    # result" / "Timeline detail" were <details><summary> toggle labels for
    # revealing the same data; React's BoundedText exposes truncated/full_href
    # instead, so the underlying data is asserted below rather than the labels.
    # "raw-evidence" was a CSS hook with no data of its own. "Repo Context
    # Brief" is a bare heading. All dropped as pure presentation.
    task = payload["session"]["task"]
    assert task["preview"].endswith("REPORT_TASK_TAIL_2099")
    assert task["truncated"] is False
    launch_target = payload["summary"]["launch_target"]
    assert long_command_tail in launch_target["preview"]
    assert launch_target["truncated"] is False
    result = payload["summary"]["result"]
    assert long_result_tail in result["preview"]
    assert result["truncated"] is False
    worker_event = payload["worker_timeline"]["items"][0]
    assert "custom_payload" in worker_event["detail"]["preview"]
    assert long_detail_tail in worker_event["detail"]["preview"]
    assert worker_event["detail"]["truncated"] is False
    repo_brief = payload["repo_context_briefs"]["items"][0]
    assert repo_tail in repo_brief["text"]["preview"]
    assert repo_brief["text"]["truncated"] is False
    assert payload["summary"]["adapter_id"] == "opencode"
    assert payload["summary"]["tracking_mode"] == "native_usage"
    assert payload["summary"]["selected_project"]["preview"] == "compact-report-project"


def test_session_report_missing_session_returns_404(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/sessions/missing", headers=_portal_headers())

    assert response.status_code == 404


def _make_runner(database_path: Path):
    def runner(plan):
        db.record_token_turn(
            database_path,
            session_id=plan.metadata["session_id"],
            usage_kind="task_execution",
            model="opencode/gpt-5.1",
            prompt_tokens=10,
            completion_tokens=5,
            cost=0,
            raw_usage={"total_tokens": 15},
        )
        return {"returncode": 0, "stdout": "done", "stderr": ""}

    return runner


def _wait_for_worker_run_status(database_path: Path, task_id: str, status: str):
    deadline = time.time() + 5
    while time.time() < deadline:
        runs = db.list_worker_runs(database_path, task_id=task_id)
        if runs and runs[-1]["status"] == status:
            return runs[-1]
        time.sleep(0.01)
    raise AssertionError(f"worker run did not reach status {status}")


def _launchable_read_only_task(database_path: Path, project_root: Path):
    profile = git_project_profile(project_root)
    project = db.upsert_connected_project(
        database_path,
        name="Session Checkpoint Project",
        root_path=str(project_root.resolve()),
        profile=profile,
        capability={"state": "launch_ready", "can_launch": True},
    )
    db.update_worker_adapter(
        database_path,
        "opencode",
        workdir=str(project_root),
        config={"launch_template": ["python", "-c", "print('worker')"]},
        supported_models=["opencode/gpt-5.1"],
        is_default=True,
    )
    db.mark_worker_adapter_verification(database_path, "opencode", verified=True, evidence={"ok": True})
    return db.create_task(
        database_path,
        description="Session checkpoint test",
        status="Ready",
        estimate_tokens=1000,
        recommended_model="opencode/gpt-5.1",
        metadata=with_task_kind({**project_task_metadata(project)}, "acceptance_verification"),
    )


def test_manual_checkpoint_evaluate_replaces_results_after_guardrail_change(tmp_path, monkeypatch):
    """2.3 The manual endpoint re-evaluates and overwrites results after guardrail config changes."""
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    project_root = tmp_path / "checkpoint-project"
    with _client(tmp_path) as client:
        database_path = client.app.state.settings.database_path
        task = _launchable_read_only_task(database_path, project_root)
        launch_task(
            database_path,
            task["id"],
            adapter_id="opencode",
            model=None,
            proxy_url=None,
            runner=_make_runner(database_path),
            guardrail_config=client.app.state.guardrails,
        )
        worker_run = _wait_for_worker_run_status(database_path, task["id"], "completed")
        session_id = worker_run["session_id"]

        first = client.post(f"/session/{session_id}/checkpoint/evaluate", headers=_portal_headers()).json()
        assert first["checkpoint_results"]
        first_budget = next(result for result in first["checkpoint_results"] if result["name"] == "budget_health")
        assert first_budget["passed"] is True

        # Re-evaluate with a much lower session cap so the same token spend fails budget health.
        from dataclasses import replace

        strict_config = replace(
            client.app.state.guardrails,
            session_cap=replace(client.app.state.guardrails.session_cap, tokens=10),
        )
        client.app.state.guardrails = strict_config

        second = client.post(f"/session/{session_id}/checkpoint/evaluate", headers=_portal_headers()).json()
        assert second["session_id"] == session_id
        second_budget = next(result for result in second["checkpoint_results"] if result["name"] == "budget_health")
        assert second_budget["passed"] is False
        assert second_budget["details"]["session_cap_tokens"] == 10

        artifact = db.build_session_artifact(database_path, session_id)
        budget_results = [result for result in artifact["checkpoint_results"] if result["name"] == "budget_health"]
        assert len(budget_results) == 1


def test_session_report_renders_checkpoints_for_ordinary_completed_run(tmp_path, monkeypatch):
    """2.4 The Session Report Checkpoints section renders for an ordinary completed run."""
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    project_root = tmp_path / "checkpoint-project"
    with _client(tmp_path) as client:
        database_path = client.app.state.settings.database_path
        task = _launchable_read_only_task(database_path, project_root)
        launch_task(
            database_path,
            task["id"],
            adapter_id="opencode",
            model=None,
            proxy_url=None,
            runner=_make_runner(database_path),
            guardrail_config=client.app.state.guardrails,
        )
        worker_run = _wait_for_worker_run_status(database_path, task["id"], "completed")
        session_id = worker_run["session_id"]

        response = client.get(f"/api/sessions/{session_id}/report", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["checkpoints"]["items"]
    assert {item["name"] for item in payload["checkpoints"]["items"]} == {
        "budget_health",
        "stuck_loop_score",
        "tool_diversity",
        "timeout_respect",
    }
