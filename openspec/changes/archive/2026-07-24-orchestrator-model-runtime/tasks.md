## 1. Bug fix — model substitution (independent, ships first)

- [x] 1.1 In the governed proxy model resolution (`llm.py:161` and its callers in `routes/proxy.py`), resolve an orchestration/`planning`-kind session's upstream model from the orchestrator model setting instead of `request["model"]`, so pi's `"proxy"` placeholder is overridden. Leave Worker model resolution unchanged. — override in `routes/proxy.py:chat_completions` above the stream branch (covers both paths); uses `settings.control_plane_model` for now (section 4 renames to `orchestrator_model`).
- [x] 1.2 Test: a `planning`-session completion whose model is a placeholder forwards the orchestrator model upstream and records usage against it; a Worker-session completion is unchanged. — `tests/api/test_proxy.py::test_chat_completions_planning_session_uses_orchestration_model_not_sent_placeholder`.

## 2. Bug fix — system-prompt composition (independent, ships first)

- [x] 2.1 Change `governance._rewrite_system_prompt` (`governance.py:59-63`) to compose: preserve the caller's system message as the base and append the zone guidance after it, instead of replacing `messages[0]`.
- [x] 2.2 Test: a planning turn keeps the persona (`PERSONA_MARKER` present) with zone guidance appended in green/yellow/red; a turn carrying a JSON instruction keeps it; a Worker turn keeps its base prompt + zone guidance. Cover the "no system prompt present" case (zone guidance still applied).
- [x] 2.3 Regression pass across governed callers (worker + planning) confirming the composed-prompt shape does not break existing zone behavior.

## 3. Orchestrator model setting

- [x] 3.1 Add `orchestrator_model` to `settings.py` as a sibling of `estimator_model`/`task_breakdown_model`, resolved with the same config/env precedence, defaulting to the same value; add back-compat so a config naming `control_plane_model` resolves to `orchestrator_model`.
- [x] 3.2 Point estimation (`estimate_decision.py`, `estimation.py`), task breakdown (`task_breakdown.py`, `routes/tasks.py:1070`), and the proxy orchestration resolution (task 1.1) at `orchestrator_model`.
- [x] 3.3 Test: estimation and breakdown request the orchestrator model over the shared control-plane connection; a legacy `control_plane_model`-only config resolves to `orchestrator_model`.

## 4. Retire control_plane_model

- [x] 4.1 Replace the remaining `control_plane_model` reads with `orchestrator_model`: `cli.py` (`htb check`), `routes/portal.py` (settings save + connection test + agent review), `routes/react_shell.py` (nav payload), `routes/tasks.py`.
- [x] 4.2 Update the Control Plane model settings surface to the Orchestrator model surface (label + field name); connection-test flow shape unchanged.
- [x] 4.3 Stale-reference sweep: no `control_plane_model` remains except the back-compat read; docs (`README.md`, `docs/DEPLOY.md`, `.htb/config.toml` guidance) name `orchestrator_model` with the back-compat note.

## 5. Orchestration spend (narrowed — see design decision)

Decision (2026-07-24): keep orchestration spend under its existing classification
(planning turns as `planning` spend, rolling under the existing summary keys) and
do NOT introduce a new operator-visible `orchestration` rollup key. The turn-level
separation from Worker execution already existed, so section 5 is a no-op at the
db layer beyond confirming that separation holds.

- [x] 5.1 Confirm planning/orchestration turns keep their existing spend classification, stay separate from `worker_execution`, and are excluded from Worker actuals/caps. No new category key added; `db.py` spend-category mapping unchanged. (Devin's `control_plane`→`orchestration` rename reverted per the narrow decision.)
- [x] 5.2 Test: covered by existing `tests/api/test_proxy.py::test_chat_completions_on_planning_session_records_planning_turn_and_budget_governance` and `...does_not_count_against_worker_session_cap`.

## 6. Validation

- [x] 6.1 `openspec validate orchestrator-model-runtime --strict` and `openspec validate --all --strict` green.
- [x] 6.2 `uv run pytest` (1018 passed) and `npm run check` (96 tests + build) green. NOTE: the live end-to-end Planning Chat turn (persona reaches upstream, orchestrator model used) is NOT yet run against a live model backend — verified at the unit/e2e-fake level (`test_governance.py` persona composition + `test_pi_acp_conversation.py` forwards `ORCHESTRATOR_PERSONA_MARKER`). Live run still pending an orchestrator model backend.
