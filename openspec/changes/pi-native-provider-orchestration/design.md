## Context

The Orchestrator runtime is **pi** (an agent CLI), spawned through the `pi-acp`
bridge by `open_pi_conversation`. Grounded facts (verified 2026-07-24 against
installed pi `0.81.1`):

- pi supports `--provider`, `--model`/`--model provider/id`, `--append-system-prompt`,
  `--tools`, and `--mode json|rpc`.
- `~/.pi/agent/auth.json` holds OAuth token sets for `anthropic` and `openai-codex`;
  the operator has completed "Sign in with ChatGPT". `openai-codex` exposes `gpt-5.4`,
  `gpt-5.4-mini`, `gpt-5.5`, `gpt-5.6-*`. Current `orchestrator_model` default
  `gpt-5.4` is valid.
- **pi emits trustworthy per-turn usage.** In `--mode json` it streams one JSON line
  per session event (`print-mode.js`); the assistant message carries `usage`
  (`input`, `output`, `cacheRead`, `cacheWrite`, `reasoning`, `totalTokens`, `cost`)
  plus `providerId`/`modelId`. This clears the harness `native_usage` evidence bar
  (model + input + output + total + exit + run binding).
- The harness currently overrides pi onto a proxy-only profile
  (`orchestrator/pi/profile/models.json` → `harness`/`proxy`) and an isolated tmp
  agent dir, and injects a planning bearer as the provider API key, so pi never reads
  `~/.pi` and every turn is `proxy_governed`.

This change moves the **planning** path off the proxy. Estimation/breakdown are out
of scope here (they migrate in `orchestrator-structured-jobs-on-pi`).

## Goals / Non-Goals

**Goals**
- The planning Orchestrator runs pi on its own configured provider/model, using the
  operator's existing pi auth. Provider-agnostic.
- Orchestration spend is accounted from pi's native usage evidence.
- Persona and read-only tool scoping preserved.
- `orchestrator-runtime` spec is corrected to describe the native path.

**Non-Goals (this change)**
- Migrating estimation/task breakdown to the Orchestrator runtime (separate change).
- Reconstructing the proxy's budget-zone prompt injection / `max_tokens` clamp
  pi-side (ADR-0009: orchestration is accounted, not hard-capped).
- A harness-managed provider login flow (pi owns "Sign in with ChatGPT").

## Decisions

**1. pi runs on its own configured provider for planning.** Launch pi with
`--provider <p> --model <orchestrator_model>` and let it read the operator's real pi
auth, instead of the `harness`/`proxy` profile and injected bearer. `openai-codex`/
OAuth is one configuration; the mechanism is provider-agnostic. Rejected: teaching
the proxy to forward OAuth to a vendor backend — not an OpenAI-compatible endpoint,
fragile and ToS-sensitive to reproduce outside pi.

**2. Planning tracking becomes `native_usage`.** Orchestration spend is recorded from
pi's own `--mode json` usage, reusing the `native_usage` evidence path Worker
Adapters use (`tracking_modes.py`, `native_usage.py`). Session kind stays `planning`;
only the tracking mode changes. A multi-model-call turn emits one usage event per
model call — sum them into the planning turn's spend.

**3. Persona and tools unchanged.** `--append-system-prompt` and
`--tools read,grep,find,ls` are pi flags, independent of provider/transport, so they
carry over verbatim.

**4. Auth reach without leaking secrets.** The harness-spawned pi must read the
operator's real pi auth (point pi's agent/config dir at the real one, or reference the
auth file) while never writing tokens into the git-tracked profile, logs, or a
retained tmp dir. Exact mechanism is an implementation task; the invariant is: tokens
are read from the operator's pi auth, never copied into the repo or logs.

**5. `orchestrator-runtime` is rewritten, not amended.** The whole capability is
built on proxy + bearer + `usage_source: harness_proxy`. The two purely-proxy
requirements (custom-provider profile, planning bearer) are REMOVED; the metering,
ACP-subprocess, cancellation, persona, held-conversation, and tool requirements are
MODIFIED to describe the native path (no bearer; spend accounted from native usage).

## Relationship to prior changes

- Builds on the archived `orchestrator-model-runtime` (which gave `orchestrator_model`
  its own setting, retired `control_plane_model`, and fixed persona composition). That
  change made the **proxy** override the planning model; this change moves planning off
  the proxy, so that override becomes inert for planning (it still governs any
  remaining `proxy_governed` callers). Everything else from it stands.
- Supersedes the transport decision of ADR-0007 per ADR-0009.

## Risks / Trade-offs

- **No hard budget enforcement on planning.** Native usage gives accounting, not
  pre-flight caps / mid-run throttle. Deliberate (ADR-0009); revisit only if planning
  spend needs hard caps.
- **Provider-auth expiry.** If the configured provider's auth is expired/absent, pi
  fails to start a turn; the view must render a clear sign-in-required state, not dead
  UI. Ties to the Planning Chat error states.
- **Native usage fidelity.** Accounting depends on pi's json usage; verify the event
  shape and per-call summation before trusting totals.
- **ToS.** Uses pi's sanctioned "Sign in with ChatGPT" OAuth; the harness never
  scrapes or re-implements a vendor backend.
