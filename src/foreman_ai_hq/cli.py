from __future__ import annotations

import argparse
import asyncio
import ipaddress
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

import uvicorn

from foreman_ai_hq import db
from foreman_ai_hq.adapter_readiness import evaluate_adapter_readiness
from foreman_ai_hq.demo_seed import seed_demo_sandbox, seed_demo_tasks
from foreman_ai_hq.pi_adapter import resolve_orchestrator_model
from foreman_ai_hq.operator_config import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_SECRETS_PATH,
    CONTROL_API_KEY_PLACEHOLDER,
    load_operator_config,
    load_operator_secrets_env,
    secret_env_names,
    write_default_guardrails_file,
    write_default_secrets_env,
    write_default_operator_config,
)
from foreman_ai_hq.settings import Settings

APP_REF = "foreman_ai_hq.app:create_app"


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    if raw_argv and raw_argv[0] == "demo-worker":
        # The synthetic Worker owns its own flags (--model, --workdir). Handing
        # them to this parser first would let the shared options shadow them.
        from foreman_ai_hq.demo_worker import main as demo_worker_main

        return demo_worker_main(raw_argv[1:])

    parser = _build_parser()
    args = parser.parse_args(raw_argv)
    command = args.command or "serve"

    if command == "init":
        cwd = Path.cwd()
        # Initialize at the Git root so generated config and local state share one project home.
        init_root, git_exclude_path = _resolve_init_root(cwd)
        config_arg = getattr(args, "config_path", None)
        secrets_arg = getattr(args, "secrets_path", None)
        config_path = Path(config_arg) if config_arg else init_root / DEFAULT_CONFIG_PATH
        config = write_default_operator_config(config_path)
        secrets_path = Path(secrets_arg) if secrets_arg else init_root / DEFAULT_SECRETS_PATH
        write_default_secrets_env(config, secrets_path)
        guardrails_path = write_default_guardrails_file(config, base_dir=init_root)
        database_path = _resolve_local_path(config.get("database_path") or ".foreman/harness.db", init_root)
        db.init_db(database_path)
        _protect_local_state(init_root, git_exclude_path)
        print(f"Initialized root {init_root}")
        print(f"Wrote {_display_path(config_path, cwd)}")
        print(f"Wrote {_display_path(secrets_path, cwd)}")
        print(f"Wrote {_display_path(guardrails_path, cwd)}")
        print(f"Wrote {_display_path(database_path, cwd)}")
        print("Start with foremanctl serve, open http://localhost:8000/, then add the control-plane API key in /settings/control-plane.")
        portal_token_env, control_key_env = secret_env_names(config)
        secrets_display = _display_path(secrets_path, cwd)
        print(f"Portal token for shared access: set {portal_token_env} in {secrets_display}")
        print(
            f"Control-plane API key: configure {control_key_env} in /settings/control-plane; "
            f"{secrets_display} or shell env remain supported alternatives."
        )
        return 0

    if command == "serve":
        config, _, _, _ = _load_default_operator_state()
        database_path = _arg_path(args, "serve_database_path", "global_database_path")
        guardrails_path = _arg_path(args, "serve_guardrails_path", "global_guardrails_path")
        host = getattr(args, "host", None) or str(config.get("host") or "127.0.0.1")
        _set_path_env("TOKEN_TRACKER_DATABASE_PATH", database_path)
        _set_path_env("TOKEN_TRACKER_GUARDRAILS_PATH", guardrails_path)
        _set_env_if_missing("TOKEN_TRACKER_DATABASE_PATH", config.get("database_path"))
        _set_env_if_missing("TOKEN_TRACKER_GUARDRAILS_PATH", config.get("guardrails_path"))
        _set_env_if_missing(
            "FOREMAN_AI_HQ_CONTROL_PROVIDER",
            config.get("control_plane_provider"),
            aliases=("TOKEN_TRACKER_CONTROL_PLANE_PROVIDER",),
        )
        # The legacy aliases went with the resolution chain; only this name is read.
        _set_env_if_missing(
            "FOREMAN_AI_HQ_ORCHESTRATOR_MODEL",
            config.get("orchestrator_model") or config.get("control_plane_model"),
        )
        _set_env_if_missing(
            "FOREMAN_AI_HQ_CONTROL_API_KEY_ENV",
            config.get("control_plane_api_key_env"),
            aliases=("TOKEN_TRACKER_CONTROL_PLANE_API_KEY_ENV",),
        )
        _set_env_if_missing("TOKEN_TRACKER_PORTAL_TOKEN_ENV", config.get("portal_token_env"))
        _set_env_if_missing("TOKEN_TRACKER_PORTAL_AUTH_REQUIRED", config.get("portal_auth_required"))
        if os.getenv("TOKEN_TRACKER_PORTAL_AUTH_REQUIRED") is None:
            uses_proxy_headers = getattr(args, "proxy_headers", False)
            local_only_bind = _is_loopback_bind_host(host) and not uses_proxy_headers
            # Loopback serves default to frictionless access; proxied/non-loopback binds require auth.
            os.environ["TOKEN_TRACKER_PORTAL_AUTH_REQUIRED"] = "0" if local_only_bind else "1"
        if getattr(args, "local_runner", False):
            # CLI opt-in wins for this process without rewriting operator config.
            os.environ["TOKEN_TRACKER_LOCAL_RUNNER"] = "1"
        elif "TOKEN_TRACKER_LOCAL_RUNNER" not in os.environ and _config_bool(config, "local_runner_enabled"):
            os.environ["TOKEN_TRACKER_LOCAL_RUNNER"] = "1"
        uvicorn.run(
            APP_REF,
            host=host,
            port=getattr(args, "port", None) or int(config.get("port") or 8000),
            proxy_headers=getattr(args, "proxy_headers", False),
            factory=True,
            env_file=None,
        )
        return 0

    if command == "check":
        return _check_operator_setup()

    if command == "seed-demo":
        database_path = _arg_path(args, "seed_database_path", "global_database_path")
        db_path = Path(database_path or os.getenv("TOKEN_TRACKER_DATABASE_PATH", "harness.db"))
        if not getattr(args, "with_project", False):
            inserted = seed_demo_tasks(db_path)
            print(f"seed-demo inserted {len(inserted)} synthetic DEMO tasks into {db_path}")
            print("Tasks are board-visible but not launchable. Re-run with --with-project to connect a project.")
            return 0
        project_root = getattr(args, "project_root", None) or Path(db_path).resolve().parent / "demo-project"
        sandbox = seed_demo_sandbox(db_path, project_root)
        project = sandbox["project"]
        print(f"seed-demo inserted {len(sandbox['inserted_tasks'])} synthetic DEMO tasks into {db_path}")
        print(f"seed-demo connected project {project['id']} at {sandbox['project_root']}")
        print(f"Open the Pipeline: /projects/{project['id']}")
        return 0

    parser.error(f"unknown command: {command}")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="foremanctl",
        description="Foreman AI HQ operator command. Bare foremanctl starts the portal server.",
    )
    parser.add_argument(
        "--database-path",
        dest="global_database_path",
        default=None,
        help="SQLite database path. Overrides TOKEN_TRACKER_DATABASE_PATH.",
    )
    parser.add_argument(
        "--guardrails-path",
        dest="global_guardrails_path",
        default=None,
        help="Guardrails YAML path. Overrides TOKEN_TRACKER_GUARDRAILS_PATH.",
    )
    subparsers = parser.add_subparsers(dest="command")

    init = subparsers.add_parser("init", help="Create local non-secret Foreman AI HQ operator config.")
    init.add_argument(
        "--config-path",
        default=None,
        help="Operator config path to write. Defaults to .foreman/config.toml.",
    )
    init.add_argument(
        "--secrets-path",
        default=None,
        help="Local secrets env path to write. Defaults to .foreman/secrets.env.",
    )

    serve = subparsers.add_parser("serve", help="Run Foreman AI HQ portal/API server.")
    serve.add_argument("--host", default=None, help="Bind host.")
    serve.add_argument("--port", type=int, default=None, help="Bind port.")
    serve.add_argument(
        "--proxy-headers",
        action="store_true",
        default=False,
        help="Trust X-Forwarded-* headers from reverse proxy.",
    )
    serve.add_argument(
        "--database-path",
        dest="serve_database_path",
        default=None,
        help="SQLite database path. Overrides TOKEN_TRACKER_DATABASE_PATH.",
    )
    serve.add_argument(
        "--guardrails-path",
        dest="serve_guardrails_path",
        default=None,
        help="Guardrails YAML path. Overrides TOKEN_TRACKER_GUARDRAILS_PATH.",
    )
    serve.add_argument(
        "--local-runner",
        action="store_true",
        default=False,
        help="Enable the in-process Local Runner Execution Backend.",
    )

    subparsers.add_parser("check", help="Check local operator setup readiness.")

    seed_demo = subparsers.add_parser("seed-demo", help="Insert synthetic DEMO snip tasks.")
    seed_demo.add_argument(
        "--database-path",
        dest="seed_database_path",
        default=None,
        help="SQLite database path. Overrides TOKEN_TRACKER_DATABASE_PATH.",
    )
    seed_demo.add_argument(
        "--with-project",
        action="store_true",
        default=False,
        help="Also create a synthetic git repo, connect it as a project, and bind the tasks so they are launchable.",
    )
    seed_demo.add_argument(
        "--project-root",
        default=None,
        help="Where to create the synthetic demo repo. Defaults to demo-project/ beside the database.",
    )

    # Registered for `--help` discoverability only; main() dispatches it before
    # parsing so the synthetic Worker keeps its own flags.
    subparsers.add_parser(
        "demo-worker",
        add_help=False,
        help="Synthetic Worker that streams Claude stream-json events. Invoked by the seeded demo adapter.",
    )

    return parser


def _check_operator_setup() -> int:
    config, secrets, config_path, secrets_path = _load_default_operator_state()
    _set_env_if_missing("TOKEN_TRACKER_PORTAL_AUTH_REQUIRED", config.get("portal_auth_required"))
    if os.getenv("TOKEN_TRACKER_PORTAL_AUTH_REQUIRED") is None:
        host = str(config.get("host") or "127.0.0.1")
        os.environ["TOKEN_TRACKER_PORTAL_AUTH_REQUIRED"] = "0" if _is_loopback_bind_host(host) else "1"
    settings = Settings(operator_config=config)
    cwd = Path.cwd()
    hard_fail = False

    if config:
        print(f"PASS config loaded {_display_path(config_path, cwd)}")
    else:
        print(f"WARN config missing {_display_path(config_path, cwd)}; using env/defaults")
    if secrets:
        print(f"PASS secrets loaded {_display_path(secrets_path, cwd)}")
    else:
        print(f"WARN secrets missing {_display_path(secrets_path, cwd)}; using shell env only")

    if settings.portal_auth_required:
        if os.getenv(settings.portal_token_env):
            print(f"PASS portal token env {settings.portal_token_env} present")
        else:
            print(f"FAIL portal token env {settings.portal_token_env} missing")
            hard_fail = True
    else:
        print(f"PASS portal auth disabled for local-only access; {settings.portal_token_env} not required")

    for env_name, label in [
        (settings.control_plane_api_key_env, "control-plane API key"),
    ]:
        if os.getenv(env_name):
            print(f"PASS {label} env {env_name} present")
        else:
            if label == "control-plane API key":
                print(
                    f"FAIL {label} env {env_name} missing; add it in /settings/control-plane, "
                    ".foreman/secrets.env, or the shell environment. This does not configure native "
                    "Worker CLI auth. Native Worker CLI auth is separate, and so is the Orchestrator, "
                    "which authenticates through pi."
                )
            else:
                print(f"FAIL {label} env {env_name} missing")
            hard_fail = True

    # Readiness is pi's inventory, not an API key: the Orchestrator runs on pi's own
    # provider auth, so an exported control-plane key proves nothing about it.
    resolved_orchestrator = resolve_orchestrator_model(
        settings.database_path, settings.orchestrator_model
    )
    if resolved_orchestrator:
        print(f"PASS orchestrator model {resolved_orchestrator} configured from pi inventory")
    elif settings.orchestrator_model:
        print(
            f"FAIL orchestrator model {settings.orchestrator_model} is not in pi's discovered "
            "inventory; refresh the inventory in /settings/control-plane and choose a model."
        )
        hard_fail = True
    else:
        print(
            "FAIL orchestrator model not configured; run `pi /login`, then choose a model in "
            "/settings/control-plane."
        )
        hard_fail = True

    print(("PASS" if settings.local_runner_enabled else "WARN") + " local runner " + ("enabled" if settings.local_runner_enabled else "disabled"))
    _print_worker_readiness(settings.database_path)
    return 1 if hard_fail else 0


def _print_worker_readiness(database_path: Path) -> None:
    if not database_path.exists():
        print(f"WARN Worker adapters unchecked: database {database_path} does not exist yet")
        return
    try:
        adapters = db.list_worker_adapters(database_path)
    except Exception as exc:
        print(f"WARN Worker adapters unchecked: {type(exc).__name__}")
        return
    if not adapters:
        print("WARN no Worker adapters configured")
        return
    for adapter in adapters:
        readiness = evaluate_adapter_readiness(adapter)
        identity = f"{adapter.get('id')} ({adapter.get('kind')})"
        mode = readiness.tracking.mode
        if readiness.ui_launchable:
            print(f"PASS Worker adapter {identity} launch-ready via {mode}")
        elif mode == "observed_only":
            print(f"WARN Worker adapter {identity} observed_only is diagnostic-only and not normal board-launchable")
        else:
            print(f"WARN Worker adapter {identity} not launch-ready: {'; '.join(readiness.reasons)}")


def _arg_path(args: argparse.Namespace, primary: str, fallback: str) -> str | None:
    return getattr(args, primary, None) or getattr(args, fallback, None)


def _load_default_operator_state() -> tuple[dict[str, object], dict[str, str], Path, Path]:
    init_root, _ = _resolve_init_root(Path.cwd())
    config_path = init_root / DEFAULT_CONFIG_PATH
    secrets_path = init_root / DEFAULT_SECRETS_PATH
    config = load_operator_config(config_path)
    if config:
        # Config paths are repo-relative on disk; runtime Settings expects concrete paths.
        config = _resolve_config_paths(config, init_root)
    secrets = load_operator_secrets_env(config, secrets_path)
    return config, secrets, config_path, secrets_path


def _resolve_config_paths(config: dict[str, object], init_root: Path) -> dict[str, object]:
    resolved = dict(config)
    for key in ["database_path", "guardrails_path"]:
        if resolved.get(key):
            resolved[key] = str(_resolve_local_path(resolved[key], init_root))
    return resolved


def _resolve_init_root(cwd: Path) -> tuple[Path, Path | None]:
    git_root = _git_path(cwd, "--show-toplevel")
    if git_root is None:
        return cwd, None
    exclude_path = _git_path(git_root, "--git-path", "info/exclude")
    if exclude_path is not None and not exclude_path.is_absolute():
        exclude_path = git_root / exclude_path
    return git_root, exclude_path


def _git_path(cwd: Path, *args: str) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return Path(value) if value else None


def _resolve_local_path(value: object, base_dir: Path) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else base_dir / path


def _protect_local_state(init_root: Path, git_exclude_path: Path | None) -> None:
    if git_exclude_path is None:
        # Outside Git, protect generated .foreman files with a local ignore file.
        gitignore = init_root / ".foreman" / ".gitignore"
        existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        lines = {line.strip() for line in existing.splitlines()}
        additions = [line for line in ["*", "!.gitignore"] if line not in lines]
        if additions:
            suffix = "" if existing.endswith("\n") or not existing else "\n"
            addition_text = "\n".join(additions)
            gitignore.write_text(f"{existing}{suffix}{addition_text}\n", encoding="utf-8")
        return
    git_exclude_path.parent.mkdir(parents=True, exist_ok=True)
    existing = git_exclude_path.read_text(encoding="utf-8") if git_exclude_path.exists() else ""
    if ".foreman/" not in {line.strip() for line in existing.splitlines()}:
        # In Git repos, keep local state untracked without editing the committed .gitignore.
        suffix = "" if existing.endswith("\n") or not existing else "\n"
        git_exclude_path.write_text(f"{existing}{suffix}.foreman/\n", encoding="utf-8")


def _display_path(path: Path, cwd: Path) -> str:
    try:
        return str(path.relative_to(cwd))
    except ValueError:
        return str(path)


def _set_path_env(name: str, value: str | None) -> None:
    if value:
        os.environ[name] = str(Path(value))


def _set_env_if_missing(name: str, value: object | None, aliases: tuple[str, ...] = ()) -> None:
    if value is not None and os.getenv(name) is None and not any(os.getenv(alias) is not None for alias in aliases):
        os.environ[name] = str(value)


def _config_bool(config: dict[str, object], name: str) -> bool:
    return bool(config.get(name))


def _is_loopback_bind_host(host: str) -> bool:
    normalized = host.strip().lower().strip("[]")
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False
