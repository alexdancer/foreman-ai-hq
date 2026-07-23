## Discovery notes

Confirmed from installed `pi` 0.81.1 and `pi-acp` 0.0.31.

### pi tool flags

`pi --help` shows:

- `--tools, -t <tools>` — "Comma-separated allowlist of tool names to enable. Applies to built-in, extension, and custom tools"
- `--exclude-tools, -xt <tools>` — denylist variant
- `--no-builtin-tools, -nbt` — disable built-in tools but keep extension/custom tools
- `--no-tools, -nt` — disable all tools

`@earendil-works/pi-coding-agent/dist/core/tools/index.js` defines the canonical built-in set:

```js
export const allToolNames = new Set(["read", "bash", "edit", "write", "grep", "find", "ls"]);
```

And a read-only subset:

```js
export function createReadOnlyToolDefinitions(cwd, options) {
    return [
        createReadToolDefinition(cwd, options?.read),
        createGrepToolDefinition(cwd, options?.grep),
        createFindToolDefinition(cwd, options?.find),
        createLsToolDefinition(cwd, options?.ls),
    ];
}
```

`pi --tools read,grep,find,ls` therefore enables exactly the read/search tools and omits `bash`, `edit`, and `write`.

### pi tool allowlist enforcement

`@earendil-works/pi-coding-agent/dist/cli/args.js` parses `--tools` into a list of trimmed names:

```js
else if ((arg === "--tools" || arg === "-t") && i + 1 < args.length) {
    result.tools = args[++i]
        .split(",")
        .map((s) => s.trim())
        .filter((name) => name.length > 0);
}
```

`@earendil-works/pi-coding-agent/dist/core/agent-session.js` applies the allowlist during tool-registry refresh:

```js
const allowedToolNames = this._allowedToolNames;
const excludedToolNames = this._excludedToolNames;
const isAllowedTool = (name) => (!allowedToolNames || allowedToolNames.has(name)) && !excludedToolNames?.has(name);
```

Only allowed names are registered and exposed to the model. This is the fail-closed launch-time guardrail: any future tool not in `read,grep,find,ls` stays denied.

### pi-acp bridge spawn behavior

`node_modules/pi-acp/dist/index.js` (0.0.31):

```js
function getPiCommand(override) {
  return override ?? defaultPiCommand();
}

static async spawn(params) {
  const cmd = getPiCommand(params.piCommand);
  const args = ["--mode", "rpc", "--no-themes"];
  if (params.sessionPath) args.push("--session", params.sessionPath);
  const child = spawn(cmd, args, {
    cwd: params.cwd,
    stdio: "pipe",
    env: process.env,
    shell: shouldUseShellForPiCommand(cmd)
  });
}
```

`PI_ACP_PI_COMMAND` is passed as the single executable override; the bridge then appends its fixed `--mode rpc --no-themes` (and `--session <path>`) args.

### Wrapper argv shape with tool policy

The adapter generates a POSIX wrapper:

```sh
#!/bin/sh
exec pi --append-system-prompt "${PI_ACP_PERSONA_PATH}" --tools "${PI_ACP_ALLOWED_TOOLS}" "$@"
```

With:

- `PI_ACP_PI_COMMAND` = absolute path to generated wrapper
- `PI_ACP_PERSONA_PATH` = absolute path to tracked `orchestrator.md`
- `PI_ACP_ALLOWED_TOOLS` = `read,grep,find,ls` (comma-joined, no secrets)

When the bridge spawns the wrapper, the wrapper re-execs `pi` with the final argv:

```
pi --append-system-prompt <orchestrator.md> --tools read,grep,find,ls --mode rpc --no-themes --session <session-file>
```

The `--tools` flag reaches the pi child before the bridge's fixed `--mode rpc --no-themes "$@"`.

### One-shot path

`launch_pi_once` passes `--tools read,grep,find,ls` directly on the `pi -p` argv next to `--append-system-prompt`.

### pi-acp does not gate built-in tools behind ACP permission

`node_modules/pi-acp/dist/index.js`:

Tool calls are emitted as report-only `session/update` notifications:

```js
this.emit({
  sessionUpdate: "tool_call",
  toolCallId,
  title: toolName,
  kind: toToolKind(toolName),
  status,
  locations,
  rawInput
});
```

The only `conn.requestPermission` call is inside `requestExtensionPermission` and wraps an extension UI tool call:

```js
async requestExtensionPermission(id, ev, options) {
  return await this.conn.requestPermission({
    sessionId: this.sessionId,
    toolCall: extensionUiToolCall(id, ev),
    options
  });
}
```

`requestPermission` is extension-UI only; there is no hook to pause a built-in `bash`/`edit`/`write` tool call and route it to a human. Mid-flight HITL escalation of denied tools is therefore not buildable on pi-acp 0.0.31; deterministic deny-at-launch is the honest guardrail for this slice.
