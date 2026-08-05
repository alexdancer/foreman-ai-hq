from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from foreman_ai_hq import db
from foreman_ai_hq.app import create_app
from foreman_ai_hq.settings import Settings


ROOT = Path(__file__).resolve().parents[2]
PORTAL_TOKEN = "test-portal-token"


def _client(tmp_path: Path) -> TestClient:
    settings = Settings(
        database_path=tmp_path / "harness.db",
        guardrails_path=ROOT / "guardrails.yaml",
    )
    db.init_db(settings.database_path)
    project_root = tmp_path / "connected-project"
    project_root.mkdir()
    db.upsert_connected_project(
        settings.database_path,
        name=project_root.name,
        root_path=str(project_root.resolve()),
        profile={"name": project_root.name, "root_path": str(project_root.resolve())},
        capability={"state": "analysis_ready", "can_launch": False},
    )
    return TestClient(create_app(settings))


@pytest.mark.parametrize(
    ("path", "expected_status"),
    [
        ("/estimate", 404),
        ("/tasks", 404),
        ("/tasks/estimate-form", 405),
    ],
)
def test_legacy_public_task_intake_routes_are_retired(tmp_path, path, expected_status):
    with _client(tmp_path) as client:
        response = client.post(
            path,
            headers={"Authorization": f"Bearer {PORTAL_TOKEN}"},
            json={"description": "Bypass Planning Chat"},
        )

    assert response.status_code == expected_status
    assert db.list_tasks(tmp_path / "harness.db") == []


def test_project_scoped_legacy_intake_and_read_only_proof_routes_are_retired(tmp_path):
    with _client(tmp_path) as client:
        project = db.list_connected_projects(tmp_path / "harness.db")[0]
        headers = {"Authorization": f"Bearer {PORTAL_TOKEN}"}
        estimate = client.post(
            f"/projects/{project['id']}/tasks/estimate-form",
            headers=headers,
            data={"description": "Bypass Planning Chat"},
        )
        proof = client.post(
            f"/settings/project/{project['id']}/read-only-proof",
            headers=headers,
        )

    assert estimate.status_code == 404
    assert proof.status_code == 404
    assert db.list_tasks(tmp_path / "harness.db") == []
