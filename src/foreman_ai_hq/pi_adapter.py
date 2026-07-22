from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from foreman_ai_hq import db

DEFAULT_PI_PROVIDER = "harness"
DEFAULT_PI_MODEL = "harness/proxy"
PI_HARNESS_API_KEY_ENV = "PI_HARNESS_API_KEY"
DEFAULT_PROFILE_DIR = Path(__file__).resolve().parent / "orchestrator" / "pi" / "profile"


def _default_proxy_url() -> str:
    return f"http://127.0.0.1:{os.environ.get('PORT', '8000')}/v1"


def launch_pi_once(
    database_path: Path | str,
    prompt: str,
    *,
    proxy_url: str | None = None,
    profile_dir: Path | str | None = None,
    provider: str = DEFAULT_PI_PROVIDER,
    model: str = DEFAULT_PI_MODEL,
    timeout: float = 60,
) -> tuple[dict[str, Any], subprocess.CompletedProcess[str]]:
    """Mint a planning session and run pi once through the Harness Proxy.

    The tracked pi profile is copied to a temporary agent directory so pi's
    runtime files (sessions, trust, settings) are never written into the repo.
    The planning bearer is injected as the provider API key via a per-process
    environment variable; it is never written to the tracked profile.
    """
    session, bearer_key = db.create_planning_session(
        database_path,
        task_description="pi orchestrator launch",
        model=model,
    )
    selected_proxy_url = proxy_url or _default_proxy_url()
    selected_profile_dir = Path(profile_dir) if profile_dir else DEFAULT_PROFILE_DIR

    source_models = selected_profile_dir / "models.json"
    if not source_models.is_file():
        raise FileNotFoundError(f"pi orchestrator profile not found: {source_models}")

    with tempfile.TemporaryDirectory(prefix="pi-orchestrator-") as tmpdir:
        agent_dir = Path(tmpdir) / "agent"
        agent_dir.mkdir()
        # Keep runtime state out of the tracked profile.
        (Path(tmpdir) / "sessions").mkdir()

        config = json.loads(source_models.read_text(encoding="utf-8"))
        provider_config = config.get("providers", {}).get(provider)
        if provider_config is None:
            raise KeyError(f"provider '{provider}' not found in pi profile")
        provider_config["baseUrl"] = selected_proxy_url

        (agent_dir / "models.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )

        env = {
            **os.environ,
            "PI_CODING_AGENT_DIR": str(agent_dir),
            "PI_CODING_AGENT_SESSION_DIR": str(Path(tmpdir) / "sessions"),
            PI_HARNESS_API_KEY_ENV: bearer_key,
        }
        command = [
            "pi",
            "-p",
            "--offline",
            "--provider",
            provider,
            "--model",
            model,
            prompt,
        ]
        result = subprocess.run(
            command,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    return session, result
