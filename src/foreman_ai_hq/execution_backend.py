from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from foreman_ai_hq import db

RELEVANT_DOC_NAMES = ("README.md", "CONTEXT.md", "HARNESS.md", "AGENTS.md", "CLAUDE.md")
READ_ONLY_PROOF_DESCRIPTION = (
    "Read-only proof: inspect the connected repository and produce a concise session report with "
    "language, test command, run command, top-level structure, and relevant docs. Do not modify files."
)


@dataclass(frozen=True)
class ProjectConnectionResult:
    project: dict[str, Any] | None
    error: str | None = None


class LocalExecutionBackend:
    id = "local_runner"
    name = "Local Runner"

    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)

    def status(self) -> dict[str, Any]:
        return db.upsert_execution_backend_status(
            self.database_path,
            self.id,
            name=self.name,
            online=True,
            details={"mode": "in_process"},
        )

    def connect_project(self, root_path: Path | str) -> ProjectConnectionResult:
        validation_error = validate_local_project_path(root_path)
        if validation_error:
            return ProjectConnectionResult(None, validation_error)

        profile = detect_project_profile(root_path)
        capability = build_project_capability(
            self.database_path,
            profile=profile,
            backend_online=True,
        )
        project = db.upsert_connected_project(
            self.database_path,
            name=profile["name"],
            root_path=profile["root_path"],
            profile=profile,
            capability=capability,
            backend_id=self.id,
        )
        self.status()
        return ProjectConnectionResult(project)

    def project_capability(self, project: dict[str, Any]) -> dict[str, Any]:
        status = self.status()
        return build_project_capability(
            self.database_path,
            profile=project.get("profile", {}),
            backend_online=bool(status.get("online")),
        )

    def create_read_only_proof_task(self, project: dict[str, Any]) -> dict[str, Any]:
        profile = project.get("profile", {})
        adapter = db.get_worker_adapter(self.database_path, "opencode") or {}
        supported_models = adapter.get("supported_models") or ["opencode/gpt-5.1"]
        # A proof task validates adapter/project wiring without authorizing file edits.
        return db.create_task(
            self.database_path,
            description=READ_ONLY_PROOF_DESCRIPTION,
            status="Estimated",
            estimate_tokens=1500,
            recommended_model=supported_models[0],
            metadata={
                "task_kind": "acceptance_verification",
                "read_only_proof": True,
                "connected_project_id": project["id"],
                "project_root_path": project["root_path"],
                "project_profile": profile,
            },
        )


def validate_local_project_path(root_path: Path | str) -> str | None:
    path = Path(root_path).expanduser()
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError:
        return "Local project path does not exist."
    except OSError as exc:
        return f"Local project path cannot be read: {exc.strerror or type(exc).__name__}."
    if not resolved.is_dir():
        return "Local project path must be a directory."
    return None


def detect_project_profile(root_path: Path | str) -> dict[str, Any]:
    root = Path(root_path).expanduser().resolve()
    top_level_entries = sorted(child.name for child in root.iterdir() if not child.name.startswith("."))
    top_level_folders = sorted(child.name for child in root.iterdir() if child.is_dir() and not child.name.startswith("."))
    docs = _relevant_docs(root)
    files = {child.name for child in root.iterdir() if child.is_file()}
    suggested_test_command = _suggest_test_command(files)
    suggested_base_branch = _suggest_base_branch(root)

    return {
        "name": root.name,
        "root_path": str(root),
        "git_branch": _git_branch(root),
        "language_hints": _language_hints(root, files),
        "framework_hints": _framework_hints(root, files),
        "package_manager_hints": _package_manager_hints(files),
        # Detection is a suggestion; the operator must confirm before it runs.
        "test_command_suggested": suggested_test_command,
        "test_command_confirmed": False,
        "test_command": None,
        "base_branch_suggested": suggested_base_branch,
        "base_branch_confirmed": False,
        "base_branch": suggested_base_branch if suggested_base_branch else None,
        "run_command": _detect_run_command(files),
        "top_level_folders": top_level_folders,
        "top_level_entries": top_level_entries[:50],
        "relevant_docs": docs,
    }


def build_project_capability(
    database_path: Path | str,
    *,
    profile: dict[str, Any],
    backend_online: bool,
) -> dict[str, Any]:
    reasons: list[str] = []
    root_path = profile.get("root_path")
    path_error = validate_local_project_path(root_path) if root_path else "Connected project path is missing."
    if path_error:
        reasons.append(path_error)
    if not backend_online:
        reasons.append("Local Runner backend is offline.")
    if not db.has_launchable_worker_adapter(database_path):
        reasons.append("No verified launchable Worker Adapter is available.")

    # Analysis remains available when the path is valid but launch prerequisites are missing.
    if not path_error and backend_online and not reasons:
        state = "launch_ready"
        label = "Launch-ready via Local Runner"
    elif not path_error:
        state = "analysis_ready"
        label = "Analysis-ready"
    else:
        state = "blocked"
        label = "Blocked"
    return {
        "state": state,
        "label": label,
        "backend": "local_runner",
        "reasons": reasons,
        "can_launch": state == "launch_ready",
        "can_analyze": state in {"analysis_ready", "launch_ready"},
    }



def _git_branch(root: Path) -> str | None:
    if not (root / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    branch = result.stdout.strip()
    return branch or None


def _language_hints(root: Path, files: set[str]) -> list[str]:
    hints: list[str] = []
    if "pyproject.toml" in files or "requirements.txt" in files:
        hints.append("python")
    if "package.json" in files:
        hints.append("javascript")
    if "Cargo.toml" in files:
        hints.append("rust")
    if "go.mod" in files:
        hints.append("go")
    if any((root / name).exists() for name in ("Dockerfile", "docker-compose.yml", "compose.yaml")):
        hints.append("docker")
    return hints


def _framework_hints(root: Path, files: set[str]) -> list[str]:
    hints: list[str] = []
    if "pyproject.toml" in files:
        # Bound manifest reads; hints should never require loading a whole generated file.
        pyproject = (root / "pyproject.toml").read_text(errors="ignore")[:20_000].lower()
        for name in ("fastapi", "django", "flask", "pytest"):
            if name in pyproject:
                hints.append(name)
    if "package.json" in files:
        package_json = (root / "package.json").read_text(errors="ignore")[:20_000].lower()
        for name in ("react", "next", "vite", "express"):
            if name in package_json:
                hints.append(name)
    return hints


def _package_manager_hints(files: set[str]) -> list[str]:
    hints: list[str] = []
    for marker, hint in (
        ("uv.lock", "uv"),
        ("poetry.lock", "poetry"),
        ("pyproject.toml", "pip"),
        ("package-lock.json", "npm"),
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("Cargo.lock", "cargo"),
        ("go.mod", "go"),
    ):
        if marker in files and hint not in hints:
            hints.append(hint)
    return hints


def _suggest_test_command(files: set[str]) -> str | None:
    if "pyproject.toml" in files or "pytest.ini" in files:
        return "pytest"
    if "package.json" in files:
        return "npm test"
    if "Cargo.toml" in files:
        return "cargo test"
    if "go.mod" in files:
        return "go test ./..."
    return None


def _suggest_base_branch(root: Path) -> str | None:
    if not (root / ".git").exists():
        return None
    # Prefer the default branch reported by the first configured remote.
    result = subprocess.run(
        ["git", "remote", "show", "origin"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    for line in result.stdout.splitlines():
        if "HEAD branch" in line:
            branch = line.split(":", 1)[-1].strip()
            if branch:
                return branch
    # Fall back to the current checked-out branch.
    return _git_branch(root)


def _detect_run_command(files: set[str]) -> str | None:
    if "pyproject.toml" in files:
        return "python -m foreman_ai_hq"
    if "package.json" in files:
        return "npm run dev"
    if "Cargo.toml" in files:
        return "cargo run"
    return None


def _relevant_docs(root: Path) -> list[str]:
    docs: list[str] = []
    for name in RELEVANT_DOC_NAMES:
        if (root / name).is_file():
            docs.append(name)
    docs_dir = root / "docs"
    if docs_dir.is_dir():
        for name in ("HARNESS.md", "README.md"):
            if (docs_dir / name).is_file():
                docs.append(f"docs/{name}")
    return docs
