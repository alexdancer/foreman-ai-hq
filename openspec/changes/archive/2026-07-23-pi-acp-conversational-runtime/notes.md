# pi ACP conversational runtime — discovered wiring notes

pi 0.81.1 does **not** expose ACP directly. It exposes a custom JSON-RPC protocol over stdio via `pi --mode rpc`. The Harness therefore uses the community `pi-acp` Node adapter as a thin ACP↔pi RPC bridge.

## Bridge dependency

- Package: `pi-acp` pinned to `0.0.31`.
- Tracked configuration: `src/foreman_ai_hq/orchestrator/pi/bridge/package.json` + `package-lock.json`.
- `node_modules` is git-ignored and installed at runtime like the pi engine.
- Entry point: `node node_modules/pi-acp/dist/index.js` (or `npx -y pi-acp@0.0.31` as a fallback).

## Spawn wiring

The Python adapter spawns the bridge with:

- `cwd` = the tracked bridge directory (so the local `node_modules` install is used).
- `env` = parent env plus:
  - `PI_CODING_AGENT_DIR` → temporary agent dir containing the rewritten `models.json`.
  - `PI_CODING_AGENT_SESSION_DIR` → temporary sessions dir.
  - `PI_HARNESS_API_KEY` → the per-conversation planning bearer.
- `start_new_session=True` so the whole process group can be terminated on cleanup.

The tracked `models.json` provider profile (`harness`) has its `baseUrl` rewritten to the running Harness Proxy URL at launch. The `apiKey` placeholder is left untouched; the real bearer is supplied only through the environment.

## ACP client shape

pi-acp speaks newline-delimited JSON-RPC 2.0 over stdio. The Python side acts as the ACP client.

Conversation lifecycle:

1. `initialize` — negotiate protocol version 1.
2. `session/new` with `{cwd, mcpServers: []}` — returns `{sessionId, configOptions, models, modes, _meta}`.
   - The response already reports `currentModelId: "harness/proxy"` because the custom provider profile is the only configured provider.
   - Startup info is emitted as `session/update` `agent_message_chunk` notifications after this call.
3. Drain startup notifications before the first prompt so they do not mix into the user response.
4. `session/prompt` with `{sessionId, prompt: [{type: "text", text: ...}]}` for each turn.
   - The bridge sends `agent_message_chunk` notifications and returns `{stopReason: "end_turn"}` once the model turn completes.
   - Text response is collected from `sessionUpdate: "agent_message_chunk"` notifications with `content.type == "text"`.
5. Clean shutdown: terminate the bridge process group (`SIGTERM`, then `SIGKILL`), close stdin/stdout/stderr, and assert the child `pi` process is gone.

## Model/provider selection

With the tracked custom-provider profile as the only provider, `pi-acp`/`pi` default to `harness/proxy` without needing an explicit `session/set_config_option` call. No `/v1/models` probe was observed during launch or prompt in the governed fake-proxy test.

## Clean-shutdown handshake

pi-acp does not advertise `sessionCapabilities.close`, so `session/close` is not used. The Python adapter owns lifecycle:

- On success or exception, `_terminate_process_group` sends `SIGTERM` to the process group.
- Waits up to 5 seconds; if still alive, sends `SIGKILL`.
- Closes all stdio handles.
- The test asserts `proc.poll() is not None` and that `pgrep -af "pi --mode rpc"` is empty.
