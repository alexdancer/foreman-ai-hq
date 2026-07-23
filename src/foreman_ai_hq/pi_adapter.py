from __future__ import annotations

import contextlib
import json
import os
import queue
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Iterator

from foreman_ai_hq import db

DEFAULT_PI_PROVIDER = "harness"
DEFAULT_PI_MODEL = "harness/proxy"
PI_HARNESS_API_KEY_ENV = "PI_HARNESS_API_KEY"
PI_ACP_PI_COMMAND_ENV = "PI_ACP_PI_COMMAND"
PI_ACP_PERSONA_PATH_ENV = "PI_ACP_PERSONA_PATH"
PI_ACP_ALLOWED_TOOLS_ENV = "PI_ACP_ALLOWED_TOOLS"

PI_ORCHESTRATOR_ALLOWED_TOOLS = ("read", "grep", "find", "ls")
DEFAULT_PROFILE_DIR = Path(__file__).resolve().parent / "orchestrator" / "pi" / "profile"
DEFAULT_BRIDGE_DIR = Path(__file__).resolve().parent / "orchestrator" / "pi" / "bridge"
PI_ACP_PACKAGE = "pi-acp"


def _persona_path(profile_dir: Path) -> Path:
    """Return the path to the git-tracked orchestrator persona."""
    return profile_dir / "orchestrator.md"


def _write_pi_acp_wrapper(tmpdir: Path, persona_path: Path) -> Path:
    """Write a generated POSIX wrapper that execs pi with the persona and tool allowlist appended.

    The wrapper is content-free of policy text; it reads the persona path and
    comma-joined allowlist from environment variables set by the adapter.
    """
    wrapper = tmpdir / "pi-wrapper.sh"
    wrapper.write_text(
        '#!/bin/sh\nexec pi --append-system-prompt "${PI_ACP_PERSONA_PATH}" --tools "${PI_ACP_ALLOWED_TOOLS}" "$@"\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    return wrapper


def _default_proxy_url() -> str:
    return f"http://127.0.0.1:{os.environ.get('PORT', '8000')}/v1"


def _pi_acp_command(bridge_dir: Path) -> list[str]:
    """Return the Node command for the pi ACP bridge, preferring the local install."""
    package_json = bridge_dir / "package.json"
    version = "0.0.31"
    if package_json.is_file():
        try:
            version = json.loads(package_json.read_text(encoding="utf-8")).get("dependencies", {}).get(PI_ACP_PACKAGE, version)
        except (json.JSONDecodeError, OSError):
            pass
    local_main = bridge_dir / "node_modules" / PI_ACP_PACKAGE / "dist" / "index.js"
    if local_main.is_file():
        return ["node", str(local_main)]
    return ["npx", "-y", f"{PI_ACP_PACKAGE}@{version}"]


def _prepare_pi_env(
    bearer_key: str,
    proxy_url: str,
    profile_dir: Path,
    provider: str,
    agent_dir: Path,
    sessions_dir: Path,
) -> dict[str, str]:
    """Build the environment for a pi launch with the bearer injected as the provider API key."""
    source_models = profile_dir / "models.json"
    if not source_models.is_file():
        raise FileNotFoundError(f"pi orchestrator profile not found: {source_models}")

    config = json.loads(source_models.read_text(encoding="utf-8"))
    provider_config = config.get("providers", {}).get(provider)
    if provider_config is None:
        raise KeyError(f"provider '{provider}' not found in pi profile")
    provider_config["baseUrl"] = proxy_url

    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "models.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    sessions_dir.mkdir(parents=True, exist_ok=True)

    return {
        **os.environ,
        "PI_CODING_AGENT_DIR": str(agent_dir),
        "PI_CODING_AGENT_SESSION_DIR": str(sessions_dir),
        PI_HARNESS_API_KEY_ENV: bearer_key,
    }


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

    The tracked pi profile is read, its provider baseUrl is rewritten to the
    running proxy URL, and the result is written into a temporary agent directory
    so pi's runtime files (sessions, trust, settings) never land in the repo.
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

    with tempfile.TemporaryDirectory(prefix="pi-orchestrator-") as tmpdir:
        agent_dir = Path(tmpdir) / "agent"
        sessions_dir = Path(tmpdir) / "sessions"
        env = _prepare_pi_env(
            bearer_key,
            selected_proxy_url,
            selected_profile_dir,
            provider,
            agent_dir,
            sessions_dir,
        )
        persona_path = _persona_path(selected_profile_dir)
        command = [
            "pi",
            "-p",
            "--offline",
            "--append-system-prompt",
            str(persona_path),
            "--tools",
            ",".join(PI_ORCHESTRATOR_ALLOWED_TOOLS),
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


class AcpRuntimeError(RuntimeError):
    """Raised when the ACP stdio conversation with pi fails."""


class _AcpJsonRpcTransport:
    """Minimal JSON-RPC 2.0 client over a subprocess stdio pipe.

    pi-acp speaks newline-delimited JSON-RPC over stdin/stdout.  This transport
    sends requests, correlates responses by id, and queues non-response messages
    (notifications such as ``session/update``) for the caller to drain.
    """

    def __init__(self, proc: subprocess.Popen) -> None:
        self.proc = proc
        self._next_id = 1
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._write_lock = threading.Lock()

    def _read_loop(self) -> None:
        stdout = self.proc.stdout
        if stdout is None:
            return
        for line in stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            self._queue.put(msg)

    def _send_frame(self, payload: dict[str, Any]) -> None:
        if self.proc.stdin is None:
            raise AcpRuntimeError("ACP bridge stdin is closed")
        with self._write_lock:
            self.proc.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
            self.proc.stdin.flush()

    def _write(self, method: str, params: dict[str, Any]) -> int:
        req_id = self._next_id
        self._next_id += 1
        payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        self._send_frame(payload)
        return req_id

    def notify(self, method: str, params: dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no id, no response)."""
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        self._send_frame(payload)

    def call(
        self, method: str, params: dict[str, Any], *, timeout: float = 30
    ) -> tuple[Any, list[dict[str, Any]]]:
        """Send a JSON-RPC request and return (result, notifications captured before the response)."""
        req_id = self._write(method, params)
        notifications: list[dict[str, Any]] = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                msg = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if msg.get("id") == req_id:
                if "error" in msg:
                    raise AcpRuntimeError(f"ACP {method} failed: {msg['error']}")
                return msg.get("result"), notifications
            notifications.append(msg)
        raise AcpRuntimeError(f"ACP {method} timed out")

    def drain(self, *, timeout: float = 0.5) -> list[dict[str, Any]]:
        """Drain remaining notifications, waiting up to ``timeout`` for the queue to empty."""
        items: list[dict[str, Any]] = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                items.append(self._queue.get(timeout=0.1))
            except queue.Empty:
                break
        return items


def _extract_text_chunks(notifications: list[dict[str, Any]]) -> str:
    """Concatenate ``agent_message_chunk`` text notifications."""
    chunks: list[str] = []
    for msg in notifications:
        update = msg.get("params", {}).get("update", {})
        if update.get("sessionUpdate") == "agent_message_chunk":
            content = update.get("content", {})
            if content.get("type") == "text" and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "".join(chunks)


class PiConversation:
    """Handle for an active ACP pi conversation."""

    def __init__(
        self,
        session: dict[str, Any],
        proc: subprocess.Popen,
        transport: _AcpJsonRpcTransport,
        session_id: str,
        default_timeout: float,
    ) -> None:
        self.session = session
        self.proc = proc
        self.responses: list[str] = []
        self._transport = transport
        self._session_id = session_id
        self._default_timeout = default_timeout

    def prompt(self, text: str, *, timeout: float | None = None) -> tuple[str, str]:
        """Drive one turn and return (text, stop_reason)."""
        deadline = timeout if timeout is not None else self._default_timeout
        result, notifications = self._transport.call(
            "session/prompt",
            {"sessionId": self._session_id, "prompt": [{"type": "text", "text": text}]},
            timeout=deadline,
        )
        # Trailing ``agent_message_chunk`` notifications may arrive after the
        # prompt response; give them a moment to land.
        notifications.extend(self._transport.drain(timeout=0.5))
        stop_reason = result.get("stopReason", "end_turn") if isinstance(result, dict) else "end_turn"
        text = _extract_text_chunks(notifications)
        self.responses.append(text)
        return text, stop_reason

    def cancel(self) -> None:
        """Send a ``session/cancel`` notification for the active session."""
        self._transport.notify("session/cancel", {"sessionId": self._session_id})


def _terminate_process_group(proc: subprocess.Popen) -> None:
    """Terminate the bridge and any child processes it spawned (e.g. pi)."""
    if proc.poll() is not None:
        return
    try:
        if hasattr(os, "killpg"):
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
        else:
            proc.terminate()
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            if hasattr(os, "killpg"):
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            else:
                proc.kill()
        except ProcessLookupError:
            pass
        proc.wait(timeout=2)
    finally:
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass


@contextlib.contextmanager
def launch_pi_conversation(
    database_path: Path | str,
    prompts: list[str] | None = None,
    *,
    proxy_url: str | None = None,
    profile_dir: Path | str | None = None,
    provider: str = DEFAULT_PI_PROVIDER,
    model: str = DEFAULT_PI_MODEL,
    cwd: Path | str | None = None,
    timeout: float = 60,
) -> Iterator[PiConversation]:
    """Mint one planning session and yield a handle for an ACP pi conversation.

    The planning bearer is injected as the provider API key for the subprocess only;
    it is never written to the tracked profile.  The yielded ``PiConversation`` handle
    exposes ``prompt(text)``, ``cancel()``, ``session``, ``proc``, and ``responses``.
    If ``prompts`` is provided, the helper drives them eagerly and the collected
    responses are already on the handle when it is yielded.  The context manager
    guarantees the subprocess is terminated and stdio is closed on exit or error.
    """
    session, bearer_key = db.create_planning_session(
        database_path,
        task_description="pi orchestrator ACP conversation",
        model=model,
    )
    selected_proxy_url = proxy_url or _default_proxy_url()
    selected_profile_dir = Path(profile_dir) if profile_dir else DEFAULT_PROFILE_DIR
    selected_cwd = Path(cwd) if cwd else Path.cwd()
    bridge_dir = DEFAULT_BRIDGE_DIR

    with tempfile.TemporaryDirectory(prefix="pi-orchestrator-acp-") as tmpdir:
        agent_dir = Path(tmpdir) / "agent"
        sessions_dir = Path(tmpdir) / "sessions"
        env = _prepare_pi_env(
            bearer_key,
            selected_proxy_url,
            selected_profile_dir,
            provider,
            agent_dir,
            sessions_dir,
        )
        persona_path = _persona_path(selected_profile_dir)
        wrapper = _write_pi_acp_wrapper(Path(tmpdir), persona_path)
        env[PI_ACP_PI_COMMAND_ENV] = str(wrapper)
        env[PI_ACP_PERSONA_PATH_ENV] = str(persona_path)
        env[PI_ACP_ALLOWED_TOOLS_ENV] = ",".join(PI_ORCHESTRATOR_ALLOWED_TOOLS)

        command = _pi_acp_command(bridge_dir)
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=str(bridge_dir),
            start_new_session=True,
        )
        try:
            transport = _AcpJsonRpcTransport(proc)
            transport.call(
                "initialize",
                {
                    "protocolVersion": 1,
                    "clientInfo": {"name": "foreman-ai-hq", "version": "0.1.0"},
                },
                timeout=timeout,
            )
            new_result, _ = transport.call(
                "session/new",
                {"cwd": str(selected_cwd), "mcpServers": []},
                timeout=timeout,
            )
            session_id = new_result["sessionId"]
            # Discard pi startup info / available-commands notifications so they
            # do not mix into the first prompt response.
            transport.drain(timeout=1.0)

            conv = PiConversation(session, proc, transport, session_id, timeout)
            if prompts:
                for prompt in prompts:
                    conv.prompt(prompt)

            yield conv
        finally:
            _terminate_process_group(proc)
