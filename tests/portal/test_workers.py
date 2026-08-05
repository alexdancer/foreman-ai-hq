from foreman_ai_hq import db
from tests.portal.helpers import PORTAL_TOKEN, _client, _portal_headers, _project_metadata


def _adapter(payload, adapter_id):
    return next(a for a in payload["adapters"] if a["id"] == adapter_id)


def test_settings_workers_page_requires_auth_and_renders_safe_adapter_cards(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        assert client.get("/api/settings/workers").status_code == 401
        db.update_worker_adapter(
            tmp_path / "harness.db",
            "codex",
            workdir=str(tmp_path),
            config={"env": {"OPENAI_API_KEY": "super-secret-key"}},
            supported_models=["5.4"],
            is_default=True,
        )
        db.mark_worker_adapter_verification(
            tmp_path / "harness.db",
            "codex",
            verified=True,
            evidence={"stdout": "FOREMAN_AI_HQ_ADAPTER_OK", "env": {"OPENAI_API_KEY": "super-secret-key"}},
        )

        response = client.get("/api/settings/workers", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"adapters", "active_adapter_id", "next_action"}
    assert set(payload["next_action"]) == {"label", "detail", "href"}

    adapters_by_id = {a["id"]: a for a in payload["adapters"]}
    assert set(adapters_by_id) == {"claude_code", "codex", "opencode"}
    assert "hermes" not in adapters_by_id

    assert payload["active_adapter_id"] == "codex"
    assert "/settings/workers" in payload["next_action"]["href"]

    codex = adapters_by_id["codex"]
    assert codex["is_default"] is True
    assert codex["configured"] is False
    assert codex["launchable"] is False
    assert codex["verification_evidence"]["stdout"] == "FOREMAN_AI_HQ_ADAPTER_OK"

    # Backend state: some adapters are configured, the default one here is not.
    configured = {a["id"]: a["configured"] for a in payload["adapters"]}
    assert any(configured.values())
    assert not all(configured.values())

    # The rendered labels "Worker adapters", "Claude Code", "Codex", "OpenCode",
    # "OpenCode diagnostics", etc. are React presentation; the JSON handoff uses
    # ids/kinds and bounded diagnostics instead.
    assert "super-secret-key" not in response.text
    assert "OPENAI_API_KEY" not in response.text
    assert "sk_sess_" not in response.text


def test_worker_model_discovery_route_uses_native_harness_and_updates_portal(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        calls = []

        def fake_discovery_runner(plan):
            calls.append(plan)
            return {
                "returncode": 0,
                "stdout": '[{"id":"anthropic/claude-sonnet-4"},{"id":"openai/gpt-5.1"}]',
                "stderr": "",
            }

        getattr(client.app, "state").worker_model_discovery_runner = fake_discovery_runner
        response = client.post("/settings/workers/opencode/discover-models", headers=_portal_headers())
        page = client.get("/api/settings/workers?adapter_id=opencode", headers=_portal_headers())

    assert response.status_code == 200
    assert response.json()["models"] == ["anthropic/claude-sonnet-4", "openai/gpt-5.1"]
    assert calls[0].env == {}

    payload = page.json()
    opencode = _adapter(payload, "opencode")
    assert opencode["model_discovery_label"] == "Native model discovery"
    assert opencode["connection_type"] == "CLI Worker"
    assert "anthropic/claude-sonnet-4" in opencode["discovered_models"]
    assert "openai/gpt-5.1" in opencode["discovered_models"]
    assert {opt["mode"] for opt in opencode["tracking_mode_options"]} >= {"native_usage", "observed_only"}


def test_claude_code_discovery_route_uses_curated_inventory_and_preserves_adapter_context(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        db.update_worker_adapter(database_path, "codex", is_default=True)
        calls = []

        def fake_discovery_runner(plan):
            calls.append(plan)
            return {"returncode": 0, "stdout": "claude fable\n", "stderr": ""}

        getattr(client.app, "state").worker_model_discovery_runner = fake_discovery_runner
        response = client.post(
            "/settings/workers/claude_code/discover-models",
            headers={**_portal_headers(), "Accept": "text/html"},
            follow_redirects=False,
        )
        page = client.get("/api/settings/workers?adapter_id=claude_code", headers=_portal_headers())

    assert response.status_code == 303
    assert response.headers["location"] == "/settings/workers?adapter_id=claude_code"
    assert calls == []

    payload = page.json()
    assert payload["active_adapter_id"] == "claude_code"
    claude = _adapter(payload, "claude_code")
    assert claude["model_discovery_label"] == "Curated model inventory"
    expected_curated = {
        "claude-opus-4-8",
        "claude-sonnet-5",
        "claude-haiku-4-5",
    }
    assert expected_curated <= set(claude["discovered_models"])
    assert "claude fable" not in claude["discovered_models"]
    assert "claude-haiku-4-5-20251001" not in claude["discovered_models"]


def test_worker_allowed_models_route_saves_only_discovered_models(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        db.update_worker_adapter(
            database_path,
            "opencode",
            config={"model_discovery": {"models": ["openai/gpt-5.1", "opencode/big-pickle"]}},
            supported_models=["openai/gpt-5.1"],
        )
        response = client.post(
            "/settings/workers/opencode/allowed-models",
            headers=_portal_headers(),
            data={"allowed_models": "opencode/big-pickle"},
            follow_redirects=False,
        )
        rejected = client.post(
            "/settings/workers/opencode/allowed-models",
            headers=_portal_headers(),
            data={"allowed_models": "undiscovered/model"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert db.get_worker_adapter(database_path, "opencode")["supported_models"] == ["opencode/big-pickle"]
    assert rejected.status_code == 303
    assert rejected.headers["location"].startswith("/settings/workers?adapter_id=opencode")
    assert "error=" in rejected.headers["location"]
    assert db.get_worker_adapter(database_path, "opencode")["supported_models"] == ["opencode/big-pickle"]


def test_workers_page_shows_allowed_model_checkboxes_after_discovery(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        db.update_worker_adapter(
            database_path,
            "opencode",
            config={"model_discovery": {"models": ["openai/gpt-5.1", "opencode/big-pickle"]}},
            supported_models=["openai/gpt-5.1"],
            is_default=True,
        )
        response = client.get("/api/settings/workers?adapter_id=opencode", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_adapter_id"] == "opencode"
    opencode = _adapter(payload, "opencode")
    assert opencode["supported_models"] == ["openai/gpt-5.1"]
    assert set(opencode["discovered_models"]) >= {"openai/gpt-5.1", "opencode/big-pickle"}
    assert opencode["model_discovery_label"] == "Native model discovery"
    # HTML form actions, data-* attributes, and checkbox labels are React-owned
    # presentation; the JSON handoff exposes the same allowed/discovered model state.


def test_worker_verify_template_error_is_not_reported_as_missing_adapter(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        db.update_worker_adapter(
            database_path,
            "opencode",
            config={"verification_template": ["opencode", "{missing_variable}", "{proxy_url}", "{session_api_key}"]},
            supported_models=["5.4"],
        )
        response = client.post(
            "/settings/workers/opencode/verify",
            headers=_portal_headers(),
            json={"model": "5.4"},
        )

    assert response.status_code == 422
    assert "worker adapter configuration invalid" in response.json()["detail"]
    assert response.json()["detail"] != "worker adapter not found"


def test_board_uses_verified_worker_adapter_status(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        metadata = _project_metadata(database_path, tmp_path / "connected-project")
        db.create_task(
            database_path,
            description="Launchable estimated task",
            status="Estimated",
            estimate_tokens=25000,
            recommended_model="5.4",
            metadata=metadata,
        )
        db.update_worker_adapter(
            tmp_path / "harness.db",
            "codex",
            workdir=str(tmp_path),
            config={"command": "codex"},
            supported_models=["5.4"],
        )
        db.mark_worker_adapter_verification(tmp_path / "harness.db", "codex", verified=True, evidence={"ok": True})

        response = client.get(f"/api/projects/{metadata['connected_project_id']}/board", headers=_portal_headers())
        payload = response.json()

    assert response.status_code == 200
    task = next(t for t in payload["tasks_by_status"]["Estimated"] if t["summary"]["text"] == "Launchable estimated task")
    assert task["recommended_model"] == "5.4"
    assert task["controls"]["can_launch"] is True


def test_configure_route_sets_adapter_default_without_workdir(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.post(
            "/settings/workers/opencode/configure",
            headers=_portal_headers(),
            data={"workdir": str(tmp_path / "my-project"), "is_default": "1"},
            follow_redirects=False,
        )
    assert response.status_code == 303
    assert response.headers["location"] == "/settings/workers?adapter_id=opencode"
    adapter = db.get_worker_adapter(tmp_path / "harness.db", "opencode")
    assert adapter["workdir"] is None
    assert adapter["is_default"] is True
    assert adapter["configured"] is True


def test_configure_route_sets_default_and_clears_previous(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        # Set opencode as default
        client.post(
            "/settings/workers/opencode/configure",
            headers=_portal_headers(),
            data={"workdir": str(tmp_path), "is_default": "1"},
        )
        # Set codex as default - should clear opencode
        client.post(
            "/settings/workers/codex/configure",
            headers=_portal_headers(),
            data={"workdir": str(tmp_path), "is_default": "1"},
        )
    assert db.get_worker_adapter(database_path, "opencode")["is_default"] is False
    assert db.get_worker_adapter(database_path, "codex")["is_default"] is True


def test_workers_page_shows_diagnostics_for_all_adapters(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.get("/api/settings/workers", headers=_portal_headers())
    assert response.status_code == 200
    payload = response.json()
    for adapter in payload["adapters"]:
        # The JSON handoff exposes a bounded, sanitized diagnostics object (or
        # null) per adapter; rendered per-adapter diagnostics headings are React
        # presentation and are not serialized.
        assert "diagnostics" in adapter
        if adapter["diagnostics"] is not None:
            assert "executable" not in adapter["diagnostics"]
            assert "/secret/path" not in response.text


def test_board_shows_adapter_and_model_selectors(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        metadata = _project_metadata(database_path, tmp_path / "connected-project")
        db.create_task(
            database_path,
            description="Test task",
            status="Estimated",
            estimate_tokens=1000,
            recommended_model="5.4",
            metadata=metadata,
        )
        response = client.get(f"/api/projects/{metadata['connected_project_id']}/board", headers=_portal_headers())
        payload = response.json()

    assert response.status_code == 200
    assert payload["adapters"]
    assert all({"id", "is_default", "launchable", "allowed_models", "tracking"} <= set(a) for a in payload["adapters"])
    task = next(t for t in payload["tasks_by_status"]["Estimated"] if t["summary"]["text"] == "Test task")
    assert task["recommended_model"] == "5.4"
    assert task["controls"]["can_launch"] is True
    # "selected=5.4", "Worker Adapter", "Worker model", "refreshed", and form
    # markup like 'name="model"' are React presentation, not backend state.


def test_board_does_not_offer_recommended_model_when_adapter_has_no_allowed_models(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        metadata = _project_metadata(database_path, tmp_path / "connected-project")
        db.create_task(
            database_path,
            description="No allowed model task",
            status="Estimated",
            estimate_tokens=1000,
            recommended_model="5.4",
            metadata=metadata,
        )
        db.update_worker_adapter(
            database_path,
            "codex",
            config={"model_discovery": {"models": ["5.4"]}},
            supported_models=[],
            is_default=True,
        )
        response = client.get(f"/api/projects/{metadata['connected_project_id']}/board", headers=_portal_headers())
        payload = response.json()

    assert response.status_code == 200
    codex = next(a for a in payload["adapters"] if a["id"] == "codex")
    assert codex["is_default"] is True
    assert codex["allowed_models"] == []
    task = next(t for t in payload["tasks_by_status"]["Estimated"] if t["summary"]["text"] == "No allowed model task")
    assert task["recommended_model"] == "5.4"
    assert task["launch_model"] is None
    assert task["controls"]["can_launch"] is True
    # '<option value="">(no allowed models)</option>' and the
    # "5.4 (no discovered models)" label are rendered by React; the backend
    # exposes allowed_models as an empty list and the task's recommended_model.


def test_board_launch_button_visible_without_verified_adapter(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        metadata = _project_metadata(database_path, tmp_path / "connected-project")
        db.create_task(
            database_path,
            description="Unverified launch test",
            status="Estimated",
            estimate_tokens=500,
            recommended_model="claude-sonnet",
            metadata=metadata,
        )
        response = client.get(f"/api/projects/{metadata['connected_project_id']}/board", headers=_portal_headers())
        payload = response.json()

    assert response.status_code == 200
    task = next(t for t in payload["tasks_by_status"]["Estimated"] if t["summary"]["text"] == "Unverified launch test")
    assert task["controls"]["can_launch"] is True
    assert task["controls"]["setup_href"] == "/settings/workers"
    assert payload["board_summary"]["launch_ready"] is False


def test_launch_unverified_adapter_shows_error_banner(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        task = db.create_task(
            database_path,
            description="Will fail launch",
            status="Estimated",
            estimate_tokens=500,
            recommended_model="5.4",
            metadata=_project_metadata(database_path, tmp_path / "connected-project"),
        )
        response = client.post(
            f"/tasks/{task['id']}/launch",
            headers={**_portal_headers(), "Accept": "text/html"},
            data={"adapter_id": "codex", "model": "5.4"},
            follow_redirects=False,
        )
        project_id = task["metadata"]["connected_project_id"]
        board = client.get(
            f"/api/projects/{project_id}/board",
            headers=_portal_headers(),
        )
        payload = board.json()

    assert response.status_code == 303
    location = response.headers["location"]
    assert "error=" in location
    assert response.headers["location"].startswith(f"/projects/{project_id}?error=")

    assert payload["board_summary"]["launch_ready"] is False
    assert all(not a["launchable"] for a in payload["adapters"])
    board_task = next(t for t in payload["tasks_by_status"]["Estimated"] if t["summary"]["text"] == "Will fail launch")
    assert board_task["controls"]["setup_href"] == "/settings/workers"
    # "Open Worker Setup" and the board error banner copy are React-owned; the
    # handoff exposes the setup_href and launch_ready=false backend state.


def test_guided_worker_setup_selects_default_adapter_and_keeps_advanced_details(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        db.update_worker_adapter(database_path, "codex", workdir=str(tmp_path), config={"command": "codex"}, is_default=True)
        response = client.get("/api/settings/workers", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    codex = _adapter(payload, "codex")
    assert codex["is_default"] is True
    assert codex["configured"] is True
    assert codex["launchable"] is False
    assert codex["connection_type"] == "CLI Worker"

    # Verify the guided next step is a setup blocker, not launch-ready.
    assert payload["active_adapter_id"] == "codex"
    assert payload["next_action"]["label"] in {
        "Approve Worker models",
        "Verify adapter",
        "Fix CLI setup",
    }
    assert "/settings/workers" in payload["next_action"]["href"]

    # Tracking-mode options include observed_only for this CLI-only adapter.
    modes = {opt["mode"] for opt in codex["tracking_mode_options"]}
    assert "observed_only" in modes
    assert any(opt["label"] == "CLI: Observe command only" for opt in codex["tracking_mode_options"])
    # Proxy-governed modes are not available because no proxy template is configured.
    assert "proxy_governed" not in modes
    assert all(a["connection_type"] == "CLI Worker" for a in payload["adapters"])

    # Advanced details are surfaced through bounded evidence/diagnostic fields.
    for adapter in payload["adapters"]:
        assert "verification_evidence" in adapter
        assert "verification_diagnostic" in adapter

    # "PROVIDER_API_KEY" is a control-plane secret and must not leak into the
    # Worker settings handoff.
    assert "PROVIDER_API_KEY" not in response.text

    # "Codex setup", "Choose active adapter", "Advanced details", "API / Proxy Worker",
    # and "Governed via Harness Proxy" are React-rendered copy; the JSON endpoint
    # exposes the underlying adapter state instead.


def test_worker_setup_shows_claude_login_diagnostic_in_primary_readiness_copy(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    database_path = tmp_path / "harness.db"
    with _client(tmp_path) as client:
        db.update_worker_adapter(
            database_path,
            "claude_code",
            config={"command": "claude", "allowed_models_configured": True},
            supported_models=["claude-opus-4-8"],
            is_default=True,
        )
        db.mark_worker_adapter_verification(
            database_path,
            "claude_code",
            verified=False,
            evidence={
                "returncode": 1,
                "stdout": '{"type":"error","message":"Not logged in · Please run /login api_key=abc123"}',
                "stderr": "raw setup output Bearer abc.def",
                "diagnostic": {
                    "code": "claude_code_not_logged_in",
                    "summary": "Not logged in · Please run /login",
                    "next_action": "Run `/login` in Claude Code, then verify the adapter again.",
                    "setup_href": "/settings/workers",
                },
            },
        )

        response = client.get("/api/settings/workers?adapter_id=claude_code", headers=_portal_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_adapter_id"] == "claude_code"
    claude = _adapter(payload, "claude_code")
    assert claude["configured"] is True
    assert claude["launchable"] is False

    assert claude["verification_diagnostic"]["summary"] == "Not logged in · Please run /login"
    assert claude["verification_diagnostic"]["next_action"] == "Run `/login` in Claude Code, then verify the adapter again."
    assert claude["verification_diagnostic"]["setup_href"] == "/settings/workers"

    assert payload["next_action"]["label"] == "Fix CLI setup"
    assert payload["next_action"]["detail"] == "Not logged in · Please run /login"
    assert payload["next_action"]["href"] == "/settings/workers"

    assert "raw setup output" in claude["verification_evidence"]["stderr"]
    assert "api_key=abc123" not in response.text
    assert "Bearer abc.def" not in response.text

    # "Open Worker Setup" and "Advanced details" are React copy; the diagnostic
    # summary, next_action, and setup_href carry the same backend state.


def test_refresh_diagnostics_route_forces_redetection(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", PORTAL_TOKEN)
    with _client(tmp_path) as client:
        response = client.post(
            "/settings/workers/opencode/refresh-diagnostics",
            headers=_portal_headers(),
            follow_redirects=False,
        )
    assert response.status_code == 303
    assert response.headers["location"] == "/settings/workers?adapter_id=opencode"
