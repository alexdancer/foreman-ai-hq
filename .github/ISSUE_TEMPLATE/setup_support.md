---
name: Setup support
about: Get help with install, control-plane setup, Docker, or Worker Adapter readiness
title: "Setup: "
labels: needs-triage
---

## Where are you blocked?

- [ ] Install
- [ ] `foremanctl init`
- [ ] Portal login
- [ ] `/settings/control-plane` discovery/save/verification
- [ ] Project connect
- [ ] Worker Adapter setup
- [ ] Worker launch
- [ ] Session report/token evidence
- [ ] Docker local run

## Redacted setup check

Paste `foremanctl check` output here. If you are using a source checkout without installing the CLI, `uv run foremanctl check` is also acceptable. Do not paste API keys, portal tokens, `.foreman/secrets.env`, or raw credentials.

```text

```

## Environment

- OS:
- CPU architecture:
- Install method: pipx / curl installer / Homebrew / source checkout / Docker / other
- Does `command -v foremanctl` succeed?: yes / no
- Docker or local Python:
- Orchestrator Model and pi inventory state:
- Optional Harness Proxy upstream configuration in use: yes / no
- If yes, upstream key source: `.foreman/secrets.env` / environment variable
- Worker Adapter: OpenCode / Claude Code / Codex / Hermes / other
- Tracking mode: `proxy_governed` / `native_usage` / `observed_only` / unknown

## What happened?


## Expected behavior

