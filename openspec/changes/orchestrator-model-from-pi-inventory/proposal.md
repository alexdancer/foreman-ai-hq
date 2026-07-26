## Why

ADR-0009 moved the Orchestrator onto pi running on its own provider. The operator-facing
configuration never followed. `/settings/control-plane` still collects a provider, base
URL, API key, and API key env name — the shape of an OpenAI-compatible HTTP connection —
plus a curated dropdown of ten hardcoded models. For orchestration, almost none of it is
real:

- **`control_plane_provider` is inert.** `_resolve_pi_provider_model()` takes only the
  model string, splits on `/`, and otherwise falls back to pi's own `defaultProvider`.
  Nothing passes the configured provider to pi.
- **Base URL and API key are read only by `LLMClient`**, which orchestration no longer
  uses.
- **`CURATED_CONTROL_PLANE_MODELS` names providers that are not pi provider ids.**
  `("openrouter", "anthropic/claude-sonnet-5")` resolves correctly only by accident: the
  OpenRouter namespace happens to parse as a pi provider.

The consequences compound into a page that can lie in both directions. **Test
control-plane connection** exercises `LLMClient`, so it can pass green against a provider
the Orchestrator will never call. **Setup Overview** computes readiness as
`bool(os.getenv(api_key_env))` (`portal.py:1604`), so exporting an API key marks the
Orchestrator "ready" on a machine where pi has never been logged in. And the three pi
launch paths disagree on what to record: `launch_pi_once` and the ACP conversation
persist the provider-stripped `model_id`, while `run_pi_structured_job` persists the full
`provider/model`, so planning turns and estimation turns land under different model
strings and fragment the per-model Estimation Coefficients.

Meanwhile pi already exposes exactly the surface this setting needs. `pi --list-models`
returns provider, model, context window, max output, and thinking/image support, filtered
to providers the operator is actually authenticated with; against an empty agent dir it
returns "No models available. Use /login…" rather than a catalog. It runs offline in
under a second.

Per ADR-0010: **pi's inventory is the sole authority for the Orchestrator model, and an
Orchestrator that is not configured against it does not operate.**

## What Changes

- **One Orchestrator Model drives all four orchestration jobs** — planning, Task
  Estimation, Task Breakdown, and Agent Review. The `apply_to_estimator_breakdown`
  checkbox is removed; saving writes every job. Per-job config keys survive unrendered,
  and a divergent override surfaces as a warning rather than a normal read-only row.
- **The model is a provider-qualified pi id from the discovered inventory.** Bare names,
  fuzzy patterns, `CURATED_CONTROL_PLANE_MODELS`, and the `"gpt-5.4"` code default are
  all removed. A stored value absent from the inventory is *not configured*, never
  repaired by inference. `_resolve_pi_provider_model()`'s `defaultProvider` fallback goes.
- **Discovery follows the Worker Adapter pattern.** Explicit refresh runs
  `pi --list-models`, parses it under a non-model-text rejection guard, and persists
  evidence with a timestamp. Save re-validates live so a stale cache cannot persist an
  unrunnable setting.
- **Verification runs a real sentinel pi turn** and passes only if the sentinel matched
  *and* a token turn was recorded — the two-part bar Worker Adapters already clear.
  Replaces the `LLMClient` connection test.
- **Accounting reflects what ran.** All three pi paths record one convention, taken from
  pi's own `raw_usage` provider and model, falling back to the setting only when pi emits
  no evidence.
- **Agent Review and `htb check` move onto pi.** Agent Review becomes a `submit_review`
  structured job over a curated payload plus the Task Branch diff, with no live
  repository tools; `_parse_markdownish_agent_review` is deleted. `htb check` reports pi
  readiness.
- **Not configured blocks orchestration.** The board, launches, and all four orchestration
  jobs gate on a configured Orchestrator. Login, every settings page, and read-only
  evidence (sessions, reports, alarms) stay reachable so a lapsed provider token cannot
  hide the operator's own audit trail.
- **The provider/base-URL/API-key trio loses its settings page** but stays in code serving
  `proxy_governed` Workers via the Harness Proxy, per ADR-0009.
- **Docker stops advertising dead config.** The five `FOREMAN_AI_HQ_CONTROL_*` variables
  are removed from `docker-compose.yml` and the image is documented as portal/evidence
  only; it ships no Node, no pi, and no provider auth.
- **The resolution chain collapses from ten sources to two:**
  `FOREMAN_AI_HQ_ORCHESTRATOR_MODEL` then `config["orchestrator_model"]`, then not
  configured. The three legacy env aliases and the estimator/breakdown model env vars are
  dropped.

## Capabilities

### Modified Capabilities
- `orchestrator-model`: the Orchestrator Model is a provider-qualified pi id constrained
  to pi's discovered inventory; there is no code default; one model serves all four
  orchestration jobs; token turns record the model pi resolved; an unconfigured
  Orchestrator blocks orchestration while leaving settings and read-only evidence
  reachable.
- `control-plane-model-connection`: the direct provider connection is no longer the
  orchestration model connection and loses its operator-facing settings surface; it is
  retained solely as Harness Proxy upstream configuration for `proxy_governed` Workers.
  The curated model list, the portal-managed API key entry path, and the connection test
  are retired for orchestration.

## Impact

- **Backend.** `settings.py` (resolution chain, default removal), `pi_adapter.py`
  (`_resolve_pi_provider_model`, model recording across all three paths, inventory
  discovery, sentinel verification), `routes/portal.py` (`ControlPlaneSettingsRequest`,
  `CURATED_CONTROL_PLANE_MODELS`, save/test routes, `_control_plane_setup_state`),
  `routes/react_shell.py` (settings handoff), `routes/tasks.py` (Agent Review → pi),
  `cli.py` (`htb check`), plus a new gate on board/launch/orchestration routes.
- **Orchestrator profile.** New `agent_review.md` persona and `submit-review.ts` extension
  alongside the existing estimate/breakdown pair.
- **Frontend.** `ControlPlaneSettings.jsx` rewritten: no provider, base URL, or API key
  fields; inventory dropdown with refresh and timestamp; verification action; empty-auth
  state directing the operator to `pi /login`.
- **Dead code.** `proxy.py`'s planning-session model override; the OpenRouter preset
  defaults in `operator_config.py`.
- **Docs.** `README.md` env table, `docker-compose.yml`, `docs/HARNESS.md`.

## Decisions

- **Thinking level** defers to pi's default. The operator's `~/.pi/agent/settings.json`
  already carries `defaultThinkingLevel`, and pi is the authority on how to run its own
  model. Exposing a second control means persisting it, validating it against the inventory
  row's advertised thinking support, and reconciling it with pi's default — for a value no
  operator has asked to vary per Task. Add it when per-Task thinking is a real request.
- **Gate placement** is a shared FastAPI dependency, matching the existing
  `Depends(require_portal_auth)` pattern the routes already use. It reads persisted discovery
  evidence, so Recorded Demo Runs seed it as ordinary scenario state with no environment
  bypass.
- **Status record key** stays `"control_plane_model"`; only the operator-visible label
  changes. It is an internal `execution_backend_status` row id with 25 references in `src/`,
  invisible to operators, and renaming it costs a migration for no behavioural gain. A
  comment marks it as legacy naming so the next reader does not mistake it for live
  control-plane concept.
