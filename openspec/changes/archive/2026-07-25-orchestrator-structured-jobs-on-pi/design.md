## Context

After `pi-native-provider-orchestration`, the Orchestrator runs planning on its own
provider with native-usage accounting, a tracked persona, a read-only tool allowlist,
and a verified native-usage recorder. Estimation and task breakdown still run as
single-shot `llm_client.acompletion(..., response_format: json_object)` calls with
strict parsing — the "single-shot control-plane steps" ADR-0007 contrasted the
Orchestrator against. ADR-0009 (decision 1) reverses that: they become Orchestrator
agent turns.

Grounded facts (installed pi `0.81.1`): no native `response_format`/output-schema
mode, but a full custom-tool system (`createTool`/`defineTool`/`registerTool`,
`CustomTool`) with `JsonSchema` inputs, and `--tools` allowlisting that already
applies to custom tools.

## Goals / Non-Goals

**Goals**
- Estimation and breakdown run as Orchestrator agent turns on the Orchestrator's own
  provider, accounted from native usage.
- Structured output is enforced at a submit-tool boundary, not hoped for from free text.
- Curated context by default; deep reading escalates to a Scout.
- Driver-based estimation and the breakdown review contract are preserved verbatim
  downstream.

**Non-Goals**
- Changing the driver/coefficient model, model routing, or Task Breakdown Review.
- Letting the jobs write code, run a shell, or launch Workers.
- Inline repository crawling inside a job (that is a Scout).

## Decisions

**1. Estimation and breakdown are Orchestrator agent turns (S2 submit-tool).** Each
job runs as a one-shot `pi -p --mode json` turn on the Orchestrator's provider, with
its own persona, its own read-only tool allowlist plus a single submit tool, and it
terminates by calling that submit tool. The submit tool's `JsonSchema` parameters are
the result schema, validated at the tool boundary. Rejected: prompt-for-JSON +
validate/repair (S1) — enforces nothing, the exact agent-runtime weakness; and a
separate extraction shim (S3) — adds a call and a seam and half-abandons "the runtime
does it."

**2. Structured-output failure is explicit, never fabricated.** If a run ends without
a valid submit call, the system surfaces a structured-output failure onto the existing
failure/manual-recovery paths (manual estimate; breakdown-failed review). It does not
coerce prose into a result or fall back to a heuristic — consistent with the existing
"no silent heuristic estimate / no deterministic markdown split" rules.

**3. Curated context; Scout escalation (i-pure).** Jobs receive the same curated
lightweight context they get today (language, framework, test command, top-level
structure, docs) and are not given free rein over repository source. When a job cannot
produce a confident result, it emits an investigation-recommended signal that becomes
a governed, read-only Scout Task — the reading is a visible card, never hidden
orchestration spend. (For estimation this is the existing low-confidence → Scout path;
for breakdown it is the existing `scout` candidate proposal.)

**4. Downstream contracts preserved.** `submit_estimate`'s schema carries the
Estimation Drivers (files-to-read/modify, expected turns, test-needed, complexity,
confidence, shadow token estimate), not a raw magnitude — so driver arithmetic and
coefficients are unchanged. `submit_breakdown`'s schema carries the Proposed Task
Breakdown contract (candidates, kinds, constraints, verification, global summary,
rejected items) consumed by Task Breakdown Review unchanged.

**5. Per-job personas and tools are tracked config.** The personas and allowlists live
under the pi profile as tracked product config (same shape as the planning persona),
no secrets. The submit tools are tracked first-party pi extensions.

## Risks / Trade-offs

- **Termination discipline.** The run must reliably end by calling the submit tool;
  if pi emits prose instead, decision 2 makes that a bounded failure, not a fabricated
  result. Verify pi's behavior and tune the persona/stop handling.
- **Structured-output reliability vs. json-mode.** The submit-tool boundary is the
  mitigation for agent-runtime JSON drift and must be proven against the golden
  decomposition/estimation fixtures.
- **Latency/cost.** Agent turns cost more than a single json call; curated context +
  Scout escalation keeps them bounded, and native-usage accounting keeps them visible.
