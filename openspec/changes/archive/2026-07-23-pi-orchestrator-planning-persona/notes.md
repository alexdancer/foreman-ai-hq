## Discovery notes

Confirmed from installed `pi` 0.81.1 and `pi-acp` 0.0.31.

### pi system-prompt flags

- `pi --help` shows:
  - `--system-prompt <text>`
  - `--append-system-prompt <text>` — "Append text or file contents to the system prompt (can be used multiple times)"
- A path to the tracked persona file can be passed as the argument; pi reads the file contents and appends them to its system prompt.

### pi-acp bridge spawn behavior

In `node_modules/pi-acp/dist/index.js`:

```js
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

`getPiCommand` returns `process.env.PI_ACP_PI_COMMAND` or `pi`. The bridge therefore accepts only a **single executable override** and always appends its fixed `--mode rpc --no-themes` args.

### Wrapper shape

Decision: generate a small POSIX wrapper into the per-launch temp directory. This avoids packaging executable-bit concerns and keeps the wrapper content-free of persona text.

```sh
#!/bin/sh
exec pi --append-system-prompt "${PI_ACP_PERSONA_PATH}" "$@"
```

The adapter sets:

- `PI_ACP_PI_COMMAND` to the absolute path of the generated wrapper.
- `PI_ACP_PERSONA_PATH` to the absolute path of the tracked `orchestrator.md` persona.

The wrapper is `chmod +x` before `PI_ACP_PI_COMMAND` is handed to the bridge. The bridge calls the wrapper with `--mode rpc --no-themes`, and the wrapper re-execs `pi` with `--append-system-prompt <persona>` followed by those args.

### One-shot path

`launch_pi_once` passes `--append-system-prompt <tracked-persona>` directly on the `pi -p` argv because there is no pi-acp bridge in that path.
