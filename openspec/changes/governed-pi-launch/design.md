## Context

M1 shipped the metering plumbing: `db.create_planning_session` mints a planning-kind
anchor + bearer, and `routes/proxy.py:_persist_turn` derives `usage_kind` from the
session kind, so any OpenAI-compatible client authenticated as a planning session lands
a `planning` token turn. M1's proof was client-agnostic; a real pi turn was deferred.

Worker Adapters point their CLIs at the proxy by env (`worker_adapters.py` sets
`OPENAI_BASE_URL` = proxy_url and `OPENAI_API_KEY` = session_api_key). The M1 spike
proved this does **not** work for pi: pi 0.80.10's built-in `openai` provider ignores
`OPENAI_BASE_URL` and 401s without hitting the proxy. pi had no config dir on a fresh
install, so the custom-provider config location/shape is unknown.

This change (ADR-0007 M2a) closes that gap: launch pi through a tracked custom-provider
profile and record one real pi turn as `planning`. It establishes the
`orchestrator-runtime` capability minimally, before the ACP conversational runtime (M2b).

## Goals / Non-Goals

**Goals:**
- pi's model traffic reaches the Harness Proxy via a tracked custom-provider profile.
- The planning bearer is injected as the provider key at launch, never committed.
- One real pi turn records as a `planning` token turn (reusing M1 unchanged).

**Non-Goals:**
- No ACP, Node↔Python bridge, subprocess supervision/lifecycle, HITL/cancel, or
  streamed tool-calls (all M2b).
- No orchestrator prompt/persona, tools, tool-scoping (M3), memory, or plugins.
- No chat UI. No `/v1/models` stub unless pi's launch actually probes it.

## Decisions

**1. Route pi via a config-file custom provider, not `OPENAI_BASE_URL` env.**
The spike proved the env path is ignored by pi's stock provider. The profile declares a
custom provider with `baseUrl` = proxy. Alternative (env var, as Worker Adapters use)
rejected — it silently 401s for pi.

**2. The custom-provider config lives in a git-tracked profile; the key is injected at launch.**
Per ADR-0007, pi = configuration-not-engine: the profile (provider entry) is product
behavior and is tracked, unlike the git-ignored `.opencode/`/`.codex/` operator dirs.
The provider `apiKey` = planning bearer is supplied to the launched process only (from
`.htb/secrets.env`), never written into the tracked file. Alternative (commit a key,
or store under a git-ignored dir) rejected — secret leak / not product-tracked.

**3. Non-interactive `pi -p`, not a supervised subprocess.**
M2a only needs one turn to prove metering. Running `pi -p` and letting it exit is the
smallest thing that works; a managed, cancellable, long-lived subprocess is M2b's job.
Alternative (build the subprocess lifecycle now) rejected — premature, that's M2b.

**4. Reuse M1 wholesale; add no metering code.**
`create_planning_session` and the proxy's planning classification already exist and are
tested. M2a is integration + config only. Alternative (new planning launch metering)
rejected — duplicates M1.

**5. Task 1 discovers pi's custom-provider config format before wiring.**
pi's actual provider-config location/shape is unknown from a minimal read; it must be
learned from pi's docs or by experiment (hardware-calibration reality: the tool behaves
how it behaves, not how a spec wishes). This gates the profile's concrete shape.

## Risks / Trade-offs

- **pi's custom-provider config format is unknown** → task 1 resolves it from pi docs /
  experiment before the profile is written; the profile shape is not finalized until then.
- **pi may probe `/v1/models` on startup** (the proxy only serves `/v1/chat/completions`)
  → observe during the real-launch task; add a minimal stub only if pi actually 4xxs
  without it. Do not build the stub speculatively.
- **pi non-interactive flag/behavior may differ across pi versions** → pin to the
  installed pi and record the exact invocation; version drift is an M2b lifecycle concern.
- **Launch injects a real bearer** → scope the injected env/key to the launched process
  and assert it is absent from the tracked profile in a test.

## Migration Plan

Additive. New tracked profile path + a launch helper; reuses M1 metering. No schema or
existing-flow change. Rollback = remove the profile + helper; M1 metering is untouched.

## Resolved from experiment (pi 0.81.1 on this machine)

- pi custom-provider config is loaded from the directory pointed to by `PI_CODING_AGENT_DIR` (default `~/.pi/agent`) as `models.json`. Schema: `{"providers": {"<provider-id>": {"baseUrl": "...", "api": "openai-completions", "apiKey": "$ENV_VAR", "models": [{"id": "..."}]}}}`.
- Non-interactive one-turn argv: `pi -p --provider harness --model harness/proxy "<prompt>"`. The request body sets `stream: true`; the proxy must return a proper SSE stream with a final `finish_reason: "stop"` chunk. The model id from the profile is passed through to the proxy unchanged.
- No `/v1/models` probe was observed in `-p` mode, so no stub is needed.

## Open Questions

- None remaining for M2a.
