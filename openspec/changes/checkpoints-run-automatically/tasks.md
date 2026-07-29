## 1. Evaluate at Worker Run completion

- [x] 1.1 Extract the evaluate-and-persist body of `routes/sessions.py:99-105` into a reusable function so the automatic and manual paths cannot drift apart.
- [x] 1.2 Call it from the Worker Run completion path once the Session Artifact is available.
- [x] 1.3 Record an evaluation failure as sanitized detail and let the Worker Run complete; checkpoints are advisory and must not destroy existing run evidence.
- [x] 1.4 Keep `POST /session/{id}/checkpoint/evaluate` as the re-evaluation path, now calling the shared function.

## 2. Tests

- [x] 2.1 Add coverage: a completed Worker Run has non-empty `checkpoint_results` with no operator action.
- [x] 2.2 Add coverage: an evaluation failure leaves the Worker Run completed with its other evidence intact.
- [x] 2.3 Add coverage: the manual endpoint re-evaluates and overwrites results after guardrail configuration changes.
- [x] 2.4 Add a guard test that the Session Report Checkpoints section renders for an ordinary completed run, so a future regression to the empty state is caught by the surface that motivated this change.

## 3. Docs

- [x] 3.1 Verify `CONTEXT.md` Checkpoint needs no edit — the definition already says "runs at a Session boundary" and this change makes that true.
- [x] 3.2 Confirm `defaults/guardrails.yaml` `notify_and_checkpoint` now reaches a live evaluation, and state its behaviour in the guardrail docs if it does not.

## Verification

- `openspec validate --all --strict`: 61 passed, 0 failed.
- Full pytest: 1084 passed, 5 skipped (was 1080 passed / 5 skipped before this change).
- Targeted `tests/portal/test_sessions.py`: 10 passed.
- Targeted `tests/workers/test_checkpoints_run_automatically.py`: 2 passed.
- `notify_and_checkpoint` does not yet trigger a live checkpoint save; its behaviour is now documented in `docs/HARNESS.md` and the comments in `guardrails.yaml` / `src/foreman_ai_hq/defaults/guardrails.yaml` have been corrected to match.
