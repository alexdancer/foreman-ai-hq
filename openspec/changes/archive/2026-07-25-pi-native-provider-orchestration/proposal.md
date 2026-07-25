## Why

The Orchestrator (pi) drives the governed Planning Chat by routing its model
traffic through the API-key Harness Proxy (`orchestrator-runtime`, ADR-0007). Two
wants break that:

- **The operator wants the Orchestrator on their own model provider.** ChatGPT via
  pi's "Sign in with ChatGPT" OAuth is the immediate case (`~/.pi/agent/auth.json`
  already holds an `openai-codex` token set; the operator is logged in), but the
  provider is incidental — the want is "pi's own configured provider, whatever it
  is." OAuth-backed providers are not OpenAI-compatible chat endpoints and cannot
  traverse the API-key proxy at all, and more generally forcing pi through the proxy
  means it can never use a provider the proxy can't carry.
- **The proxy override actively fights this.** `orchestrator/pi/profile/models.json`
  pins pi to a single `harness` provider (proxy `/v1`, `$PI_HARNESS_API_KEY`, model
  `proxy`), and the launch uses an isolated tmp agent dir so pi never reads the
  operator's real auth. pi is forced onto `--provider harness --model proxy`.

This change runs the planning Orchestrator on **its own provider config**, off the
proxy, with planning spend **accounted from pi's native usage** (which is
trustworthy — pi emits provider, model, input/output/cache/reasoning/total, even
cost, per turn in `--mode json`). It is **planning only**; estimation and task
breakdown migrate in the follow-on `orchestrator-structured-jobs-on-pi`. It also
pays down the spec debt: the `orchestrator-runtime` capability, written entirely on
pi-through-proxy-with-a-bearer, is rewritten for the native path.

Per ADR-0009: orchestration becomes *accounted, not hard-capped*. The proxy remains
for `proxy_governed` Workers, where hard pre-flight caps and mid-run throttling
actually matter.

## What Changes

- **The Orchestrator runs planning on its own configured provider.** The harness
  launches pi with its own provider/model (`--provider <p> --model
  <orchestrator_model>`), reading the operator's real pi auth, instead of the
  `harness`/`proxy` profile override and the isolated tmp agent dir. pi owns provider
  auth and token refresh. This is provider-agnostic; `openai-codex`/OAuth is one
  configuration, not a hard-coded dependency.
- **Planning moves `proxy_governed` → `native_usage`.** Planning turns no longer
  traverse the proxy; the harness records orchestration spend from pi's native
  per-turn usage evidence (`pi --mode json`), reusing the `native_usage` evidence
  path Worker Adapters already use.
- **`orchestrator_model` is a pi provider/model id** for planning (default `gpt-5.4`
  is already valid), replacing the `proxy` placeholder.
- **Persona and read-only tool scoping are preserved** (they are pi CLI flags,
  independent of transport).
- **Provider-auth-missing is a clear state.** When the configured provider's auth is
  absent or expired, Planning Chat renders a clear sign-in-required state rather than
  a dead composer or silent empty turn.
- **`orchestrator-runtime` is rewritten off the proxy** (spec-debt fix): the
  proxy-custom-provider and planning-bearer requirements are removed; ACP subprocess,
  cancellation, persona, and read-only tools are preserved but re-metered as native
  usage.

## Capabilities

### Modified Capabilities
- `orchestrator-runtime`: the planning Orchestrator runs on its own configured model
  provider (not the Harness Proxy); planning turns are accounted from the runtime's
  native usage evidence; ACP subprocess lifecycle, in-flight cancellation, the
  orchestrator persona, and the read-only tool allowlist are preserved; a
  missing/expired provider auth surfaces a clear operator state.
- `proxy-governed-orchestration`: orchestration MAY run in `native_usage` mode off
  the proxy; any turns still traversing the proxy are governed and metered exactly as
  before.

## Impact

- **Backend.** `pi_adapter.py` (`open_pi_conversation`, `_prepare_pi_env`,
  `_write_pi_acp_wrapper`, the `models.json` override, tmp agent-dir isolation,
  `create_planning_session` bearer) to launch pi on its own provider against the
  operator's real pi auth; a native-usage recorder for planning turns.
- **Tracking.** Planning session kind stays `planning`; tracking mode becomes
  `native_usage` (`tracking_modes.py`, `native_usage.py`).
- **Frontend.** Planning Chat gains a provider-auth-missing state.
- **Settings/docs.** `orchestrator_model` documented as a pi provider/model id for the
  native path; setup notes that provider auth (e.g. "Sign in with ChatGPT") is
  established through pi, not a harness field.

## Open Questions (for design)

- **Auth reach without leaking secrets:** how the harness-spawned pi reaches the
  operator's real pi auth (point pi's agent/config dir at the real one vs. reference
  the auth file) while never copying tokens into the tracked profile, logs, or a
  retained tmp dir.
- **Native usage fidelity:** confirm the exact `--mode json` usage-event shape and
  that summing per-model-call usage matches the runtime's own totals before trusting
  the accounting.
