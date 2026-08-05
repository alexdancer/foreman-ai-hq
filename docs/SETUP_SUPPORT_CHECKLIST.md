# Setup support checklist

Use this when opening a setup issue or asking for help. Do not paste secrets.

## Redacted command output

Run:

```bash
foremanctl check
```

If you are a contributor running from a checkout without installing the CLI, this equivalent development command is also acceptable:

```bash
uv run foremanctl check
```

Paste the redacted `PASS` / `WARN` / `FAIL` output only. Do not paste API keys, portal tokens, `.foreman/secrets.env`, bearer tokens, raw credential files, or private repository content.

## Environment details

Include:

- OS and CPU architecture
- Install method: `pipx`, curl installer, Homebrew, source checkout, Docker, or other
- Whether `command -v foremanctl` succeeds
- Orchestrator Model and pi inventory/authentication state
- Worker Adapter identity: OpenCode, Claude Code, Codex, or other
- Worker tracking status shown in the Portal: verified native usage, diagnostic-only, failed, or unknown
- Whether you are running local Python or Docker

## Safe screenshots

Screenshots are useful when they show sanitized Portal state and no secrets.

![Foreman AI HQ task breakdown recovery UI](assets/screenshots/task-breakdown-manual-recovery.png)

## Boundary reminder

Installing Foreman AI HQ exposes the `foremanctl` operator CLI. Pi orchestration authentication comes from `pi /login`; native Worker CLI setup happens separately in those tools and through the Portal Worker Adapter setup flow.
