from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from foreman_ai_hq import db
from foreman_ai_hq.app import create_app
from foreman_ai_hq.settings import Settings


ROOT = Path(__file__).resolve().parents[2]


def _client(tmp_path: Path) -> TestClient:
    settings = Settings(
        database_path=tmp_path / "harness.db",
        guardrails_path=ROOT / "guardrails.yaml",
    )
    db.init_db(settings.database_path)
    app = create_app(settings)
    project_root = tmp_path / "connected-project"
    project_root.mkdir(exist_ok=True)
    db.upsert_connected_project(
        settings.database_path,
        name=project_root.name,
        root_path=str(project_root.resolve()),
        profile={"name": project_root.name, "root_path": str(project_root.resolve())},
        capability={"state": "launch_ready", "can_launch": True},
    )
    return TestClient(app)


def _seed_task(tmp_path: Path, **overrides):
    values = {
        "description": "Estimated task",
        "status": "Estimated",
        "estimate_tokens": 8_000,
        "recommended_model": "claude-haiku",
    }
    values.update(overrides)
    return db.create_task(tmp_path / "harness.db", **values)


def test_update_task_lifecycle(tmp_path):
    with _client(tmp_path) as client:
        created = _seed_task(tmp_path, description="Add save command")
        updated = client.put(
            f"/tasks/{created['id']}",
            json={
                "status": "Ready",
                "estimate_tokens": 12_000,
                "recommended_model": "claude-haiku",
                "description": "Add save command and tests",
            },
        )

    assert updated.status_code == 200
    assert updated.json()["id"] == created["id"]
    assert updated.json()["status"] == "Estimated"
    assert updated.json()["estimate_tokens"] == 12_000
    assert updated.json()["recommended_model"] == "claude-haiku"
    assert updated.json()["description"] == "Add save command and tests"


def test_update_task_rejects_noncanonical_status_as_blocked(tmp_path):
    with _client(tmp_path) as client:
        created = _seed_task(tmp_path)
        updated = client.put(f"/tasks/{created['id']}", json={"status": "Backlog"})

    assert updated.status_code == 200
    assert updated.json()["status"] == "Estimated"
    metadata = updated.json()["metadata"]
    assert metadata["blocked_reason"] == "Unsupported task status: Backlog"
    assert metadata["original_status"] == "Backlog"


def test_direct_update_done_requires_completed_session(tmp_path):
    with _client(tmp_path) as client:
        created = _seed_task(tmp_path, description="Cannot directly finish")
        updated = client.put(f"/tasks/{created['id']}", json={"status": "Done"})

    assert updated.status_code == 200
    assert updated.json()["status"] == "Estimated"
    assert updated.json()["metadata"]["blocked_reason"] == (
        "Use refresh endpoint to finalize completed sessions."
    )


def test_direct_update_done_allows_completed_session_backing(tmp_path):
    with _client(tmp_path) as client:
        session = db.create_session(
            tmp_path / "harness.db",
            task_description="Completed externally",
            model="claude-haiku",
            session_key_hash="f" * 64,
            guardrail_overrides={},
            status="completed",
        )
        created = _seed_task(
            tmp_path,
            description="Completed externally",
            session_id=session["id"],
        )
        updated = client.put(f"/tasks/{created['id']}", json={"status": "Done"})

    assert updated.status_code == 200
    assert updated.json()["status"] == "Done"


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"estimate_tokens": True}, "estimate_tokens"),
        ({"estimate_tokens": -1}, "estimate_tokens"),
        ({"actual_tokens": True}, "actual_tokens"),
        ({"actual_tokens": -1}, "actual_tokens"),
    ],
)
def test_update_task_rejects_bool_and_negative_numeric_fields(tmp_path, payload, field):
    with _client(tmp_path) as client:
        created = _seed_task(tmp_path, description="Bad numeric update")
        response = client.put(f"/tasks/{created['id']}", json=payload)

    assert response.status_code == 422
    assert field in response.text


def test_update_missing_task_returns_404(tmp_path):
    with _client(tmp_path) as client:
        response = client.put("/tasks/missing", json={"status": "Done"})

    assert response.status_code == 404
