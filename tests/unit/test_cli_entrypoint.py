import json
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from foreman_ai_hq import db
from foreman_ai_hq.app import create_app
from foreman_ai_hq.cli import main
from foreman_ai_hq.demo_worker import stream_payloads
from foreman_ai_hq.project_context import resolve_task_project
from foreman_ai_hq.worker_adapters import get_adapter_builder


ROOT = Path(__file__).resolve().parents[2]


def _clear_cli_env(monkeypatch):
    for name in [
        "TOKEN_TRACKER_DATABASE_PATH",
        "TOKEN_TRACKER_GUARDRAILS_PATH",
        "FOREMAN_AI_HQ_CONTROL_MODEL",
        "FOREMAN_AI_HQ_CONTROL_API_KEY",
        "FOREMAN_AI_HQ_CONTROL_API_KEY_ENV",
        "TOKEN_TRACKER_CONTROL_PLANE_MODEL",
        "TOKEN_TRACKER_CONTROL_PLANE_API_KEY_ENV",
        "TOKEN_TRACKER_LOCAL_RUNNER",
        "TOKEN_TRACKER_PORTAL_TOKEN",
        "TOKEN_TRACKER_PORTAL_AUTH_REQUIRED",
        "TOKEN_TRACKER_PORTAL_TOKEN_ENV",
    ]:
        monkeypatch.delenv(name, raising=False)


def test_bare_foremanctl_defaults_to_serve(monkeypatch, tmp_path):
    calls = []
    _clear_cli_env(monkeypatch)

    def fake_run(app_ref, **kwargs):
        calls.append((app_ref, kwargs))

    monkeypatch.setattr("foreman_ai_hq.cli.uvicorn.run", fake_run)

    exit_code = main([
        "--database-path",
        str(tmp_path / "harness.db"),
        "--guardrails-path",
        str(ROOT / "guardrails.yaml"),
    ])

    assert exit_code == 0
    assert calls == [
        (
            "foreman_ai_hq.app:create_app",
            {
                "host": "127.0.0.1",
                "port": 8000,
                "proxy_headers": False,
                "factory": True,
                "env_file": None,
            },
        )
    ]
    assert __import__("os").environ["TOKEN_TRACKER_PORTAL_AUTH_REQUIRED"] == "0"


def test_serve_cli_arguments_override_environment(monkeypatch, tmp_path):
    calls = []
    _clear_cli_env(monkeypatch)
    monkeypatch.setenv("TOKEN_TRACKER_DATABASE_PATH", "env-harness.db")
    monkeypatch.setenv("TOKEN_TRACKER_GUARDRAILS_PATH", "env-guardrails.yaml")
    monkeypatch.setattr("foreman_ai_hq.cli.uvicorn.run", lambda app_ref, **kwargs: calls.append((app_ref, kwargs)))

    exit_code = main([
        "serve",
        "--host",
        "0.0.0.0",
        "--port",
        "9009",
        "--database-path",
        str(tmp_path / "cli-harness.db"),
        "--guardrails-path",
        str(ROOT / "guardrails.yaml"),
    ])

    assert exit_code == 0
    assert calls[0][1]["host"] == "0.0.0.0"
    assert calls[0][1]["port"] == 9009
    assert calls[0][1]["factory"] is True
    assert calls[0][1]["env_file"] is None
    assert __import__("os").environ["TOKEN_TRACKER_PORTAL_AUTH_REQUIRED"] == "1"


def test_serve_proxy_headers_keep_portal_auth_required_on_loopback(monkeypatch, tmp_path):
    calls = []
    _clear_cli_env(monkeypatch)
    monkeypatch.setattr("foreman_ai_hq.cli.uvicorn.run", lambda app_ref, **kwargs: calls.append((app_ref, kwargs)))

    exit_code = main([
        "serve",
        "--proxy-headers",
        "--database-path",
        str(tmp_path / "cli-harness.db"),
        "--guardrails-path",
        str(ROOT / "guardrails.yaml"),
    ])

    assert exit_code == 0
    assert calls[0][1]["host"] == "127.0.0.1"
    assert calls[0][1]["proxy_headers"] is True
    assert __import__("os").environ["TOKEN_TRACKER_PORTAL_AUTH_REQUIRED"] == "1"


def test_serve_local_runner_flag_sets_backend_environment(monkeypatch, tmp_path):
    calls = []
    _clear_cli_env(monkeypatch)
    monkeypatch.setattr("foreman_ai_hq.cli.uvicorn.run", lambda app_ref, **kwargs: calls.append((app_ref, kwargs)))

    exit_code = main([
        "serve",
        "--database-path",
        str(tmp_path / "cli-harness.db"),
        "--guardrails-path",
        str(ROOT / "guardrails.yaml"),
        "--local-runner",
    ])

    assert exit_code == 0
    assert calls[0][0] == "foreman_ai_hq.app:create_app"
    assert calls[0][1]["factory"] is True
    assert __import__("os").environ["TOKEN_TRACKER_LOCAL_RUNNER"] == "1"


def test_init_writes_non_secret_operator_config(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    exit_code = main(["init"])

    assert exit_code == 0
    config = tmp_path / ".foreman" / "config.toml"
    secrets = tmp_path / ".foreman" / "secrets.env"
    content = config.read_text()
    secret_content = secrets.read_text()
    assert "control_plane_model" not in content
    assert "local_runner_enabled = true" in content
    assert "env var NAMES, not secret values" in content
    assert "your-control-plane-api-key" not in content
    assert "TOKEN_TRACKER_PORTAL_TOKEN=foremanctl-" in secret_content
    assert "FOREMAN_AI_HQ_CONTROL_API_KEY='<your-control-plane-api-key>'" in secret_content
    output = capsys.readouterr().out
    assert "Wrote .foreman/config.toml" in output
    assert "Wrote .foreman/secrets.env" in output
    assert "Start with foremanctl serve" in output
    assert "/settings/control-plane" in output
    assert "open http://localhost:8000/" in output
    assert "Portal token for shared access: set TOKEN_TRACKER_PORTAL_TOKEN" in output
    assert "Control-plane API key: configure FOREMAN_AI_HQ_CONTROL_API_KEY" in output
    assert ".foreman/secrets.env or shell env remain supported alternatives" in output
    assert "export TOKEN_TRACKER_PORTAL_TOKEN" not in output


def test_init_creates_database_and_outside_git_ignore(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    assert main(["init"]) == 0
    db_path = tmp_path / ".foreman" / "harness.db"
    db.create_task(db_path, description="keep this", status="Blocked")
    gitignore = tmp_path / ".foreman" / ".gitignore"
    gitignore.write_text("# keep local notes\n", encoding="utf-8")
    assert main(["init"]) == 0

    assert db_path.exists()
    assert [task["description"] for task in db.list_tasks(db_path)] == ["keep this"]
    gitignore_lines = gitignore.read_text(encoding="utf-8").splitlines()
    assert "# keep local notes" in gitignore_lines
    assert "*" in gitignore_lines
    assert "!.gitignore" in gitignore_lines
    output = capsys.readouterr().out
    assert f"Initialized root {tmp_path}" in output
    assert "Wrote .foreman/harness.db" in output


def test_init_from_git_subdirectory_uses_repo_root_and_exclude(monkeypatch, tmp_path, capsys):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subdir = tmp_path / "nested" / "work"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)

    assert main(["init"]) == 0

    assert (tmp_path / ".foreman" / "config.toml").exists()
    assert (tmp_path / ".foreman" / "secrets.env").exists()
    assert (tmp_path / ".foreman" / "guardrails.yaml").exists()
    assert (tmp_path / ".foreman" / "harness.db").exists()
    assert not (subdir / ".foreman").exists()
    assert ".foreman/" in (tmp_path / ".git" / "info" / "exclude").read_text()
    output = capsys.readouterr().out
    assert f"Initialized root {tmp_path}" in output


def test_init_falls_back_to_cwd_when_git_is_unavailable(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    def raise_missing_git(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr("foreman_ai_hq.cli.subprocess.run", raise_missing_git)

    assert main(["init"]) == 0

    assert (tmp_path / ".foreman" / "config.toml").exists()
    assert (tmp_path / ".foreman" / "harness.db").exists()
    assert (tmp_path / ".foreman" / ".gitignore").read_text() == "*\n!.gitignore\n"


def test_init_explicit_config_and_secrets_paths_are_not_relocated(monkeypatch, tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subdir = tmp_path / "nested"
    subdir.mkdir()
    monkeypatch.chdir(subdir)

    assert main(["init", "--config-path", "local-config.toml", "--secrets-path", "local-secrets.env"]) == 0

    assert (subdir / "local-config.toml").exists()
    assert (subdir / "local-secrets.env").exists()
    assert not (tmp_path / ".foreman" / "config.toml").exists()
    assert not (tmp_path / ".foreman" / "secrets.env").exists()
    assert (tmp_path / ".foreman" / "guardrails.yaml").exists()
    assert (tmp_path / ".foreman" / "harness.db").exists()


def test_serve_from_git_subdirectory_reads_repo_root_config(monkeypatch, tmp_path):
    calls = []
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subdir = tmp_path / "nested" / "work"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)
    _clear_cli_env(monkeypatch)
    monkeypatch.setattr("foreman_ai_hq.cli.uvicorn.run", lambda app_ref, **kwargs: calls.append((app_ref, kwargs)))

    assert main(["init"]) == 0
    _clear_cli_env(monkeypatch)
    assert main(["serve"]) == 0

    assert calls
    assert __import__("os").environ["TOKEN_TRACKER_DATABASE_PATH"] == str(tmp_path / ".foreman" / "harness.db")
    assert __import__("os").environ["TOKEN_TRACKER_GUARDRAILS_PATH"] == str(tmp_path / ".foreman" / "guardrails.yaml")
    assert __import__("os").environ["TOKEN_TRACKER_PORTAL_TOKEN"].startswith("foremanctl-")


def test_check_from_git_subdirectory_reads_repo_root_state(monkeypatch, tmp_path, capsys):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subdir = tmp_path / "nested" / "work"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)
    _clear_cli_env(monkeypatch)

    assert main(["init"]) == 0
    capsys.readouterr()
    _clear_cli_env(monkeypatch)

    assert main(["check"]) == 1

    output = capsys.readouterr().out
    assert f"PASS config loaded {tmp_path / '.foreman' / 'config.toml'}" in output
    assert f"PASS secrets loaded {tmp_path / '.foreman' / 'secrets.env'}" in output
    assert "PASS portal auth disabled for local-only access; TOKEN_TRACKER_PORTAL_TOKEN not required" in output


def test_init_preserves_existing_config_and_prints_configured_secret_env_names(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    capsys.readouterr()
    config = tmp_path / ".foreman" / "config.toml"
    content = config.read_text()
    content = content.replace('portal_token_env = "TOKEN_TRACKER_PORTAL_TOKEN"', 'portal_token_env = "CUSTOM_PORTAL_TOKEN"')
    content = content.replace(
        'control_plane_api_key_env = "FOREMAN_AI_HQ_CONTROL_API_KEY"',
        'control_plane_api_key_env = "CUSTOM_CONTROL_API_KEY"',
    )
    content += '\ncontrol_plane_model = "custom-model"\n'
    config.write_text(content)

    exit_code = main(["init"])

    assert exit_code == 0
    rewritten = config.read_text()
    secrets = tmp_path / ".foreman" / "secrets.env"
    secret_content = secrets.read_text()
    assert 'portal_token_env = "CUSTOM_PORTAL_TOKEN"' in rewritten
    assert 'control_plane_api_key_env = "CUSTOM_CONTROL_API_KEY"' in rewritten
    assert 'control_plane_model = "custom-model"' in rewritten
    assert "CUSTOM_PORTAL_TOKEN=foremanctl-" in secret_content
    assert "CUSTOM_CONTROL_API_KEY='<your-control-plane-api-key>'" in secret_content
    output = capsys.readouterr().out
    assert "Start with foremanctl serve" in output
    assert "/settings/control-plane" in output
    assert "Portal token for shared access: set CUSTOM_PORTAL_TOKEN" in output
    assert "Control-plane API key: configure CUSTOM_CONTROL_API_KEY" in output


def test_init_migrates_secret_values_mistakenly_written_as_env_names(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    capsys.readouterr()
    config = tmp_path / ".foreman" / "config.toml"
    config.write_text(
        config.read_text()
        .replace('portal_token_env = "TOKEN_TRACKER_PORTAL_TOKEN"', 'portal_token_env = "demo-token"')
        .replace(
            'control_plane_api_key_env = "FOREMAN_AI_HQ_CONTROL_API_KEY"',
            'control_plane_api_key_env = "sk-proj-secret"',
        )
    )

    exit_code = main(["init"])

    assert exit_code == 0
    rewritten = config.read_text()
    assert 'portal_token_env = "TOKEN_TRACKER_PORTAL_TOKEN"' in rewritten
    assert 'control_plane_api_key_env = "FOREMAN_AI_HQ_CONTROL_API_KEY"' in rewritten
    secret_content = (tmp_path / ".foreman" / "secrets.env").read_text()
    assert "TOKEN_TRACKER_PORTAL_TOKEN=foremanctl-" in secret_content
    assert "FOREMAN_AI_HQ_CONTROL_API_KEY='<your-control-plane-api-key>'" in secret_content


def test_serve_reads_operator_config_when_flags_missing(monkeypatch, tmp_path):
    calls = []
    monkeypatch.chdir(tmp_path)
    _clear_cli_env(monkeypatch)
    monkeypatch.setattr("foreman_ai_hq.cli.uvicorn.run", lambda app_ref, **kwargs: calls.append((app_ref, kwargs)))
    assert main(["init"]) == 0
    secrets = tmp_path / ".foreman" / "secrets.env"
    secrets.write_text(
        secrets.read_text().replace(
            "FOREMAN_AI_HQ_CONTROL_API_KEY='<your-control-plane-api-key>'",
            "FOREMAN_AI_HQ_CONTROL_API_KEY='fake-control-key'",
        )
    )

    exit_code = main(["serve"])

    assert exit_code == 0
    assert calls[0][1]["host"] == "127.0.0.1"
    assert calls[0][1]["port"] == 8000
    assert __import__("os").environ["TOKEN_TRACKER_DATABASE_PATH"] == str(tmp_path / ".foreman" / "harness.db")
    assert "FOREMAN_AI_HQ_CONTROL_MODEL" not in __import__("os").environ
    assert __import__("os").environ["TOKEN_TRACKER_PORTAL_TOKEN"].startswith("foremanctl-")
    assert __import__("os").environ["FOREMAN_AI_HQ_CONTROL_API_KEY"] == "fake-control-key"
    assert __import__("os").environ["TOKEN_TRACKER_LOCAL_RUNNER"] == "1"
    assert __import__("os").environ["TOKEN_TRACKER_PORTAL_AUTH_REQUIRED"] == "0"


def test_serve_preserves_explicit_portal_auth_required_config(monkeypatch, tmp_path):
    calls = []
    monkeypatch.chdir(tmp_path)
    _clear_cli_env(monkeypatch)
    monkeypatch.setattr("foreman_ai_hq.cli.uvicorn.run", lambda app_ref, **kwargs: calls.append((app_ref, kwargs)))
    assert main(["init"]) == 0
    config = tmp_path / ".foreman" / "config.toml"
    config.write_text(config.read_text() + "portal_auth_required = true\n")

    assert main(["serve"]) == 0

    assert calls[0][1]["host"] == "127.0.0.1"
    assert __import__("os").environ["TOKEN_TRACKER_PORTAL_AUTH_REQUIRED"] == "True"


def test_serve_preserves_legacy_env_alias_over_config(monkeypatch, tmp_path):
    calls = []
    monkeypatch.chdir(tmp_path)
    _clear_cli_env(monkeypatch)
    monkeypatch.setenv("TOKEN_TRACKER_CONTROL_PLANE_MODEL", "legacy-env-model")
    monkeypatch.setattr("foreman_ai_hq.cli.uvicorn.run", lambda app_ref, **kwargs: calls.append((app_ref, kwargs)))
    assert main(["init"]) == 0
    config = tmp_path / ".foreman" / "config.toml"
    config.write_text(config.read_text() + '\ncontrol_plane_model = "config-model"\n')

    exit_code = main(["serve"])

    assert exit_code == 0
    assert calls
    assert "FOREMAN_AI_HQ_CONTROL_MODEL" not in __import__("os").environ
    assert __import__("os").environ["TOKEN_TRACKER_CONTROL_PLANE_MODEL"] == "legacy-env-model"


def test_serve_preserves_local_runner_env_override_over_config(monkeypatch, tmp_path):
    calls = []
    monkeypatch.chdir(tmp_path)
    _clear_cli_env(monkeypatch)
    monkeypatch.setenv("TOKEN_TRACKER_LOCAL_RUNNER", "0")
    monkeypatch.setattr("foreman_ai_hq.cli.uvicorn.run", lambda app_ref, **kwargs: calls.append((app_ref, kwargs)))
    assert main(["init"]) == 0

    exit_code = main(["serve"])

    assert exit_code == 0
    assert calls
    assert __import__("os").environ["TOKEN_TRACKER_LOCAL_RUNNER"] == "0"


def test_check_reports_missing_required_env_without_secret_values(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    capsys.readouterr()
    monkeypatch.delenv("TOKEN_TRACKER_PORTAL_TOKEN_ENV", raising=False)
    monkeypatch.delenv("FOREMAN_AI_HQ_CONTROL_API_KEY_ENV", raising=False)
    monkeypatch.delenv("TOKEN_TRACKER_PORTAL_TOKEN", raising=False)
    monkeypatch.delenv("FOREMAN_AI_HQ_CONTROL_API_KEY", raising=False)

    exit_code = main(["check"])

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "PASS portal auth disabled for local-only access; TOKEN_TRACKER_PORTAL_TOKEN not required" in output
    assert "FAIL control-plane API key env FOREMAN_AI_HQ_CONTROL_API_KEY missing" in output
    assert "/settings/control-plane" in output
    assert ".foreman/secrets.env" in output
    assert "shell environment" in output
    assert "does not configure native Worker CLI auth" in output
    assert "Native Worker CLI auth is separate" in output
    assert "sk-" not in output
    assert "portal-secret" not in output


def test_check_requires_portal_token_for_shared_host(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    config = tmp_path / ".foreman" / "config.toml"
    config.write_text(config.read_text().replace('host = "127.0.0.1"', 'host = "0.0.0.0"'))
    secrets = tmp_path / ".foreman" / "secrets.env"
    secrets.write_text(
        "\n".join(
            line for line in secrets.read_text().splitlines() if not line.startswith("TOKEN_TRACKER_PORTAL_TOKEN=")
        )
        + "\n"
    )
    capsys.readouterr()
    _clear_cli_env(monkeypatch)

    assert main(["check"]) == 1

    output = capsys.readouterr().out
    assert "FAIL portal token env TOKEN_TRACKER_PORTAL_TOKEN missing" in output
    assert "PASS portal auth disabled" not in output


def test_check_reports_control_plane_and_observed_only_worker(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TOKEN_TRACKER_DATABASE_PATH", raising=False)
    monkeypatch.setenv("FOREMAN_AI_HQ_ORCHESTRATOR_MODEL", "anthropic/claude-sonnet-5")
    monkeypatch.delenv("TOKEN_TRACKER_PORTAL_TOKEN_ENV", raising=False)
    monkeypatch.delenv("FOREMAN_AI_HQ_CONTROL_API_KEY_ENV", raising=False)
    monkeypatch.setenv("TOKEN_TRACKER_PORTAL_TOKEN", "portal-secret")
    monkeypatch.setenv("FOREMAN_AI_HQ_CONTROL_API_KEY", "control-secret")
    assert main(["init"]) == 0
    db_path = tmp_path / ".foreman" / "harness.db"
    db.init_db(db_path)
    workdir = tmp_path / "worker"
    workdir.mkdir()
    db.update_worker_adapter(
        db_path,
        "opencode",
        workdir=str(workdir),
        config={"native_launch_template": ["opencode", "run"]},
        supported_models=["openai/gpt-5.5"],
    )
    db.mark_worker_adapter_verification(
        db_path,
        "opencode",
        verified=True,
        evidence={"tracking_mode": "observed_only", "tracking_authoritative": False},
    )
    capsys.readouterr()

    exit_code = main(["check"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "PASS orchestrator model anthropic/claude-sonnet-5 configured from pi inventory" in output
    assert "WARN Worker adapter opencode (opencode) observed_only is diagnostic-only and not normal board-launchable" in output


def test_seed_demo_inserts_synthetic_tasks(tmp_path, capsys):
    db_path = tmp_path / "harness.db"

    exit_code = main(["--database-path", str(db_path), "seed-demo"])

    assert exit_code == 0
    tasks = {task["id"]: task for task in db.list_tasks(db_path)}
    assert "DEMO_TASK_2099_T1" in tasks
    assert "DEMO_TASK_2099_T6" in tasks
    assert "inserted 6" in capsys.readouterr().out


def test_init_creates_guardrails_for_clean_cwd_app_startup(tmp_path, monkeypatch, capsys):
    _clear_cli_env(monkeypatch)
    monkeypatch.chdir(tmp_path)

    assert main(["init"]) == 0

    assert (tmp_path / ".foreman" / "config.toml").exists()
    assert (tmp_path / ".foreman" / "secrets.env").exists()
    assert (tmp_path / ".foreman" / "guardrails.yaml").exists()
    output = capsys.readouterr().out
    assert "Wrote .foreman/guardrails.yaml" in output

    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200


def test_board_only_seed_demo_does_not_change_worker_adapters(tmp_path):
    db_path = tmp_path / "harness.db"

    assert main(["--database-path", str(db_path), "seed-demo"]) == 0

    assert {adapter["id"] for adapter in db.list_worker_adapters(db_path)} == {"claude_code", "codex", "opencode"}


def test_project_demo_adapter_uses_installed_foremanctl_command(tmp_path):
    db_path = tmp_path / "harness.db"
    project_root = tmp_path / "demo-project"

    assert main([
        "--database-path", str(db_path), "seed-demo", "--with-project", "--project-root", str(project_root),
    ]) == 0

    adapter = db.get_worker_adapter(db_path, "demo_worker")
    assert adapter["config"]["command"] == "foremanctl"
    assert adapter["config"]["launch_template"][:2] == ["foremanctl", "demo-worker"]
    assert adapter["config"]["verification_template"][:2] == ["foremanctl", "demo-worker"]
    assert "foremanctl-demo-worker" not in str(adapter["config"])


def test_seed_demo_without_project_leaves_tasks_unlaunchable(tmp_path):
    """Plain seed-demo is board-only; the CLI must say so rather than imply launchability."""
    db_path = tmp_path / "harness.db"

    assert main(["--database-path", str(db_path), "seed-demo"]) == 0

    task = db.get_task(db_path, "DEMO_TASK_2099_T1")
    assert task["metadata"].get("connected_project_id") is None
    assert db.list_connected_projects(db_path) == []


def test_seed_demo_with_project_binds_launchable_tasks(tmp_path, capsys):
    """--with-project must produce tasks that survive the launch-time project gate."""
    db_path = tmp_path / "harness.db"
    project_root = tmp_path / "demo-project"

    exit_code = main(
        ["--database-path", str(db_path), "seed-demo", "--with-project", "--project-root", str(project_root)]
    )

    assert exit_code == 0
    assert (project_root / "README.md").is_file()
    assert (project_root / ".git").is_dir()

    project = db.list_connected_projects(db_path)[0]
    for task in db.list_tasks(db_path):
        resolved, errors = resolve_task_project(db_path, task, expected_project_id=project["id"])
        assert resolved is not None, f"{task['id']} is not launchable: {errors}"
    assert f"connected project {project['id']}" in capsys.readouterr().out


def test_seed_demo_with_project_is_idempotent(tmp_path):
    """Re-seeding the same root must refresh the project, not fork a duplicate."""
    db_path = tmp_path / "harness.db"
    project_root = tmp_path / "demo-project"
    argv = ["--database-path", str(db_path), "seed-demo", "--with-project", "--project-root", str(project_root)]

    assert main(argv) == 0
    assert main(argv) == 0

    assert len(db.list_connected_projects(db_path)) == 1
    assert len(db.list_tasks(db_path)) == 6


def test_demo_worker_streams_events_for_every_live_feed_kind():
    """The synthetic Worker must exercise the real adapter parsing, not a demo seam."""
    builder = get_adapter_builder({"id": "demo_worker", "kind": "claude_code", "config": {}})

    events = [
        builder.map_stream_event(json.dumps(payload))
        for payload in stream_payloads("claude-sonnet-4-6", "DEMO prompt")
    ]
    kinds = {event["kind"] for event in events if event}

    assert {"agent_message", "tool_call", "token", "status"} <= kinds


def test_demo_worker_final_usage_equals_streamed_provisional_total():
    """The final total must reconcile with the provisional lines the operator watched."""
    payloads = stream_payloads("claude-sonnet-4-6", "DEMO prompt")
    final = payloads[-1]
    provisional = [
        payload["usage"]
        for payload in payloads[:-1]
        if payload.get("type") == "result" and isinstance(payload.get("usage"), dict)
    ]

    assert final["usage"]["input_tokens"] == sum(usage["input_tokens"] for usage in provisional)
    assert final["usage"]["output_tokens"] == sum(usage["output_tokens"] for usage in provisional)
    assert final["modelUsage"]["claude-sonnet-4-6"]["inputTokens"] == final["usage"]["input_tokens"]


def test_demo_worker_subcommand_keeps_its_own_flags(capsys):
    """`--model` belongs to the synthetic Worker, not the shared foremanctl parser."""
    assert main(["demo-worker", "--model", "claude-haiku-4-5", "--delay-ms", "0", "DEMO prompt"]) == 0

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines[-1]["modelUsage"].get("claude-haiku-4-5") is not None


def test_seed_demo_is_idempotent(tmp_path, capsys):
    db_path = tmp_path / "harness.db"

    assert main(["--database-path", str(db_path), "seed-demo"]) == 0
    assert main(["--database-path", str(db_path), "seed-demo"]) == 0

    assert len(db.list_tasks(db_path)) == 6
    assert "inserted 0" in capsys.readouterr().out
