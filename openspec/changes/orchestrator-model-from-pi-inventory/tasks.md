## 1. Inventory discovery

- [x] 1.1 Add `discover_orchestrator_models()` in `pi_adapter.py`: run `pi --list-models` under `_prepare_pi_env`, parse the fixed-width table into provider-qualified ids, reject the header row and the "No models available" line, and return models plus sanitized returncode/stdout/stderr.
- [x] 1.2 Reuse the non-model-text guard rather than writing a second one; factor `_looks_like_model_id()` out of `worker_adapters.py` if it must be shared.
- [x] 1.3 Persist discovery evidence (`models`, `discovered_at`, returncode, sanitized output) into the orchestrator `execution_backend_status` details.
- [x] 1.4 Treat an empty result as the authenticate-with-pi state, distinct from a discovery failure.

## 2. Model identity and resolution

- [x] 2.1 Remove `DEFAULT_PI_MODEL` and the `"gpt-5.4"` default in `settings.py`; absent configuration resolves to not configured.
- [x] 2.2 Collapse the resolution chain to `FOREMAN_AI_HQ_ORCHESTRATOR_MODEL` → `config["orchestrator_model"]` → `config["control_plane_model"]` (validated candidate) → not configured. Drop the three legacy env aliases and the estimator/breakdown model env vars.
- [x] 2.3 Reduce `_resolve_pi_provider_model()` to a split; remove the `_pi_default_provider()` fallback. Reject unqualified values at validation rather than repairing them at launch.
- [x] 2.4 Add validation: a value is valid only when provider-qualified and present in persisted discovery evidence.

## 3. One recorded model convention

- [x] 3.1 Add one helper that derives the recorded model from `raw_usage["provider"]`/`raw_usage["model"]`, falling back to the configured value.
- [x] 3.2 Route all six recording sites through it (`pi_adapter.py:231,268,313,409,729,796`) so no path records a provider-stripped id.
- [x] 3.3 Regression test: planning and estimation turns on the same configured model record identical model strings.

## 4. Orchestrator verification

- [x] 4.1 Add verification that runs one `launch_pi_once` sentinel turn with the real persona and tool allowlist; reuse `SENTINEL_PROMPT`/`SENTINEL_RESPONSE`.
- [x] 4.2 Pass only when the sentinel matched **and** a token turn was recorded; record spend with `usage_kind="adapter_verification"`.
- [x] 4.3 Persist sanitized pass/fail evidence; mark verification stale when the model changes without blocking the save.

## 5. Settings surface

- [x] 5.1 Rewrite `ControlPlaneSettingsRequest`: one `orchestrator_model` field validated against the inventory; drop provider, base URL, API key, API key env, and `apply_to_estimator_breakdown`.
- [x] 5.2 Save writes the orchestrator model to every orchestration job; surface any diverging per-job config key as a warning with a reset action.
- [x] 5.3 Save revalidates against a freshly discovered inventory and rejects a value no longer present.
- [x] 5.4 Delete `CURATED_CONTROL_PLANE_MODELS` and the OpenRouter preset defaults in `operator_config.py`.
- [x] 5.5 Replace the connection-test route with the verification route.
- [x] 5.6 Rewrite `ControlPlaneSettings.jsx`: inventory dropdown with context/thinking columns, discovery timestamp, Refresh, Verify, and the authenticate-with-pi empty state. No provider, base URL, or API key fields.
- [x] 5.7 Update the React settings handoff in `react_shell.py` to project inventory and verification state instead of curated models and key presence.

## 6. Readiness and gating

- [x] 6.1 Replace `_control_plane_setup_state()`: ready means a configured model present in persisted discovery evidence — never `bool(os.getenv(api_key_env))`.
- [x] 6.2 Add a not-configured gate on board, launch, and the four orchestration jobs, reading persisted state only; keep sign-in, all settings, sessions, reports, and alarms reachable.
- [x] 6.3 Verify a Recorded Demo Run passes the gate by seeding discovery evidence as scenario state, with no environment bypass.
- [x] 6.4 Rename the `execution_backend_status` key to `orchestrator_model` with migration, or keep the key and change only its label — decide during implementation.

## 7. Agent Review on pi

- [x] 7.1 Add `orchestrator/pi/profile/agent_review.md` persona.
- [x] 7.2 Add `orchestrator/pi/extensions/submit-review.ts` whose schema is the review result schema (summary, recommendation, findings).
- [x] 7.3 Route `_run_agent_review` through `run_pi_structured_job` with `usage_kind="reporting"` and the `read_curated_input` allowlist.
- [x] 7.4 Add the Task Branch diff to the curated payload via `_git_diff_summary()`; keep the payload bounded.
- [x] 7.5 Delete `_parse_agent_review`'s repair path and `_parse_markdownish_agent_review`.

## 8. CLI, proxy, Docker, docs

- [x] 8.1 `htb check` reports pi readiness (installed, authenticated providers, configured model present in inventory) instead of an `LLMClient` round-trip.
- [x] 8.2 Remove the dead planning-session model override in `proxy.py:33-38`; pi no longer traverses the proxy.
- [x] 8.3 Remove the five `FOREMAN_AI_HQ_CONTROL_*` variables from `docker-compose.yml`; document the image as portal/evidence only.
- [x] 8.4 Update the `README.md` env table and `docs/HARNESS.md`.

## 9. Verification

- [x] 9.1 Unit: inventory parsing rejects header and no-models lines; validation rejects bare and pattern values; resolution returns not configured with no default.
- [x] 9.2 Unit: verification fails on sentinel-without-token-row.
- [x] 9.3 Portal: save rejects a stale model absent from a fresh inventory; readiness is false with an API key exported but no pi auth.
- [x] 9.4 Portal: unconfigured blocks board and launch while sessions, reports, alarms, and settings stay reachable.
- [x] 9.5 Smoke: a Recorded Demo Run completes with seeded discovery evidence and no environment bypass.
