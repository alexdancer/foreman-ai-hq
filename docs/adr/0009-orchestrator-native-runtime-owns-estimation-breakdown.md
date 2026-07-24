# ADR-0009: The Orchestrator is one native-provider agent runtime that owns planning, estimation, and breakdown

**Date**: 2026-07-24
**Status**: proposed
**Supersedes**: the `proxy_governed` transport decision of ADR-0007 (which otherwise stands: pi as the Orchestrator runtime, driven over ACP, profile-as-config, Scout boundary).

## Context

ADR-0007 established pi as the control-plane Orchestrator runtime for the Planning
Chat, with its model traffic pointed at the Harness Proxy so every planning turn is
`proxy_governed` and metered as `planning` Orchestration Tokens. That shipped (M1 →
M2b). Two things have since changed the picture:

1. **The operator wants the Orchestrator to own estimation and task breakdown too**,
   as real agent turns — an estimator/decomposer that can reason over project context
   the way the planner does — not the two disconnected single-shot `llm_client` calls
   they are today. ADR-0007 explicitly scoped the Orchestrator to planning and left
   estimation/breakdown as one-shot steps.
2. **The operator wants the Orchestrator to run on their own model provider** (e.g.
   ChatGPT via pi's "Sign in with ChatGPT" OAuth, but the provider is incidental — the
   want is "pi's own configured provider", whatever it is). OpenAI's ChatGPT backend is
   OAuth-only and is not an OpenAI-compatible chat endpoint, so it cannot traverse the
   API-key Harness Proxy at all. More generally, forcing the Orchestrator through the
   proxy means it can never use a provider the proxy can't carry.

The landed `orchestrator-model-runtime` change already unified the *model name*
(`orchestrator_model`, with `estimator_model`/`task_breakdown_model` as fall-through
overrides) and fixed governance to *compose* persona + zone guidance rather than
replace. This ADR unifies the *runtime* and changes the *transport*.

## Decision

**The Orchestrator is a single agent runtime that runs planning, Task Estimation, and
Task Breakdown as agent turns, on its own configured model provider, with spend
accounted from the runtime's native usage rather than governed through the Harness
Proxy.**

Concretely, five coupled decisions taken in a design interview on 2026-07-24:

1. **Runtime unification (not just model).** Estimation and breakdown become
   Orchestrator agent turns, not single-shot `llm_client` calls. The value is a
   sizer/decomposer that can actually look before it commits.
2. **Provider-agnostic native transport.** The Orchestrator runs on its own provider
   config (dropping the harness proxy-only profile override and the isolated agent
   dir). OAuth vs API-key is a property of the chosen provider, not of the feature.
3. **Off the proxy → `native_usage`, accounted not hard-capped (P1).** Because the
   runtime calls the provider directly, orchestration spend is recorded from its
   native per-turn usage evidence — verified trustworthy (provider, model,
   input/output/cache/reasoning/total, even cost). The proxy stays *only* for
   `proxy_governed` Workers, where hard pre-flight caps and mid-run throttling
   actually matter. Orchestration keeps accounting + overrun alarms, not hard caps.
4. **The Scout boundary holds (i-pure).** Estimation/breakdown run on curated
   lightweight context and never crawl the repo inline. When a job genuinely needs
   code read, it emits an explicit *investigation-recommended* signal that becomes a
   visible, budgeted, read-only Scout Task; the reading is never silent hidden spend.
5. **Structured output via submit-tools (S2), per-job personas + allowlists.**
   Estimation and breakdown each end by calling a custom runtime tool
   (`submit_estimate` / `submit_breakdown`) whose schema *is* the result schema,
   enforced at the tool boundary (the runtime has no `response_format` mode but a full
   custom-tool system). Each of the three jobs is configured with its own persona and
   its own read-only tool allowlist (planning: nav tools, no submit; estimation &
   breakdown: nav tools + their `submit_*`).

## Alternatives considered

| # | Alternative | Why rejected |
|---|---|---|
| 1 | Unify only the model/auth (route today's single-shot estimation/breakdown through the new provider, keep them one-shot) | Delivers billing unification but no capability; the whole point is a repo-aware sizer/decomposer. |
| 2 | Keep the proxy in front of the Orchestrator when the provider is API-key; native only for OAuth (P2) | "How governed is orchestration?" would silently depend on which provider you picked; two transports, two metering stories. |
| 3 | Let estimation/breakdown crawl the repo inline (ii), or inline-with-a-cap (iii) | Reintroduces the "hidden orchestrator spend" ADR-0007 pushed to Scout; re-implements a weaker, ungoverned Scout inside the estimator. |
| 4 | Prompt-for-JSON + validate/repair (S1) or a separate extraction shim (S3) | S1 enforces nothing (free-text drift, the exact agent-runtime weakness); S3 adds a call + seam and half-abandons "the runtime does it". |
| 5 | Keep everything `proxy_governed` (status quo, ADR-0007) | Cannot carry OAuth/other providers at all; and the proxy's zone prompt-injection was found actively wrong for orchestration. |

## Consequences

- **Governance shifts from enforcement to accounting for orchestration.** We lose
  hard pre-flight caps and mid-run throttling on planning/estimation/breakdown. This
  is a deliberate, bounded trade: orchestration turns are short, and the runaway-spend
  risk lives in Workers, which keep the proxy. Native usage + daily-budget counting +
  overrun alarms remain. This is the same trust class already accepted for
  `native_usage` Workers.
- **The `orchestrator-runtime` spec must be rewritten, not amended.** It is currently
  built entirely on pi-through-proxy with an injected planning bearer and
  `usage_source: harness_proxy`; that contract is replaced for orchestration.
- **Structured-output reliability becomes a first-class concern.** An agent turn is
  measurably worse at strict JSON than a json-mode call; the submit-tool boundary is
  the mitigation and must be proven.
- **Two-step estimation flow when investigation is needed** (estimate → Scout →
  re-estimate) instead of one "smart" estimate. Accepted for the visibility it buys.
- **`CONTEXT.md` updated**: Orchestrator Agent, Task Estimation, Task Breakdown Agent,
  Orchestration Tokens, and Planning Chat now describe one native-usage-accounted
  agent runtime. pi stays out of the glossary (implementation), per ADR-0007.

## Rollout

Two OpenSpec changes, planning-first:

- **Change 1 — `pi-native-provider-orchestration`** (reshape of the former
  `pi-orchestrator-native-oauth`): planning only, provider-agnostic. The Orchestrator
  runs planning on its own provider config; `native_usage` accounting from native
  per-turn usage; persona + read-only tools preserved; a clear provider-auth-missing
  state; and the `orchestrator-runtime` spec rewritten off the proxy. Closest to done —
  M2b already runs the runtime; this swaps transport + accounting.
- **Change 2 — `orchestrator-structured-jobs-on-pi`** (gated on Change 1): Task
  Estimation and Task Breakdown migrate to Orchestrator agent turns with `submit_*`
  tools, per-job personas and allowlists, curated context, and Scout escalation.
