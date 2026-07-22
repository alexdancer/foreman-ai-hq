## Why

M1 (`proxy-governed-orchestration`) proved `proxy_governed` metering end-to-end but only client-agnostically; a **real pi turn through the proxy** was explicitly deferred (M1 task 5.2). The M1 spike found why it's non-trivial: pi 0.80.10's built-in `openai` provider **ignores `OPENAI_BASE_URL`** (returns 401 without hitting the proxy), so the env-injection pattern Worker Adapters use (`worker_adapters.py` sets `OPENAI_BASE_URL`/`OPENAI_API_KEY`) does not work for pi. Before building the ACP conversational runtime (M2b), we must prove pi's spend is actually governable — by pointing pi at the Harness Proxy through a **custom provider** and recording one real pi turn as a `planning` token turn.

## What Changes

- Introduce the tracked **pi orchestrator profile** (first, minimal version) under a git-tracked repo path — a custom-provider entry whose `baseUrl` is the Harness Proxy. Only the provider config; no orchestrator prompt, tools, plugins, or memory yet.
- Add a launch path that runs pi **non-interactively** (`pi -p`) with that profile, injecting the planning session bearer as the provider `apiKey` **at launch** (from `.htb/secrets.env`, never committed) — mirroring the Worker Adapter session-key injection intent, but via pi's config-file custom provider because `OPENAI_BASE_URL` is ignored.
- Reuse M1's `db.create_planning_session` to mint the metering anchor + bearer, and M1's proxy classification so the resulting turn records as `planning`.
- Prove it: launching pi through this path records exactly one real pi turn as a `planning` token turn.
- First task resolves the concrete unknown the spike left open: **how pi declares a custom provider** (config-file location and shape), since pi had no config dir on a fresh install.

## Capabilities

### New Capabilities
- `orchestrator-runtime`: pi runs as a governed orchestrator process whose model spend is metered through the Harness Proxy as `planning` Orchestration Tokens. Established here minimally — a non-interactive (`pi -p`) launch with a tracked custom-provider profile pointed at the proxy and the planning session bearer injected at launch. M2b later extends this capability with the ACP conversational runtime, orchestrator prompt, and memory.

### Modified Capabilities
<!-- None. Reuses M1's create_planning_session and proxy planning classification unchanged. -->

## Impact

- **New tracked repo path** for the pi orchestrator profile (custom-provider config). Unlike the git-ignored operator adapter dirs (`.opencode/`, `.codex/`), this is git-tracked because it defines product behavior (ADR-0007 Consequences: pi = configuration, not engine).
- **Backend**: a minimal pi launch helper that constructs the `pi -p` invocation, points it at the profile, and injects the planning bearer as the provider `apiKey` at launch. Reuses `db.create_planning_session` and the existing proxy endpoint; no new metering code.
- **Secrets**: the provider `apiKey` (planning session bearer) is injected at launch and never committed to the profile.
- **Dependencies**: pi installed on the machine (external, pinned — ADR-0007), and `proxy-governed-orchestration` (M1) archived (done). No new Python dependency.
- **Non-goals**: no ACP, no Node↔Python bridge, no subprocess supervision/lifecycle management, no HITL/cancellation, no streamed tool-calls, no orchestrator prompt/persona, no tools or tool-scoping (M3), no memory, no plugins, no chat UI, and no `/v1/models` stub unless pi's launch actually probes it.
