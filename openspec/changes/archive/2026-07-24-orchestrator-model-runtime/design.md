## Context

The harness has three model layers, and pi has been quietly wedged into the
first with no setting of its own:

| Layer | Used by | Model source (today) | Reality |
|---|---|---|---|
| Control plane | estimator, task breakdown, agent review, reports | `control_plane_model` | works |
| Planning orchestrator (pi) | Planning Chat | — nothing — | forwards literal `"proxy"` |
| Worker | OpenCode / Claude Code / Codex | adapter allowed models | works |

`estimator_model` and `task_breakdown_model` (`settings.py:22-23`) already prove
the "same connection, different model per job" pattern; `orchestrator_model`
sits beside them.

Two roads reach the model, with different governance — this is the crux:

```
  estimation ─┐
  breakdown  ─┼─▶ llm_client.acompletion ──────────▶ upstream
  agent review┘    system prompt INTACT · response_format json_object
                   no zone governance

  pi (Planning) ─▶ HTTP /v1 ─▶ apply_governance ─▶ llm_client ─▶ upstream
                               system prompt REPLACED · max_tokens clamped
                               tools filtered · metered
```

Breakdown works *because* it never crosses the governed proxy. That is exactly
why pi's persona doesn't survive and breakdown's JSON instruction would not
either, if it were moved onto the governed road.

## Goals / Non-Goals

**Goals**
- Planning Chat runs with the correct model and an intact persona.
- The orchestrator has one model setting, distinct from Worker adapter models,
  backing chat + estimation + breakdown.
- `control_plane_model` retires with config back-compat.

**Non-Goals**
- Estimation/breakdown do NOT become pi agent turns (see Decision 3).
- No separate provider block for planning (connection stays shared).
- No Worker-layer change.

## Decisions

**1. Fix model substitution at the proxy, keyed on session kind.**
The governed proxy resolves an orchestrator/planning session's model from
`orchestrator_model`, not from `request["model"]`. pi's `"proxy"` string stops
reaching upstream. Rejected: fixing pi's `models.json` to send the real model —
it hard-codes the model into a git-tracked profile and splits the source of
truth away from the operator setting.

**2. Governance composes the system prompt; it does not replace it.**
`_rewrite_system_prompt` (`governance.py:59-63`) becomes additive: the caller's
system message (pi's persona, or breakdown's "return JSON") is the base, and the
zone guidance is appended after it.

```
system = <caller system prompt>      ← identity / contract, always
         + <zone guidance>            ← budget pressure, additive
```

Under red zone the orchestrator still gets "be terse, deliver what you have" but
never stops being the orchestrator. Rejected: exempting planning sessions from
governance — that also discards max_tokens clamping and tool filtering and makes
planning the one unmetered path into the models, discarding M2b on purpose.
Note: this changes behavior for *every* governed caller including workers, so it
carries its own regression pass (a worker under red zone now keeps its base
prompt + red guidance rather than red guidance alone).

**3. Unify the MODEL, not the RUNTIME (Reading 1 over Reading 2).**
Estimation and task breakdown keep calling `llm_client.acompletion` directly and
only change which setting they read (`orchestrator_model`). They do NOT route
through the conversational pi agent runtime.

Rejected for now — **Reading 2: run estimation/breakdown as pi agent turns.**
Tempting because pi already has `read`/`grep`/`find`/`ls` scoped to the project
root, so a repo-aware estimator beats one guessing from a description, and the
`estimator-project-context` spec documents that itch. Not taken because:

- Breakdown parses strict JSON (`task_breakdown.py:145,233` — `response_format:
  json_object`, `temperature: 0`). A conversational agent emitting JSON is
  materially less reliable; this spends reliability to buy repo-awareness.
- The persona (`one question per turn`, `stay scoped to planning`) is wrong for a
  batch estimation call — Reading 2 needs per-job personas over one runtime.
- Routing JSON jobs through the governed proxy hits the *same* prompt-replacement
  trap as Finding B; Decision 2 is a prerequisite for Reading 2, not a side
  quest.
- One estimate becomes an agent turn with tool calls — latency and cost.

Reading 1 → Reading 2 later is cheap; the reverse (estimation already depends on
the agent runtime) is a one-way door. Repo-aware estimation stays reachable via
`estimator-project-context` (repo context fed *into* the structured call)
without making the estimator an agent. Revisit Reading 2 only if dogfooding
shows blind estimation actually hurts.

**4. Retire `control_plane_model` with config back-compat.**
Once `orchestrator_model` backs every caller, remove `control_plane_model` across
its ~28 references. A `.htb/config.toml` that still names `control_plane_model`
resolves to `orchestrator_model` (back-compat read), so existing operators are
not broken on upgrade.

**5. Connection scope stays shared for this slice.**
`orchestrator_model` differs from the control-plane connection only by model
name; provider, base URL, and API key are shared. A separate provider block for
planning (e.g. control plane on local Ollama, planning on a hosted
conversation-grade model) is a named later option, not this slice.

**6. Orchestration spend category.**
Planning/orchestration turns meter under a single `orchestration` category
(replacing control-plane spend), separate from `worker_execution`, using the
existing `usage_kind`/`spend_category` fields in `token_turns`. No new schema.
This is why proposal question #3 (budget) collapses under either reading:
planning spend *is* orchestration spend.

## Risks / Trade-offs

- **Decision 2 touches all governed callers.** A worker's effective system prompt
  changes shape (base + zone, not zone-only). Bounded by a regression pass across
  zones and caller types.
- **Reading 1 leaves estimation blind** to the repo unless
  `estimator-project-context` is wired. Accepted; cheaper and more reliable than
  Reading 2, and reversible.
- **Retirement blast radius (~28 sites)** across CLI, portal, nav payload, agent
  review. Bounded by back-compat and a stale-reference sweep.

## Migration Plan

Two independent bug-fix slices first (model substitution; prompt composition) —
they fix a production-broken surface and depend on nothing else. Then the
`orchestrator_model` setting, the estimation/breakdown model-read swap, the
`control_plane_model` retirement, and the spend category. Rollback of the
setting work leaves the two bug fixes in place.

## Open Questions

- Resolved: model unification is by setting, not runtime (Decision 3); persona
  composes with zone guidance (Decision 2); connection stays shared (Decision 5);
  budget is one orchestration category (Decision 6).
- Deferred: separate provider block for planning; Reading 2 (agent-runtime
  estimation/breakdown); whether `orchestrator_model` should later gain its own
  provider/base-url/key.
