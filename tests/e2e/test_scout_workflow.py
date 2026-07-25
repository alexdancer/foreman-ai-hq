from __future__ import annotations

import json
import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from foreman_ai_hq import db

from tests.e2e.recorded_demo import DEMO_MODEL, DEMO_SESSION_ID, DEMO_SENTINEL, RecordedDemo
from tests.fake_orchestrator import FakeOrchestratorJobRunner


SCOUT_PARENT_TASK_ID = "DEMO_999_SCOUT_PARENT"


class _FakeScoutEstimatorLLM:
    """Return deterministic estimator output; zero file modifications for Scouts."""

    def __init__(self):
        self.requests: list[dict] = []

    async def acompletion(self, request: dict) -> dict:
        self.requests.append(request)
        payload = json.loads(request["messages"][1]["content"])
        task_kind = payload.get("task_kind", "implementation")
        files_to_modify = 0 if task_kind == "scout" else 1
        result = {
            "drivers": {
                "files_to_read": 2,
                "files_to_modify": files_to_modify,
                "expected_turns": 3,
                "needs_test_run": False,
            },
            "shadow_token_estimate": 11000,
            "complexity": "modest",
            "confidence": 0.82,
            "investigation_recommended": False,
            "rationale": "Synthetic estimate from Scout findings.",
            "assumptions": ["Synthetic fixture assumption."],
            "risk_flags": [],
            "budget_note": "Within synthetic budget.",
            "source": "llm",
        }
        return {
            "choices": [{"message": {"content": json.dumps(result)}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
        }


class _ScoutWorkflowDemo(RecordedDemo):
    """RecordedDemo variant that seeds a low-confidence implementation task and a Codex adapter."""

    def _seed_data(self) -> None:
        import foreman_ai_hq.db as db
        import foreman_ai_hq.execution_backend as execution_backend
        from foreman_ai_hq.project_context import project_task_metadata

        db.init_db(self.database_path)

        adapter = db.get_worker_adapter(self.database_path, "codex")
        config = dict(adapter.get("config") or {})
        config["allowed_models_configured"] = True
        db.update_worker_adapter(
            self.database_path,
            "codex",
            config=config,
            supported_models=[DEMO_MODEL],
            is_default=True,
        )
        db.mark_worker_adapter_verification(
            self.database_path,
            "codex",
            verified=True,
            evidence={
                "tracking_mode": "native_usage",
                "tracking_authoritative": True,
                "synthetic_fixture": True,
            },
        )

        profile = execution_backend.detect_project_profile(self._project_root)
        project = db.upsert_connected_project(
            self.database_path,
            name="DEMO_999_scout_project",
            root_path=str(self._project_root),
            profile=profile,
            capability={
                "state": "launch_ready",
                "label": "Launch-ready via Local Runner",
                "backend": "local_runner",
                "reasons": [],
                "can_launch": True,
                "can_analyze": True,
            },
            backend_id="local_runner",
        )
        self.project_id = project["id"]

        db.set_token_budget_settings(
            self.database_path,
            daily_cap_tokens=100_000,
            session_cap_tokens=50_000,
        )

        task_description = "DEMO 999 low-confidence implementation fixture"
        assert DEMO_SENTINEL not in task_description
        task = db.create_task(
            self.database_path,
            task_id=SCOUT_PARENT_TASK_ID,
            description=task_description,
            status="Estimated",
            estimate_tokens=1500,
            recommended_model=DEMO_MODEL,
            metadata={
                "task_kind": "implementation",
                "confidence": 0.5,
                "estimation_source": "llm",
                "estimate_revision": 1,
                "synthetic_fixture": True,
                **project_task_metadata(project),
            },
        )
        self.task_id = task["id"]

    def _seed_llm_client(self, app) -> None:
        llm = _FakeScoutEstimatorLLM()
        app.state.llm_client = llm
        app.state.orchestrator_job_runner = FakeOrchestratorJobRunner(llm)


def _parse_action(action: dict) -> tuple[str, dict[str, str]]:
    parsed = urlparse(action["href"])
    return parsed.path, {k: v[0] for k, v in parse_qs(parsed.query).items()}


def _wait_for_outcome(demo: _ScoutWorkflowDemo, timeout: float = 30) -> None:
    assert demo.outcome_done.wait(timeout=timeout), "scout worker run outcome was not applied"


def test_scout_workflow_service() -> None:
    with _ScoutWorkflowDemo() as demo:
        headers = {"Authorization": f"Bearer {demo.portal_token}"}
        base = demo.base_url

        # 1. Parent task is low-confidence and needs a decision.
        needs = httpx.get(f"{base}/api/projects/{demo.project_id}/needs-you", headers=headers).json()
        assert needs["count"] == 1
        item = needs["items"][0]
        assert item["kind"] == "low_confidence_estimate"
        assert item["decision_state"] == "decision_required"
        create_action = next(a for a in item["actions"] if a["kind"] == "create_scout")
        create_path, create_qs = _parse_action(create_action)
        estimate_revision = int(create_qs["estimate_revision"])

        # 2. Create a linked Scout for the current estimate revision.
        response = httpx.post(f"{base}{create_path}", headers=headers, json={})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["decision_state"] == "scout_pending"
        scout_id = body["scout_task_id"]

        scout = db.get_task(demo.database_path, scout_id)
        assert scout["status"] == "Estimated"
        assert scout["metadata"]["task_kind"] == "scout"
        assert scout["metadata"]["scout_for_task_id"] == demo.task_id
        assert scout["metadata"]["scout_for_estimate_revision"] == estimate_revision

        # 3. Launch the Scout with the verified Codex read-only profile.
        demo.stream_more.set()
        demo.release.set()
        launch = httpx.post(
            f"{base}/tasks/{scout_id}/launch",
            headers={**headers, "Content-Type": "application/json"},
            json={"adapter_id": "codex", "model": DEMO_MODEL},
        )
        assert launch.status_code == 200, launch.text
        launch_body = launch.json()
        assert launch_body["task"]["status"] == "Running"

        _wait_for_outcome(demo)

        # 4. Scout completed read-only; command plan proves enforced sandbox.
        scout = db.get_task(demo.database_path, scout_id)
        assert scout["status"] == "Review"
        assert scout["actual_tokens"] == 15
        command_plan = scout["metadata"]["launch_command_plan"]
        assert command_plan["metadata"]["read_only"] is True
        assert "--sandbox" in command_plan["command"]
        assert "read-only" in command_plan["command"]
        assert "workspace-write" not in command_plan["command"]
        assert "task_branch" not in scout["metadata"]

        # 5. Needs You reflects completed findings.
        needs = httpx.get(f"{base}/api/projects/{demo.project_id}/needs-you", headers=headers).json()
        item = next(i for i in needs["items"] if i["task_id"] == demo.task_id)
        assert item["decision_state"] == "findings_ready"
        request_action = next(a for a in item["actions"] if a["kind"] == "request_reestimate")

        # 6. Mark the Scout Done (synthetic Session Report is now authoritative).
        review = httpx.post(
            f"{base}/tasks/{scout_id}/review",
            headers={**headers, "Content-Type": "application/json"},
            json={"action": "mark_done", "project_id": demo.project_id},
        )
        assert review.status_code == 200, review.text
        scout = db.get_task(demo.database_path, scout_id)
        assert scout["status"] == "Done"

        # 7. Request a re-estimate from the Scout findings.
        request_path, request_qs = _parse_action(request_action)
        response = httpx.post(
            f"{base}{request_path}",
            headers=headers,
            json={},
            params=request_qs,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["decision_state"] == "reestimate_ready"

        needs = httpx.get(f"{base}/api/projects/{demo.project_id}/needs-you", headers=headers).json()
        item = next(i for i in needs["items"] if i["task_id"] == demo.task_id)
        assert item["decision_state"] == "reestimate_ready"
        apply_action = next(a for a in item["actions"] if a["kind"] == "apply_reestimate")
        apply_path, apply_qs = _parse_action(apply_action)

        # 8. Apply the re-estimate.
        parent_before = db.get_task(demo.database_path, demo.task_id)
        response = httpx.post(
            f"{base}{apply_path}",
            headers=headers,
            json={},
            params=apply_qs,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["decision_state"] == "resolved"

        parent = db.get_task(demo.database_path, demo.task_id)
        assert parent["estimate_tokens"] != parent_before["estimate_tokens"]
        assert parent["metadata"]["estimate_revision"] == 2
        assert parent["metadata"]["previous_estimate_revision"] == 1
        assert parent["metadata"]["low_confidence_decision"] is None
        assert parent["metadata"]["pending_reestimate"] is None
        assert parent["metadata"]["scout_reestimate_attempt_id"]
        assert parent["metadata"]["confidence"] == pytest.approx(0.82)

        # 9. Low-confidence decision is resolved; only the Done Scout remains hidden from Needs You.
        needs = httpx.get(f"{base}/api/projects/{demo.project_id}/needs-you", headers=headers).json()
        low_conf_items = [i for i in needs["items"] if i["task_id"] == demo.task_id]
        assert not low_conf_items
