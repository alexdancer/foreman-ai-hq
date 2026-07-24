## Why

The pi orchestrator drives the governed Planning Chat, but it has no model
setting of its own — and two defects make it unusable today, both found by
driving a real turn through the running stack (proxy on `:8899`, upstream at
`localhost:11434`) with a logging stub on the upstream port:

- **Model substitution never fires.** `llm.py:161` is
  `model = request.get("model") or settings.control_plane_model`. pi always
  sends a model (`"proxy"`, from its `models.json`), so the `or` never triggers
  and the literal `"proxy"` is forwarded upstream. Changing the Control Plane
  model swaps pi's provider, base URL, and API key — but not the model. The
  operator has to change the *control plane* setting to affect *planning*, and
  even then the model name is wrong.
- **Governance eats the persona.** The pi wrapper injects `orchestrator.md` as
  the system prompt (`pi_adapter.py:44`), then `governance._rewrite_system_prompt`
  (`governance.py:59-63`) *replaces* `messages[0]` with the zone prompt. The
  stub confirmed upstream sees the green-zone text ("Be thorough: write tests,
  add documentation, explore alternatives") with no `PERSONA_MARKER` and none of
  the planning contract. The whole M2b persona slice is silently defeated the
  moment a turn crosses the governed proxy — and the zone prompt tells the
  *planning* orchestrator to write code, the opposite of its contract.

Separately, the operator has asked that the pi orchestrator become the harness's
orchestration model — the thing that also backs estimation and task breakdown —
and that `control_plane_model` retire once the replacement is in place.

## What Changes

- **Fix model substitution (bug).** The governed proxy SHALL resolve the model
  for an orchestrator/planning session from the orchestrator model setting, not
  from the literal string pi happens to send. pi stops forwarding `"proxy"`
  upstream.
- **Fix system-prompt composition (bug).** Governance SHALL *compose* the zone
  guidance onto the caller's system prompt instead of replacing it: the persona
  (or any caller's own system message) is preserved as the base, and the zone
  guidance is appended. Budget pressure still shapes behavior (terser under red)
  without erasing identity or a caller's structured-output instruction. This
  touches every governed caller, including workers, so it carries its own test
  pass.
- **Add `orchestrator_model` (new setting).** A model setting for the
  orchestrator, sibling to the existing `estimator_model` and
  `task_breakdown_model` (`settings.py:22-23`), resolved from the same config
  and env precedence. Estimation and task breakdown read `orchestrator_model`
  in place of `control_plane_model`. Connection scope (provider/base-url/key)
  stays shared with the control plane for this slice; only the model name is
  distinct.
- **Retire `control_plane_model`.** Once `orchestrator_model` backs every caller,
  `control_plane_model` is removed across its ~28 references (`cli.py` `htb
  check`, the portal settings page + connection test, `react_shell.py` nav
  payload, agent review, `tasks.py`), with config back-compat so existing
  `.htb/config.toml` files that still name `control_plane_model` resolve to
  `orchestrator_model`.
- **Orchestration spend (narrowed).** Planning/orchestration turns keep their
  existing spend classification (planning turns as `planning` spend, rolling under
  the existing summary keys) and stay separate from `worker_execution`. Decision
  2026-07-24: do NOT introduce a new operator-visible `orchestration` rollup key —
  the turn-level separation already existed, so this is a no-op at the db layer
  beyond confirming it holds.

## Capabilities

### New Capabilities
- `orchestrator-model`: the orchestrator model setting and its resolution — one
  model, distinct from Worker adapter models, backing Planning Chat, estimation,
  and task breakdown; metered as orchestration spend.

### Modified Capabilities
- `proxy-governed-orchestration`: the governed proxy resolves an
  orchestrator/planning session's model from the orchestrator model setting, and
  governance composes zone guidance onto the caller's system prompt instead of
  replacing it.

## Impact

- **Backend.** `settings.py` gains `orchestrator_model` and back-compat for
  `control_plane_model`; `llm.py:161` model resolution; `governance.py:59-63`
  prompt composition; estimation/breakdown/agent-review model reads; `cli.py`
  `htb check`; portal settings save + connection test; `react_shell.py` nav
  payload. ~28 `control_plane_model` sites.
- **Frontend.** The Control Plane model settings surface becomes the Orchestrator
  model surface (label + field name); the connection-test flow is unchanged in
  shape.
- **Docs.** `README.md`, `docs/DEPLOY.md`, and any `.htb/config.toml` guidance
  that names `control_plane_model` update to `orchestrator_model` with the
  back-compat note.
- **Deferred (named, not surprises).**
  - **Estimation/breakdown do NOT move onto the pi agent runtime.** They keep
    calling `llm_client.acompletion` directly with `response_format:
    json_object` and strict parsing; they only change *which model setting* they
    read. Routing structured JSON jobs through the conversational pi runtime
    (per-job personas, tool-augmented repo-aware estimation) is recorded in
    `design.md` as an explicitly deferred alternative (Reading 2). Repo-aware
    estimation is still reachable via the existing `estimator-project-context`
    path — feeding repo context into the structured call — without making the
    estimator an agent.
  - **Connection scope stays shared** with the control plane (same
    provider/base-url/key). A separate provider block for planning is a later
    option if planning and control-plane want different providers.

## Impact — sequencing

The two bug fixes (model substitution, prompt composition) are independent of the
setting work and fix a surface that is broken in production now; they land first
and can ship without the `orchestrator_model`/retirement work. The
`orchestrator_model` setting, the `control_plane_model` retirement, and the spend
category follow.
