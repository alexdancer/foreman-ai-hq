# ADR-0010: pi's inventory is the sole authority for the Orchestrator model

**Date**: 2026-07-25
**Status**: accepted
**Builds on**: ADR-0009 (the Orchestrator is one native-provider agent runtime owning planning, estimation, and breakdown).

## Context

ADR-0009 moved the Orchestrator off the Harness Proxy and onto pi running on its own
configured provider. The operator-facing configuration was never migrated with it. The
`/settings/control-plane` page still collects a provider, a base URL, an API key, and an
API key env name — the shape of an OpenAI-compatible HTTP connection — and offers a
curated model dropdown of ten hardcoded entries.

Of those fields, only the model name reaches pi, and it reaches it with different
semantics than the page implies:

- `control_plane_provider` is **inert** for orchestration. `pi_adapter._resolve_pi_provider_model()`
  takes only the model string, splits it on `/`, and otherwise falls back to pi's own
  `defaultProvider`. Nothing passes the configured provider to pi.
- `control_plane_base_url` and the API key are read only by `LLMClient`, which orchestration
  no longer uses.
- `CURATED_CONTROL_PLANE_MODELS` names providers (`openai`, `openrouter`) that are not pi
  provider ids. An entry like `("openrouter", "anthropic/claude-sonnet-5")` resolves
  correctly only by accident — the OpenRouter namespace happens to parse as a pi provider.

The consequences compound. **Test control-plane connection** exercises `LLMClient`, so it
can report success against a provider the Orchestrator will never call; a green test and a
dead Orchestrator are compatible states. **Setup Overview** computes readiness as
`bool(os.getenv(api_key_env))`, so exporting an API key marks the Orchestrator "ready" on a
machine where pi has never been logged in. And the three pi launch paths record the model
inconsistently — `launch_pi_once` and the ACP conversation persist the provider-stripped
`model_id`, while `run_pi_structured_job` persists the full `provider/model` — so planning
turns and estimation turns land under different model strings, fragmenting the per-model
Estimation Coefficients.

Meanwhile pi already exposes exactly the surface this setting needs. `pi --list-models`
returns provider, model, context window, max output, thinking support, and image support,
**filtered to providers the operator is actually authenticated with**; against an empty
agent directory it returns "No models available. Use /login…" rather than a catalog. It
runs offline in under a second.

## Decision

**pi's reported inventory is the only authority for which models the Orchestrator can use.
Everything the harness previously asserted about orchestration models and credentials is
retired, and an Orchestrator that is not configured against that inventory does not
operate.**

1. **One model concept, one page.** A single **Orchestrator Model** setting drives every
   orchestration job — Planning Chat, intake judgment, Task Estimation, Task Breakdown, and Agent Review.
   The provider / base URL / API key trio stops being an operator-facing setting. Agent
   Review and the CLI health check move onto pi. `LLMClient` and the Harness Proxy remain in
   the codebase serving `proxy_governed` Workers, without a settings surface, until a stock
   adapter is verified end to end through the proxy.

2. **The inventory is the sole authority.** An Orchestrator Model is a provider-qualified pi
   id (`provider/id`) that must appear in the discovered inventory. Bare names, fuzzy
   patterns, curated hardcoded lists, and the `"gpt-5.4"` code default are all removed —
   each was the harness holding an opinion pi did not give it. A stored value absent from
   the inventory is **not configured**, not repaired by inference.

3. **Cached discovery, live validation, real verification.** Discovery follows the existing
   Worker Adapter pattern: explicit refresh runs `pi --list-models`, parses it under the same
   non-model-text rejection guard, and persists evidence with a timestamp. Save re-validates
   live so a stale cache can never persist a broken setting. Verification runs a real
   sentinel `pi` turn and passes only if the sentinel matched **and** a token row was
   recorded — the same two-part bar Worker Adapters must clear, because install-only checks
   are not proof.

4. **Accounting reflects what ran.** All three pi paths record one model convention, taken
   from pi's own `raw_usage` provider and model, falling back to the configured value only
   when pi emits no evidence.

5. **Not configured means not operating.** The board, launches, and every orchestration
   jobs are gated on a configured Orchestrator. Login, every settings page, and read-only
   evidence — sessions, reports, alarms — stay reachable, so an expired provider token can
   never lock an operator out of their own audit trail or the pages needed to fix it.

## Alternatives considered

| # | Alternative | Why rejected |
|---|---|---|
| 1 | Keep one page with two labelled sections (Orchestrator and provider connection) | Preserves the adjacency that let a green connection test coexist with a dead Orchestrator; defers the question rather than answering it. |
| 2 | Delete `LLMClient` and the Harness Proxy outright, retiring `proxy_governed` | ADR-0009 deliberately kept the proxy for Workers, where runaway spend actually lives. The path is unverified, not disproven; deleting it is a one-way door for a reversible problem. |
| 3 | Auto-qualify bare model ids against the inventory when unambiguous | Re-establishes the harness as a second authority guessing at provider intent — the exact mechanism behind the OpenRouter-namespace accident. |
| 4 | Keep the runtime `defaultProvider` fallback, validate new saves only | Two id conventions coexist indefinitely; the ledger keeps fragmenting for anyone who never revisits the page. |
| 5 | Run `pi --list-models` live on every page render | Truthful but puts a ~0.85 s subprocess on settings and readiness surfaces, and a hard live dependency would break Recorded Demo Runs, which must run without a real provider and without an environment-driven mode that weakens production behavior. |
| 6 | Advisory-only readiness badge (status quo) | Readiness computed from an unrelated fact is what produced this ADR. |
| 7 | Gate everything except login and settings | An expired OAuth token would hide the operator's own token ledger and alarm history exactly when they need it to explain spend. |

## Consequences

- **First run gains a required step.** With no code default, a fresh install is not
  configured until the operator picks a model from pi's inventory. This is intended: the
  previous default was a bare id that resolved by luck or not at all.
- **The board gate must read persisted state, not a live subprocess.** Because discovery
  evidence lives in the database, Recorded Demo Runs seed it as ordinary scenario state and
  the gate passes honestly without a test-only bypass. A live-shelling gate would have
  required exactly the environment-driven weakening the demo contract forbids.
- **Agent Review changes shape.** It becomes a `submit_review` structured job over a curated
  payload plus the Task Branch diff, with no live repository tools — the Scout boundary of
  ADR-0009 applies to review as it does to estimation and breakdown. The markdown-ish
  response repair parser is deleted; a submit tool enforces the schema at the tool boundary.
- **The Docker image cannot orchestrate.** It ships no Node, no pi, and no provider auth. Its
  five control-plane environment variables are removed rather than left advertising a
  capability the image does not have; Docker is documented as a portal and evidence surface.
  Making Docker orchestrate is deferred: mounting the pi agent directory read-only breaks
  OAuth refresh, and read-write moves host provider credentials into the container.
- **Verification costs tokens.** Orchestrator verification records an
  `adapter_verification` Orchestration Token turn. This is deliberate: an unmetered check
  would hold the Orchestrator to a weaker bar than Workers and reintroduce the hidden helper
  spend ADR-0009 removed.
- **`Control Plane Model` is retired as a domain term**, along with
  `Portal-Managed Control Plane API Key` and `Control Plane Connection Test`. `Orchestrator
  Model` and `Orchestrator Model Inventory` replace them.
