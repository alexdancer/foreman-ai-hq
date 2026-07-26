## 1. Map before deleting

- [ ] 1.1 Map `estimate_decision.py` (853 lines, 76 Scout references): which functions serve the Scout apply loop (`_claim_initial_reestimate`, `_claim_retry_reestimate`, `_apply_reestimate_result`, `apply_reestimate`, `dismiss_reestimate`) versus paths reused by non-Scout flows (`acknowledge_low_confidence`, `apply_manual_estimate`). Do not delete before this boundary is explicit.
- [ ] 1.2 Map the 53 Scout references in `needs_you.py` for the same reason.
- [ ] 1.3 Decide the fate of existing rows with `task_kind == "scout"`: migrate to `implementation`, archive, or leave readable as history.

## 2. Intake decision replaces the threshold

- [ ] 2.1 Add the intake decision to the orchestrator contract: a structured `single_task` versus `needs_breakdown` result carrying a reason.
- [ ] 2.2 Persist the decision and reason as intake provenance on the resulting Task or Proposed Task Breakdown; surface it on the card.
- [ ] 2.3 Remove `_requires_task_breakdown_review()`'s `len(description.split()) >= 120` rule; route from the recorded decision. Markdown paste and upload continue to force review unconditionally.
- [ ] 2.4 Guard the shortcut: a source judged `needs_breakdown` must never produce a single Task.

## 3. Chat as the only front door

- [ ] 3.1 Delete the Short Task Intake panel from `Board.jsx` and the short-intake endpoint's form surface in `routes/tasks.py`.
- [ ] 3.2 Remove the `task_kind` intake control and its validation branch.
- [ ] 3.3 Add file attachment to the chat composer with multipart submit for the `.md` case; preserve file-over-text precedence and existing validation messages.
- [ ] 3.4 Reject invalid attachments before starting a turn so no spend is recorded for a rejected submission.

## 4. Board pane layout

- [ ] 4.1 Extract `PlanningChat.jsx` into a pane component usable inside the board, keeping the standalone route working until the pane ships.
- [ ] 4.2 Render the pane on the Pipeline Surface (expanded default) and Execution Floor (collapsed rail default), with an operator collapse/expand control that persists per surface.
- [ ] 4.3 Add split-view CSS; collapse rather than compress below the width where board content stops being legible.
- [ ] 4.4 Verify the pane renders conversation and intake only — no Task columns, Worker Run panes, or review queues.
- [ ] 4.5 Confirm the Evidence Drawer retains its width on the Floor with the pane collapsed.

## 5. Post-turn board refresh

- [ ] 5.1 Refresh board content once when a planning turn completes, regardless of `automation.live_refresh_enabled`.
- [ ] 5.2 Confirm the refresh does not start or alter background polling.

## 6. Retire the Scout

- [ ] 6.1 Reduce `CANONICAL_TASK_KINDS` to `{implementation, acceptance_verification}`; keep `read_task_kind` tolerant of legacy `scout` metadata for historical rows.
- [ ] 6.2 Remove `read_only_profile_required` from `task_launch.py` and `launch_guardrails.py`; keep the plain `read_only` flag, which other paths use.
- [ ] 6.3 Remove `_read_only_launchable()` and the `kind == "codex"` gate from `adapter_readiness.py`, plus `read_only_launchable`/`read_only_reasons` from the readiness result.
- [ ] 6.4 Remove the Scout apply loop from `estimate_decision.py` per the 1.1 boundary; keep acknowledge and manual-estimate paths.
- [ ] 6.5 Remove Scout entries and the linked-Scout action from `needs_you.py`.
- [ ] 6.6 Remove Scout proposal rules from `task_slicing_policy.py` and `task_breakdown.py`, and the Scout branch in `estimation.py`; keep `investigation_recommended`.
- [ ] 6.7 Remove the Scout candidate kind from Task Breakdown Review.

## 7. Low confidence routes to the chat

- [ ] 7.1 Replace the linked-Scout action in the low-confidence Needs You entry with an action that opens the Planning Chat for the project, question loaded and Task identified.
- [ ] 7.2 Keep acknowledge and manual-estimate actions unchanged; keep the `0.60` threshold and its boundary behaviour.
- [ ] 7.3 Confirm no investigation Task is created and no automatic re-estimation spend occurs.

## 8. Docs

- [ ] 8.1 Remove the Scout paragraphs from `docs/HARNESS.md`, including the Scout-compatible-profile line.
- [ ] 8.2 Update `docs/TODO.md` and any demo runbook referencing Scout or Short Task Intake.
- [ ] 8.3 On archive, remove `openspec/specs/scout-tasks/spec.md`.

## 9. Verification

- [ ] 9.1 Unit: intake routing derives from the recorded decision, not a word count; a `needs_breakdown` source never yields a single Task.
- [ ] 9.2 Unit: `CANONICAL_TASK_KINDS` excludes `scout`; legacy scout metadata still reads without error.
- [ ] 9.3 Unit: launch guardrails no longer require a read-only profile; non-Codex adapters are unaffected by the removal.
- [ ] 9.4 Portal: Markdown paste and `.md` attachment through the composer both reach Task Breakdown Review with intake source preserved.
- [ ] 9.5 Portal: low-confidence Needs You offers acknowledge, manual estimate, and investigate-in-chat, and creates no Task.
- [ ] 9.6 Portal: the board has no intake form; the pane is expanded on Pipeline and collapsed on Floor.
- [ ] 9.7 Portal: a completed turn refreshes the board with background live refresh disabled.
- [ ] 9.8 Recorded Demo Run passes with intake driven through the chat pane.
