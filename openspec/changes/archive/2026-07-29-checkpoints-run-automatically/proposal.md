## Why

`CONTEXT.md` defines a Checkpoint as an evaluation that "runs at a Session boundary." It does
not. `evaluate_checkpoints` (`src/foreman_ai_hq/checkpoints.py:19`) has exactly one caller —
`POST /session/{id}/checkpoint/evaluate` at `src/foreman_ai_hq/routes/sessions.py:98` — and
nothing in the Worker Run lifecycle invokes that endpoint. In normal operation
`checkpoint_results` is always empty.

Three surfaces already depend on results that never arrive:

- the Session Report renders a Checkpoints section (`checkpoint-results-display` spec)
- the Evidence Drawer renders checkpoint evidence
- `defaults/guardrails.yaml:56` configures a `notify_and_checkpoint` enforcement action

This is the fourth instance of the defect class ADR-0012 names: evidence computed, no action
rendered. The other three are `write_capable`, `manual_commit_approval_required`, and
`detect_pr_capability`, all in `task_launch.py`.

## What Changes

`evaluate_checkpoints` runs at Worker Run completion and its results are persisted, so the
glossary definition becomes true and the three existing surfaces render real evidence.

The evaluation is cheap and safe to run on every completion: `evaluate_checkpoints` is a pure
function over an already-built Session Artifact dict, composed of four pure sub-evaluations
(`_budget_health`, `_stuck_loop_score`, `_tool_diversity`, `_timeout_respect`). It performs no
I/O, spends no tokens, and makes no model call. The work is the same four lines the existing
endpoint already runs.

The manual endpoint stays. It is how an operator re-evaluates a Session after guardrail
configuration changes, and it now shares its body with the automatic path rather than being the
only way to produce results.

Deleting checkpoints instead was considered and rejected: it is the larger diff, because it
means removing the display spec, two render paths, a guardrail action, and the existing test
module — to delete a feature whose only defect is that nobody calls it. Amending the glossary to
say "manual" was also rejected, since it leaves all three surfaces permanently dead and records
the gap as intent.

## Capabilities

### Modified Capabilities
- `worker-run-lifecycle`: Worker Run completion evaluates and persists checkpoint results, so
  checkpoint evidence exists for every completed run rather than only when an operator calls the
  evaluation endpoint by hand.

## Impact

- **Backend.** Worker Run completion path calls `evaluate_checkpoints` and
  `db.record_checkpoint_result`, reusing the body of `routes/sessions.py:99-105`.
- **Frontend.** None. The Session Report and Evidence Drawer already render results; they begin
  receiving non-empty input.
- **Tests.** New coverage that a completed Worker Run has checkpoint results.
  `tests/budgeting/test_checkpoints.py` is unaffected — the evaluation logic does not change.
- **Docs.** `CONTEXT.md` Checkpoint stays as written; this change makes the existing definition
  accurate.

## Decisions

- **Evaluation runs at Worker Run completion**, not at Session close, because Worker Run
  completion is where the Session Artifact is already assembled and where the Review surfaces
  that render checkpoints are populated.
- **Failure is non-fatal.** A checkpoint evaluation error is recorded and does not fail the
  Worker Run. Checkpoints are advisory evidence; a failure to evaluate them must not destroy
  run evidence that already exists.
