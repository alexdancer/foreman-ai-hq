## 1. Map before deleting

- [x] 1.1 Map `estimate_decision.py` (853 lines, 93 Scout-matching lines): which functions serve the Scout apply loop (`_claim_initial_reestimate`, `_claim_retry_reestimate`, `_apply_reestimate_result`, `apply_reestimate`, `dismiss_reestimate`) versus paths reused by non-Scout flows (`acknowledge_low_confidence`, `apply_manual_estimate`). Do not delete before this boundary is explicit.
- [x] 1.2 Map the 55 Scout-matching lines in `needs_you.py` for the same reason.
- [x] 1.3 Leave existing rows with `task_kind == "scout"` untouched (decided in the proposal); confirm `read_task_kind` and every projection still read them without error, and that no migration is written.

## 2. Intake decision replaces the threshold

- [x] 2.1 Add the intake decision to the orchestrator contract: a structured `single_task` versus `needs_breakdown` result carrying a reason.
- [x] 2.2 Persist the decision and reason as intake provenance on the resulting Task or Proposed Task Breakdown; surface it on the card.
- [x] 2.3 Remove `_requires_task_breakdown_review()`'s `len(description.split()) >= 120` rule; route from the recorded decision. Markdown paste and upload continue to force review unconditionally.
- [x] 2.4 Guard the shortcut: a source judged `needs_breakdown` must never produce a single Task.

## 3. Chat as the only front door

- [x] 3.1 Delete the Short Task Intake panel from `Board.jsx` and the short-intake endpoint's form surface in `routes/tasks.py`.
- [x] 3.2 Remove the `task_kind` intake control and its validation branch.
- [x] 3.3 Add file attachment to the chat composer with multipart submit for the `.md` case; preserve file-over-text precedence and existing validation messages.
- [x] 3.4 Reject invalid attachments before starting a turn so no spend is recorded for a rejected submission.

## 4. Board pane layout

- [x] 4.1 Extract `PlanningChat.jsx` into a pane component usable inside the board, keeping the standalone route working until the pane ships.
- [x] 4.2 Render the pane on the Pipeline Surface (expanded default) and Execution Floor (collapsed rail default), with an operator collapse/expand control that persists per surface.
- [x] 4.3 Add split-view CSS; collapse rather than compress below the width where board content stops being legible.
- [x] 4.4 Verify the pane renders conversation and intake only — no Task columns, Worker Run panes, or review queues.
- [x] 4.5 Confirm the Evidence Drawer retains its width on the Floor with the pane collapsed.

## 5. Post-turn board refresh

- [x] 5.1 Refresh board content once when a planning turn completes, regardless of `automation.live_refresh_enabled`.
- [x] 5.2 Confirm the refresh does not start or alter background polling.

## 6. Retire the Scout

- [x] 6.1 Reduce `CANONICAL_TASK_KINDS` to `{implementation, acceptance_verification}`; keep `read_task_kind` tolerant of legacy `scout` metadata for historical rows.
- [x] 6.2 Remove `read_only_profile_required` from `task_launch.py` and `launch_guardrails.py`; keep the plain `read_only` flag, which other paths use.
- [x] 6.3 Remove `_read_only_launchable()` and the `kind == "codex"` gate from `adapter_readiness.py`, plus `read_only_launchable`/`read_only_reasons` from the readiness result.
- [x] 6.4 Remove the Scout apply loop from `estimate_decision.py` per the 1.1 boundary; keep acknowledge and manual-estimate paths.
- [x] 6.5 Remove Scout entries and the linked-Scout action from `needs_you.py`.
- [x] 6.6 Remove Scout proposal rules from `task_slicing_policy.py` and `task_breakdown.py`, and the Scout branch in `estimation.py`; keep `investigation_recommended`.
- [x] 6.7 Remove the Scout candidate kind from Task Breakdown Review, including the operator's editable kind values.
- [x] 6.8 Remove the `/scout`, `/scout/reestimate`, `/scout/reestimate/retry`, `/scout/reestimate/apply`, and `/scout/reestimate/dismiss` estimate-decision routes and their handlers; keep `/acknowledge` and `/manual`.
- [x] 6.9 Narrow `task_kind` in the board card and task-history projections to `implementation` and `acceptance_verification`, drop the Scout label, and keep legacy rows readable.
- [x] 6.10 Drop the Scout exclusion rule from estimation accuracy metrics; investigation produces no Task actuals to exclude.

## 7. Low confidence routes to the chat

- [x] 7.1 Replace the linked-Scout action in the low-confidence Needs You entry with an action that opens the Planning Chat for the project, question loaded and Task identified.
- [x] 7.2 Keep acknowledge and manual-estimate actions unchanged; keep the `0.60` threshold and its boundary behaviour.
- [x] 7.3 Confirm no investigation Task is created and no automatic re-estimation spend occurs.
- [x] 7.4 Route the structured-jobs investigation-recommended signal to the conversation: update the estimation and breakdown persona text and result handling so the signal becomes an offer to investigate in chat, never a dispatched Task.

## 8. Docs

- [x] 8.1 Remove the Scout paragraphs from `docs/HARNESS.md`, including the Scout-compatible-profile line.
- [x] 8.2 Update `docs/TODO.md` and any demo runbook referencing Scout or Short Task Intake.
- [x] 8.3 On archive, remove `openspec/specs/scout-tasks/spec.md` — its one surviving requirement moves to `needs-you-queue` in this change's deltas, so nothing is lost with the file.
- [x] 8.4 On archive, amend the `orchestrator-structured-jobs` Purpose line, which still says "Scout escalation instead of inline repository crawling" (Purpose text is outside any requirement, so no delta covers it).

## 9. Verification

- [x] 9.1 Unit: intake routing derives from the recorded decision, not a word count; a `needs_breakdown` source never yields a single Task.
- [x] 9.2 Unit: `CANONICAL_TASK_KINDS` excludes `scout`; legacy scout metadata still reads without error.
- [x] 9.3 Unit: launch guardrails no longer require a read-only profile; non-Codex adapters are unaffected by the removal.
- [x] 9.4 Markdown paste and `.md` attachment through the composer both reach Task Breakdown Review with intake source preserved.
- [x] 9.5 Low-confidence Needs You offers acknowledge, manual estimate, and investigate-in-chat, and creates no Task.
- [x] 9.6 The board has no intake form; the pane is expanded on Pipeline and collapsed on Floor.
- [x] 9.7 A completed turn refreshes the board with background live refresh disabled.
- [x] 9.8 Recorded Demo Run passes with intake driven through the chat pane.
