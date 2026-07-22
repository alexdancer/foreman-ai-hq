# Getting started

This is the first-run guide for operators evaluating Foreman AI HQ in their own workflow.

## First-run path

1. Install the operator CLI:
   ```bash
   pipx install "git+https://github.com/alexdancer/foreman-ai-hq.git"
   ```
   After PyPI release, use `pipx install foreman-ai-hq`. See [Install options](INSTALL.md) for the curl installer and Homebrew status.
2. Initialize and start:
   ```bash
   cd /path/to/your/repo
   foremanctl init
   foremanctl serve
   ```
   `foremanctl init` keeps the installed CLI global but writes repo-local state under `.foreman/`. Inside a Git repo, it targets the Git root even if you run it from a subdirectory; outside Git, it uses the current directory. It creates `.foreman/config.toml`, `.foreman/secrets.env`, `.foreman/guardrails.yaml`, and `.foreman/harness.db`.
3. Open `http://localhost:8000/`. The default loopback server does not require a portal login token.
4. Open `/settings/control-plane`, choose provider/model, paste the provider API key, save, then test the connection.
5. Connect a local repository from `/projects`.
6. Open `/settings/workers`, choose a Worker Adapter, discover/allow Worker models, then verify tracking.
7. Estimate a tiny task in the project's Pipeline, follow it on the Execution Floor, and inspect its Evidence Drawer or full Session Report.
8. Run `foremanctl check` any time you need redacted setup status for support.

## Contributor checkout

If you are developing inside this repository rather than installing the operator CLI, use the repo-managed uv environment:

```bash
uv run --extra test pytest -q
uv run foremanctl --help
```

The full run includes the `tests/e2e` browser tests, which need Node and a
one-time `uv run --extra test playwright install chromium`. Run
`uv run --extra test pytest tests/portal tests/api tests/workers -q` to skip them.

`uv run foremanctl ...` is a contributor convenience. The public operator path is an installed bare `foremanctl` command.

## Model and credential split

Foreman AI HQ has two model layers:

| Layer | What it powers | Auth source |
|---|---|---|
| Control Plane / orchestrator model | Estimates, planning, task breakdown, summaries, reports; deterministic routing uses estimator evidence plus Worker Adapter allowed models | `/settings/control-plane`, ignored `.foreman/secrets.env`, or env vars |
| Worker / coding harness models | The actual coding task launched through OpenCode, Claude Code, Codex, or another adapter | The native CLI's own auth/config |

Pasting a control-plane API key does not configure native Worker CLIs.

## What Foreman AI HQ governs

Foreman AI HQ governs launches that go through its project Pipeline / Execution Floor and verified Worker Adapter path:

- It estimates tasks before launch.
- It records budget and launch evidence.
- It enforces launch guardrails before new Worker runs.
- It imports trustworthy Worker usage evidence when available.
- It keeps human review as the final disposition step.

Foreman AI HQ cannot govern arbitrary external-agent token spend. The supported local path is governed only after Worker Adapter setup proves the native Worker CLI emits trustworthy, run-bound usage evidence that Foreman AI HQ can import for the selected model.

## Investigating with a Scout

Choose Task kind **Scout** in short project intake when you need a bounded repository answer before implementation. A Scout is not a hidden planning call: it is estimated and launched as a visible Task, records its own Worker usage, enters Review, and produces a normal Session Report with findings, risks, and a recommendation.

Scout launch is stricter than ordinary launch. The adapter must prove authoritative token tracking and expose a separately verified, adapter-enforced read-only profile. The current built-in profile is Codex using `--sandbox read-only`; OpenCode and Claude Code may remain launchable for compatible implementation Tasks without being Scout-launchable.

An automatic estimate below `0.60` confidence also appears in Needs You as an advisory decision. You may acknowledge it, replace it manually, or create one linked Scout for that estimate revision. The original Task stays in its current lifecycle state and remains launchable when ordinary guardrails pass. Scout completion does not rewrite the estimate: request a re-estimate from the report, inspect the pending result, then explicitly apply or dismiss it.

## Local secret storage

- `.foreman/config.toml` stores non-secret config only.
- `.foreman/secrets.env` is ignored local storage for the shared-access portal token and control-plane API key.
- The portal can write a submitted control-plane API key to `.foreman/secrets.env` but never shows that raw value again.
- Blank API-key submissions preserve the existing key.
- Do not paste `.foreman/secrets.env`, API keys, portal tokens, bearer tokens, or raw credentials into support issues.

## Docker and Local Runner limits

Docker runs the containerized Control Plane/Portal and persists SQLite state at `/data/harness.db`. Docker publishes the Portal beyond loopback, so token login remains enabled there; the no-secret path proves image build/start, `/health`, `/login`, and persistence with the synthetic default Docker token.

Docker does not automatically receive host-installed OpenCode, Claude Code, Codex, local repo paths, or host credentials. Real Worker launch readiness still depends on Worker Adapter setup and tracking-mode verification.

## Portal screenshots

Use synthetic/public-safe data only. Do not capture real secrets, real customer data, or private repo content.

![Foreman AI HQ dashboard UI](assets/screenshots/dashboard-overview.png)

![Foreman AI HQ project board UI](assets/screenshots/project-board-review-workflow.png)

![Foreman AI HQ control-plane model UI](assets/screenshots/control-plane-model-settings.png)

![Foreman AI HQ worker adapter setup UI](assets/screenshots/worker-adapter-setup.png)

![Foreman AI HQ token budget UI](assets/screenshots/token-budget-soft-reset.png)

![Foreman AI HQ sessions and token ledger UI](assets/screenshots/sessions-token-ledger.png)

![Foreman AI HQ task breakdown recovery UI](assets/screenshots/task-breakdown-manual-recovery.png)
