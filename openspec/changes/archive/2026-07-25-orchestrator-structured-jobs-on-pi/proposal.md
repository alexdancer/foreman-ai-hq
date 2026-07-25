## Why

The operator wants the Orchestrator to *own* estimation and task breakdown, not just
share their model name — an estimator and decomposer that reason over project context
the way the planner does, on the operator's own provider (ADR-0009, decision 1).
Today they are single-shot `llm_client.acompletion(..., response_format: json_object)`
calls (`task_breakdown.py:147`), disconnected from the Orchestrator runtime: no tool
access, no loop, and their own transport.

`pi-native-provider-orchestration` moved **planning** onto the Orchestrator's own
provider with native-usage accounting and proved the runtime, persona, tool-scoping,
and native-usage recorder. This change makes **estimation and task breakdown** run on
that same runtime as agent turns — the second half of ADR-0009.

The hard problem is structured output: an agent turn is measurably worse at strict
JSON than a json-mode call. pi has no `response_format` mode but a full custom-tool
system with `JsonSchema` inputs, so the schema is enforced at a **submit tool**
boundary (decision S2). And the Scout boundary must hold: these jobs run on curated
context and escalate real code-reading to a visible Scout, never crawl inline
(decision i-pure).

## What Changes

- **Estimation and breakdown run as Orchestrator agent turns**, on the Orchestrator's
  own provider, accounted from native usage as Orchestration Tokens (labeled
  usage kind `estimation` / `task_breakdown`, keeping each job's existing spend
  category), separate from Worker execution spend. They replace
  the single-shot `llm_client` structured calls.
- **Per-job personas and read-only tool allowlists.** Each job is configured with its
  own persona and an allowlist containing only a pathless curated-input reader plus
  that job's submit tool. Neither can crawl the repository, write code, run a shell,
  or launch Workers.
- **Structured output via submit tools.** Each job terminates by calling
  `submit_estimate` / `submit_breakdown`, whose `JsonSchema` parameters *are* the
  result schema; the tool-call arguments are the validated structured result. Free
  text is never treated as the result; a run that never validly submits is a
  structured-output failure (retry / manual path), not a fabricated result.
- **Curated context, Scout escalation.** Jobs run on curated lightweight project
  context and do not crawl arbitrary source inline. A job that cannot produce a
  confident result surfaces an explicit investigation-recommended signal that becomes
  a governed Scout Task.
- **Downstream unchanged.** The estimation submit schema carries the Estimation
  Drivers (not a raw magnitude), preserving driver-based estimation and coefficients;
  the breakdown submit schema carries the Proposed Task Breakdown contract consumed by
  Task Breakdown Review. Routing, review, and calibration are untouched.

## Capabilities

### New Capabilities
- `orchestrator-structured-jobs`: Task Estimation and Task Breakdown run as Orchestrator
  agent turns with per-job personas and read-only tool allowlists, structured output
  enforced through job-specific submit tools, curated context with Scout escalation,
  and native-usage accounting — preserving driver-based estimation and the breakdown
  review contract.

## Impact

- **Backend.** The estimation and task-breakdown call sites move from
  `llm_client.acompletion` structured calls to Orchestrator agent-turn runs
  (`pi_adapter.py` one-shot `pi -p --mode json` + submit tool). New tracked pi
  extensions defining `submit_estimate` / `submit_breakdown` with `JsonSchema` inputs;
  per-job personas and tool allowlists under the pi profile. Native-usage recorder
  reused for estimation/breakdown turns.
- **Tracking.** Estimation and breakdown spend accounted from native usage, labeled
  usage kind `estimation` / `task_breakdown` under their existing spend categories
  (`control_plane` / `task_breakdown`), separate from `worker_execution`.
- **Scout.** Wire the investigation-recommended signal from estimation/breakdown to a
  Scout Task candidate (reuse the existing Scout path).
- **Docs.** `CONTEXT.md` already updated (Orchestrator Agent, Task Estimation, Task
  Breakdown Agent) to describe the agent-turn model.

## Open Questions (for design)

- **Submit-tool robustness:** confirm pi reliably terminates a one-shot run by calling
  the submit tool, and define behavior if it emits prose instead (bounded re-ask vs.
  immediate structured-output failure).
- **Per-job model overrides:** whether `estimator_model` / `task_breakdown_model`
  overrides continue to apply on the agent-turn path (default: yes, they already fall
  back to `orchestrator_model`).
