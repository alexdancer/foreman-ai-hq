from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import Request

from foreman_ai_hq import db, intake
from tests.fake_orchestrator import FakeOrchestratorJobRunner


class FakeUpload:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self):
        return self._content


def _fake_request(tmp_path, llm):
    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    settings = SimpleNamespace(
        database_path=database_path,
        orchestrator_model="openai/gpt-4.1-mini",
    )
    app = SimpleNamespace(state=SimpleNamespace(
        settings=settings,
        orchestrator_job_runner=FakeOrchestratorJobRunner(llm),
    ))
    scope = {"type": "http", "app": app, "path": "/"}
    request = Request(scope)
    project_root = tmp_path / "project"
    project_root.mkdir()
    project = db.upsert_connected_project(
        database_path,
        name="Project",
        root_path=str(project_root.resolve()),
        profile={"language_hints": ["Python"]},
        capability={"state": "launch_ready", "can_launch": True},
    )
    return request, project["id"]


class TestNormalizeChatIntake:
    def test_empty_message_and_no_file_is_rejected(self):
        with pytest.raises(ValueError, match="Type a message or attach a Markdown"):
            import asyncio
            asyncio.run(intake.normalize_chat_intake("", None))

    def test_non_markdown_file_is_rejected(self):
        file = FakeUpload("notes.txt", b"not markdown")
        with pytest.raises(ValueError, match="Only Markdown .md files"):
            import asyncio
            asyncio.run(intake.normalize_chat_intake("hello", file))

    def test_markdown_upload_is_normalized(self):
        file = FakeUpload("tasks.md", b"# Task\n- [ ] Step 1")
        import asyncio
        source, metadata = asyncio.run(intake.normalize_chat_intake(None, file))
        assert source == "# Task\n- [ ] Step 1"
        assert metadata["intake_source"] == "markdown_upload"

    def test_plain_text_is_kept(self):
        import asyncio
        source, metadata = asyncio.run(intake.normalize_chat_intake("Add a list command", None))
        assert source == "Add a list command"
        assert metadata["intake_source"] == "plain_text"


class TestRunIntakeDecision:
    def test_markdown_paste_skips_model_and_needs_breakdown(self, tmp_path):
        request, _ = _fake_request(tmp_path, None)
        import asyncio
        decision = asyncio.run(intake.run_intake_decision(request, "# Markdown", {"intake_source": "markdown_paste"}))
        assert decision["decision"] == "needs_breakdown"

    def test_markdown_upload_skips_model_and_needs_breakdown(self, tmp_path):
        request, _ = _fake_request(tmp_path, None)
        import asyncio
        decision = asyncio.run(intake.run_intake_decision(request, "# Markdown", {"intake_source": "markdown_upload"}))
        assert decision["decision"] == "needs_breakdown"


class TestProcessChatIntake:
    def test_needs_breakdown_never_yields_single_task(self, monkeypatch, tmp_path):
        request, project_id = _fake_request(tmp_path, None)

        async def fake_decision(request, source_text, metadata):
            return {"decision": "needs_breakdown", "reason": "multi-slice"}

        created_breakdown = {"id": "breakdown-1"}

        async def fake_breakdown(request, description, metadata):
            return created_breakdown

        monkeypatch.setattr(intake, "run_intake_decision", fake_decision)
        monkeypatch.setattr(intake, "_create_task_breakdown_review", fake_breakdown)

        import asyncio
        outcome = asyncio.run(intake.process_chat_intake(request, project_id, "Big refactor", {"intake_source": "plain_text"}))
        assert outcome["decision"] == "needs_breakdown"
        assert outcome["breakdown_id"] == "breakdown-1"
        assert "task_id" not in outcome

    def test_single_task_routes_to_estimated_task(self, monkeypatch, tmp_path):
        request, project_id = _fake_request(tmp_path, None)

        async def fake_decision(request, source_text, metadata):
            return {"decision": "single_task", "reason": "small and coherent"}

        created_task = {"id": "task-1"}

        async def fake_estimate(request, description, extra_metadata):
            return created_task

        monkeypatch.setattr(intake, "run_intake_decision", fake_decision)
        monkeypatch.setattr(intake, "_estimate_and_create_task", fake_estimate)

        import asyncio
        outcome = asyncio.run(intake.process_chat_intake(request, project_id, "Add a list command", {"intake_source": "plain_text"}))
        assert outcome["decision"] == "single_task"
        assert outcome["task_id"] == "task-1"
        assert "breakdown_id" not in outcome

    def test_intake_provenance_is_preserved_on_breakdown(self, monkeypatch, tmp_path):
        request, project_id = _fake_request(tmp_path, None)

        async def fake_decision(request, source_text, metadata):
            return {"decision": "needs_breakdown", "reason": "multi-slice"}

        captured_metadata = {}

        async def fake_breakdown(request, description, metadata):
            captured_metadata.update(metadata)
            return {"id": "breakdown-1"}

        monkeypatch.setattr(intake, "run_intake_decision", fake_decision)
        monkeypatch.setattr(intake, "_create_task_breakdown_review", fake_breakdown)

        import asyncio
        asyncio.run(intake.process_chat_intake(request, project_id, "# Markdown", {"intake_source": "markdown_paste"}))
        assert captured_metadata.get("intake_source") == "markdown_paste"
        assert captured_metadata.get("intake_decision") == "needs_breakdown"

    def test_intake_provenance_is_preserved_on_task(self, monkeypatch, tmp_path):
        request, project_id = _fake_request(tmp_path, None)

        async def fake_decision(request, source_text, metadata):
            return {"decision": "single_task", "reason": "small and coherent"}

        captured_metadata = {}

        async def fake_estimate(request, description, extra_metadata):
            captured_metadata.update(extra_metadata)
            return {"id": "task-1"}

        monkeypatch.setattr(intake, "run_intake_decision", fake_decision)
        monkeypatch.setattr(intake, "_estimate_and_create_task", fake_estimate)

        import asyncio
        asyncio.run(intake.process_chat_intake(request, project_id, "Add a list command", {"intake_source": "plain_text"}))
        assert captured_metadata.get("intake_source") == "plain_text"
        assert captured_metadata.get("intake_decision") == "single_task"
