"""Planning conversation HTTP lifecycle: start, message, poll, cancel, end."""

from __future__ import annotations

import contextlib
import json
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
import uvicorn

from foreman_ai_hq import db
from foreman_ai_hq.app import create_app
from foreman_ai_hq.settings import Settings

# Reuse the fakes and helpers proven by the ACP conversation tests.
from tests.e2e.test_pi_acp_conversation import (
    BlockingThenNormalLLMClient,
    FakePiLLMClient,
    _pi_rpc_processes,
)

ROOT = Path(__file__).resolve().parents[2]
PORTAL_TOKEN = "test-portal-token"


def _guardrails_path() -> Path:
    guardrails_path = ROOT / "guardrails.yaml"
    if not guardrails_path.is_file():
        guardrails_path = ROOT / "src" / "foreman_ai_hq" / "defaults" / "guardrails.yaml"
    return guardrails_path


def _start_server(app) -> tuple[uvicorn.Server, threading.Thread, int]:
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=0,
            loop="asyncio",
            log_level="warning",
            access_log=False,
        )
    )
    server.capture_signals = lambda: contextlib.nullcontext()  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if getattr(server, "started", False) and server.servers and server.servers[0].sockets:
            break
        time.sleep(0.05)
    else:
        raise RuntimeError("uvicorn server failed to start")
    port = server.servers[0].sockets[0].getsockname()[1]
    return server, thread, port


def _stop_server(server, thread) -> None:
    server.should_exit = True
    thread.join(timeout=5)
    if thread.is_alive():
        server.force_exit = True
        thread.join(timeout=2)


def _client(port) -> httpx.Client:
    return httpx.Client(
        base_url=f"http://127.0.0.1:{port}",
        headers={"Authorization": f"Bearer {PORTAL_TOKEN}"},
        timeout=30,
    )


@pytest.fixture
def project_and_server(tmp_path):
    if not shutil.which("pi"):
        pytest.skip("pi CLI not installed")
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")

    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    root_path = tmp_path / "project-root"
    root_path.mkdir(parents=True, exist_ok=True)
    project = db.upsert_connected_project(
        database_path,
        name="test-project",
        root_path=str(root_path),
        profile={},
        capability={},
    )

    settings = Settings(database_path=database_path, guardrails_path=_guardrails_path())
    app = create_app(settings)
    app.state.llm_client = FakePiLLMClient()
    server, thread, port = _start_server(app)
    try:
        yield project, database_path, port, app
    finally:
        _stop_server(server, thread)


def test_start_requires_portal_auth(tmp_path):
    if not shutil.which("pi"):
        pytest.skip("pi CLI not installed")
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")

    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    root_path = tmp_path / "project-root"
    root_path.mkdir(parents=True, exist_ok=True)
    project = db.upsert_connected_project(
        database_path,
        name="test-project",
        root_path=str(root_path),
        profile={},
        capability={},
    )

    settings = Settings(database_path=database_path, guardrails_path=_guardrails_path())
    app = create_app(settings)
    server, thread, port = _start_server(app)
    try:
        response = httpx.post(f"http://127.0.0.1:{port}/api/projects/{project['id']}/planning/start")
    finally:
        _stop_server(server, thread)

    assert response.status_code == 401
    assert "planning_session_id" not in response.text


def test_start_is_idempotent_and_returns_session(project_and_server):
    project, database_path, port, app = project_and_server
    with _client(port) as client:
        first = client.post(f"/api/projects/{project['id']}/planning/start")
        second = client.post(f"/api/projects/{project['id']}/planning/start")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["planning_session_id"] == second.json()["planning_session_id"]
    assert first.json()["planning_session_id"].startswith("sess_")


def test_message_drives_one_planning_turn_and_appears_in_poll(project_and_server):
    project, database_path, port, app = project_and_server
    with _client(port) as client:
        start = client.post(f"/api/projects/{project['id']}/planning/start")
        assert start.status_code == 200
        session_id = start.json()["planning_session_id"]

        message = client.post(
            f"/api/projects/{project['id']}/planning/message",
            json={"message": "hi"},
        )
        assert message.status_code == 200
        body = message.json()
        assert body["content"] == "ok"
        assert body["stop_reason"] == "end_turn"
        assert body["planning_session_id"] == session_id

        poll = client.get(f"/api/projects/{project['id']}/planning/events?since_id=0")
        assert poll.status_code == 200
        payload = poll.json()
        assert payload["planning_session_id"] == session_id
        assert len(payload["events"]) == 1
        assert payload["has_more"] is False
        assert payload["next_since_id"] == payload["events"][0]["id"]

    artifact = db.build_session_artifact(database_path, session_id)
    assert len(artifact["token_log"]) == 1
    turn = artifact["token_log"][0]
    assert turn["usage_kind"] == "planning"
    assert turn["raw_usage"]["spend_category"] == "planning"
    assert turn["raw_usage"]["usage_source"] == "harness_proxy"


def test_poll_returns_events_after_cursor(project_and_server):
    project, database_path, port, app = project_and_server
    with _client(port) as client:
        client.post(f"/api/projects/{project['id']}/planning/start")
        client.post(f"/api/projects/{project['id']}/planning/message", json={"message": "one"})
        client.post(f"/api/projects/{project['id']}/planning/message", json={"message": "two"})

        all_events = client.get(f"/api/projects/{project['id']}/planning/events").json()
        first_id = all_events["events"][0]["id"]
        second_id = all_events["events"][1]["id"]

        since = client.get(f"/api/projects/{project['id']}/planning/events?since_id={first_id}")
        payload = since.json()

    assert len(payload["events"]) == 1
    assert payload["events"][0]["id"] == second_id
    assert payload["next_since_id"] == second_id
    assert payload["has_more"] is False


def test_cancel_resolves_in_flight_turn_and_conversation_stays_usable(tmp_path):
    if not shutil.which("pi"):
        pytest.skip("pi CLI not installed")
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")

    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    root_path = tmp_path / "project-root"
    root_path.mkdir(parents=True, exist_ok=True)
    project = db.upsert_connected_project(
        database_path,
        name="test-project",
        root_path=str(root_path),
        profile={},
        capability={},
    )

    settings = Settings(database_path=database_path, guardrails_path=_guardrails_path())
    app = create_app(settings)
    fake = BlockingThenNormalLLMClient()
    app.state.llm_client = fake
    server, thread, port = _start_server(app)
    try:
        with _client(port) as client:
            start = client.post(f"/api/projects/{project['id']}/planning/start")
            session_id = start.json()["planning_session_id"]

            message_result: dict[str, Any] = {}

            def _message_in_thread() -> None:
                try:
                    with _client(port) as thread_client:
                        resp = thread_client.post(
                            f"/api/projects/{project['id']}/planning/message",
                            json={"message": "block me"},
                        )
                    message_result.update(resp.json())
                except Exception as exc:  # pragma: no cover
                    message_result["error"] = str(exc)

            msg_thread = threading.Thread(target=_message_in_thread)
            msg_thread.start()
            assert fake.block_started.wait(timeout=15), "prompt did not reach proxy"
            time.sleep(0.2)

            cancel = client.post(f"/api/projects/{project['id']}/planning/cancel")
            assert cancel.status_code == 200
            assert cancel.json()["cancelled"] is True

            msg_thread.join(timeout=15)
            assert not msg_thread.is_alive()

            assert message_result.get("stop_reason") == "cancelled"
            assert message_result.get("content") == "partial"

            follow = client.post(
                f"/api/projects/{project['id']}/planning/message",
                json={"message": "echo"},
            )
            assert follow.status_code == 200
            assert follow.json()["stop_reason"] == "end_turn"
            assert follow.json()["content"] == "ok"

    finally:
        fake.release()
        _stop_server(server, thread)

    artifact = db.build_session_artifact(database_path, session_id)
    assert len(artifact["token_log"]) == 1
    turn = artifact["token_log"][0]
    assert turn["usage_kind"] == "planning"
    assert turn["raw_usage"]["usage_source"] == "harness_proxy"


def test_end_terminates_pi_and_leaves_no_orphan(project_and_server):
    project, database_path, port, app = project_and_server
    with _client(port) as client:
        start = client.post(f"/api/projects/{project['id']}/planning/start")
        session_id = start.json()["planning_session_id"]
        end = client.post(f"/api/projects/{project['id']}/planning/end")
        assert end.status_code == 200
        assert end.json()["ended"] is True

    time.sleep(0.5)
    assert _pi_rpc_processes() == []

    # Once ended, subsequent operations report the conversation gone.
    with _client(port) as client:
        retry = client.post(f"/api/projects/{project['id']}/planning/message", json={"message": "hi"})
    assert retry.status_code == 404


def test_registry_bounds_and_reaps_lru_idle(tmp_path):
    if not shutil.which("pi"):
        pytest.skip("pi CLI not installed")
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")

    database_path = tmp_path / "harness.db"
    db.init_db(database_path)
    p1_root = tmp_path / "p1"
    p1_root.mkdir(parents=True, exist_ok=True)
    p2_root = tmp_path / "p2"
    p2_root.mkdir(parents=True, exist_ok=True)
    project1 = db.upsert_connected_project(
        database_path,
        name="p1",
        root_path=str(p1_root),
        profile={},
        capability={},
    )
    project2 = db.upsert_connected_project(
        database_path,
        name="p2",
        root_path=str(p2_root),
        profile={},
        capability={},
    )

    from foreman_ai_hq.routes.planning_conversation import PlanningConversationRegistry

    settings = Settings(database_path=database_path, guardrails_path=_guardrails_path())
    app = create_app(settings)
    app.state.llm_client = FakePiLLMClient()
    server, thread, port = _start_server(app)
    try:
        # Swap to a tiny registry so we can prove capacity and LRU idle reap.
        app.state.planning_registry = PlanningConversationRegistry(ttl_seconds=2.0, max_size=1)

        with _client(port) as client:
            start1 = client.post(f"/api/projects/{project1['id']}/planning/start")
            assert start1.status_code == 200

            # Capacity full while project1 is still active.
            start2_immediate = client.post(f"/api/projects/{project2['id']}/planning/start")
            assert start2_immediate.status_code == 503

            time.sleep(2.2)
            start2 = client.post(f"/api/projects/{project2['id']}/planning/start")
            assert start2.status_code == 200

        # The idle project1 conversation should have been reaped.
        with _client(port) as client:
            stale = client.post(f"/api/projects/{project1['id']}/planning/message", json={"message": "hi"})
        assert stale.status_code == 404

    finally:
        _stop_server(server, thread)

    time.sleep(0.5)
    # After teardown only one pi process should remain.
    assert len(_pi_rpc_processes()) <= 1


def test_persisted_turns_contain_no_secrets(project_and_server):
    project, database_path, port, app = project_and_server
    with _client(port) as client:
        client.post(f"/api/projects/{project['id']}/planning/start")
        client.post(
            f"/api/projects/{project['id']}/planning/message",
            json={"message": "my key is sk_plan_leaked_123"},
        )
        events = client.get(f"/api/projects/{project['id']}/planning/events").json()["events"]

    assert len(events) == 1
    detail = events[0]["detail"]
    raw = json.dumps(detail)
    assert "sk_plan_leaked_123" not in raw
    assert "***REDACTED***" in raw or "sk_plan_" not in raw
