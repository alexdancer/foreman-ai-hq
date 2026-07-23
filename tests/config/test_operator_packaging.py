from importlib.metadata import distribution
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[2]


def test_docker_packaging_files_define_demo_container_contract():
    dockerfile = (ROOT / "Dockerfile").read_text()
    compose = (ROOT / "docker-compose.yml").read_text()
    dockerignore = (ROOT / ".dockerignore").read_text()

    assert "foreman-ai-hq" in compose
    assert "foreman-ai-hq:local" in compose
    assert "8000:8000" in compose
    assert "TOKEN_TRACKER_DATABASE_PATH=/data/harness.db" in compose
    assert "TOKEN_TRACKER_PORTAL_TOKEN=${TOKEN_TRACKER_PORTAL_TOKEN:-DEMO_PORTAL_TOKEN_2099}" in compose
    assert "python" in compose and "/health" in compose

    assert "COPY guardrails.yaml" in dockerfile
    assert "foremanctl" in dockerfile and "serve" in dockerfile
    assert "8000" in dockerfile

    assert ".venv" in dockerignore
    assert "harness.db" in dockerignore


def test_pyproject_exposes_foremanctl_console_script():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["scripts"]["foremanctl"] == "foreman_ai_hq.cli:main"


def test_installed_distribution_exposes_foremanctl_console_script():
    dist = distribution("foreman-ai-hq")

    entrypoint = next(entry for entry in dist.entry_points if entry.name == "foremanctl")
    assert entrypoint.group == "console_scripts"
    assert entrypoint.value == "foreman_ai_hq.cli:main"


def test_pyproject_has_public_cli_package_metadata():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    project = pyproject["project"]

    assert project["readme"] == "README.md"
    assert project["license"] == "MIT"
    assert "token-tracking" in project["keywords"]
    assert project["urls"]["Repository"] == "https://github.com/alexdancer/foreman-ai-hq"


def test_pyproject_packages_server_rendered_templates_and_defaults():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    # Server-rendered templates/defaults, the tracked pi orchestrator profile, and the
    # pinned Node bridge config ship alongside the built React Portal shell assets so a
    # packaged install can serve them.
    assert pyproject["tool"]["setuptools"]["package-data"]["foreman_ai_hq"] == [
        "templates/*.html",
        "defaults/*.yaml",
        "data/*.json",
        "orchestrator/pi/profile/*.json",
        "orchestrator/pi/bridge/package.json",
        "orchestrator/pi/bridge/package-lock.json",
        "static/react/*",
        "static/react/assets/*",
    ]


def test_readme_documents_portal_first_operator_flow():
    readme = (ROOT / "README.md").read_text()
    operator_install = readme.split("For contributors working from a checkout", 1)[0]

    assert "Foreman AI HQ" in readme
    assert "pipx install" in readme
    assert "foremanctl init" in readme
    assert "created or migrated by `foremanctl init`" in readme
    assert "uv run foremanctl init" not in operator_install
    assert "http://localhost:8000/" in readme
    assert "Default loopback `foremanctl serve` opens the local Portal without a login token" in readme
    assert "sign in through `/login`" in readme
    assert "foremanctl check" in readme
    removed_command = "seed" + "-demo"
    assert f"foremanctl {removed_command}" not in readme
    assert "docker-compose up" not in readme
    assert "Docker path" not in readme
    assert "uv run --extra test pytest" in readme
    assert "provider" in readme.lower()
    assert "### With a Markdown file" in readme
    assert "upload the file" in readme
    assert "Task Breakdown Agent applies the Task Slicing Policy" in readme
    assert "final Acceptance Verification checks the original Markdown contract" in readme
    assert "compact objective, boundaries, proof command, dependencies, likely entry points, and execution mode" in readme
    assert "docs/assets/screenshots/dashboard-overview.png" in readme
    assert "docs/assets/screenshots/project-board-review-workflow.png" in readme
    assert "docs/assets/screenshots/worker-adapter-setup.png" in readme
    assert "docs/assets/screenshots/sessions-token-ledger.png" in readme
    assert "environment variables" in readme.lower()
    assert "FOREMAN_AI_HQ_CONTROL_API_KEY" in readme
    assert "proxy_governed" not in readme
    assert "proxy-governed" not in readme.lower()
    assert "Harness Proxy" not in readme


def test_install_docs_separate_operator_installs_from_contributor_uv_run():
    readme = (ROOT / "README.md").read_text()
    install_doc = (ROOT / "docs" / "INSTALL.md").read_text()
    getting_started = (ROOT / "docs" / "GETTING_STARTED.md").read_text()

    assert 'pipx install "git+https://github.com/alexdancer/foreman-ai-hq.git"' in install_doc
    assert "pipx install foreman-ai-hq" in install_doc
    assert "curl -fsSL https://raw.githubusercontent.com/alexdancer/foreman-ai-hq/main/install.sh | sh" in install_doc
    assert "## Updating Foreman AI HQ" in install_doc
    assert 'pipx install --force "git+https://github.com/alexdancer/foreman-ai-hq.git"' in install_doc
    assert 'uv tool install --force "git+https://github.com/alexdancer/foreman-ai-hq.git"' in install_doc
    assert "pipx upgrade foreman-ai-hq" in install_doc
    assert "uv tool upgrade foreman-ai-hq" in install_doc
    assert "preserves repo-local `.foreman/` state" in readme
    assert "Homebrew is planned" in install_doc
    assert "not published yet" in install_doc
    assert "uv run foremanctl ...` is a contributor convenience" in install_doc
    assert "foremanctl init" in getting_started
    assert "uv run foremanctl ...` is a contributor convenience" in getting_started
    assert "proxy_governed" not in getting_started
    assert "Harness Proxy" not in getting_started
    assert "assets/screenshots/dashboard-overview.png" in getting_started
    assert "assets/screenshots/project-board-review-workflow.png" in getting_started
    assert "assets/screenshots/control-plane-model-settings.png" in getting_started
    assert "assets/screenshots/worker-adapter-setup.png" in getting_started
    assert "assets/screenshots/token-budget-soft-reset.png" in getting_started
    assert "assets/screenshots/sessions-token-ledger.png" in getting_started
    assert "assets/screenshots/task-breakdown-manual-recovery.png" in getting_started


def test_operator_docs_do_not_advertise_proxy_governed_mode():
    operator_docs = [
        ROOT / "docs" / "GETTING_STARTED.md",
        ROOT / "docs" / "WORKER_ADAPTER_SETUP.md",
        ROOT / "docs" / "SETUP_SUPPORT_CHECKLIST.md",
        ROOT / "docs" / "MCP_AGENT_HARNESS_TODO.md",
    ]

    for path in operator_docs:
        text = path.read_text()
        assert "proxy_governed" not in text, path
        assert "proxy-governed" not in text.lower(), path
        assert "Governed via Harness Proxy" not in text, path


def test_support_checklist_requests_bare_foremanctl_check_and_install_method():
    checklist = (ROOT / "docs" / "SETUP_SUPPORT_CHECKLIST.md").read_text()
    setup_issue = (ROOT / ".github" / "ISSUE_TEMPLATE" / "setup_support.md").read_text()

    assert "foremanctl check" in checklist
    assert "uv run foremanctl check" in checklist
    assert "Install method" in checklist
    assert "Does `command -v foremanctl` succeed?" in setup_issue
    assert "pipx / curl installer / Homebrew / source checkout / Docker / other" in setup_issue
    assert "assets/screenshots/task-breakdown-manual-recovery.png" in checklist


def test_documented_screenshots_exist_and_skip_stale_dashboard_capture():
    readme = (ROOT / "README.md").read_text()
    getting_started = (ROOT / "docs" / "GETTING_STARTED.md").read_text()
    checklist = (ROOT / "docs" / "SETUP_SUPPORT_CHECKLIST.md").read_text()

    for screenshot in [
        "dashboard-overview.png",
        "project-board-review-workflow.png",
        "control-plane-model-settings.png",
        "worker-adapter-setup.png",
        "token-budget-soft-reset.png",
        "sessions-token-ledger.png",
        "task-breakdown-manual-recovery.png",
    ]:
        assert (ROOT / "docs" / "assets" / "screenshots" / screenshot).exists()

    assert not (ROOT / "docs" / "assets" / "screenshots" / "dashboard-stale-recent-alarms.png").exists()
    assert "dashboard-stale-recent-alarms.png" not in readme
    assert "dashboard-stale-recent-alarms.png" not in getting_started
    assert "dashboard-stale-recent-alarms.png" not in checklist


def test_local_readonly_demo_script_supports_loopback_without_portal_token():
    script = (ROOT / "scripts" / "local-opencode-readonly-demo.sh").read_text()

    assert "before running" not in script
    assert "AUTH_HEADERS=()" in script
    assert "Authorization: Bearer $PORTAL_TOKEN" in script
