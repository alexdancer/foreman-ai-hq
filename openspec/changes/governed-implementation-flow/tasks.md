## 1. Derive launch mode from Task kind

- [ ] 1.1 Replace the metadata-driven resolution at `task_launch.py:191-192` with derivation from canonical Task kind: `implementation` → write-capable, `acceptance_verification` → read-only.
- [ ] 1.2 Delete the `"standard"` branch and every `launch_mode` string that produces it (`:312`, `:334`, `:353`).
- [ ] 1.3 Ignore `metadata["write_capable"]`, `metadata["read_only"]`, and client-supplied `launch_mode`; a Task launches in the mode its kind requires.
- [ ] 1.4 Delete the codex-only `no_workdir_changes` check at `:833`. It is reachable only in `"standard"` mode, and the write-capable path's adapter-agnostic `has_changes` check at `:1488` supersedes it. Remove it in its own step, not as a side effect of deleting the mode.

## 2. Confirmed verification command

- [ ] 2.1 Make `_detect_test_command` produce a suggestion rather than an authoritative value.
- [ ] 2.2 Add a confirmable test command field to project connect and project settings; persist confirmation state on the project profile.
- [ ] 2.3 Refuse to execute an unconfirmed detected command; `_run_test_command` runs only operator-confirmed configuration.
- [ ] 2.4 Do not grandfather already-connected projects: a detected-but-unconfirmed command blocks the next write-capable launch, and the block response carries the confirm affordance inline.

## 3. Approve commit

- [ ] 3.1 Replace the write-only `manual_commit_approval_required` flag at `:1520` with state the Review surface reads.
- [ ] 3.2 Extend the Review Disposition action enum at `routes/tasks.py:94` with `approve_commit`.
- [ ] 3.3 Implement the handler: create the Harness-owned commit via `_create_harness_commit`, record operator authorization and the reason verification did not clear it.
- [ ] 3.4 Offer the action on both the missing-command and verification-failed paths.
- [ ] 3.5 Surface it in the Evidence Drawer beside Agent Review, Mark Done, and Block.

## 4. Open PR

- [ ] 4.1 Extend the Review Disposition action enum with `open_pr`.
- [ ] 4.2 Implement `gh pr create` from the Task branch with task, session, token, and verification evidence in the body.
- [ ] 4.3 Gate the action on the existing `detect_pr_capability` result; state the reason when unavailable rather than hiding it silently.
- [ ] 4.4 On failure, preserve the commit and Task state and record a sanitized reason; do not change lifecycle state.
- [ ] 4.5 Surface the action in the Evidence Drawer once a Harness-owned commit exists.

## 5. Base branch

- [ ] 5.1 Add a confirmable base branch to project connect and project settings, detected from the repository default and editable like the verification command.
- [ ] 5.2 Pass it as the start point in `_create_task_branch`: `git checkout -b <branch> <base>`. Do not check out the base first; the start-point form is what makes this stateless.
- [ ] 5.3 Fail launch with a clear reason when the configured base branch does not exist.
- [ ] 5.4 Advance the base by fast-forward on the acceptance action only; leave it untouched on Approve commit and Open PR.
- [ ] 5.5 On a base that cannot fast-forward, refuse, author no merge commit, leave the Task branch and commit intact, and raise a Needs You entry naming the divergence.
- [ ] 5.6 Restore the operator's original branch after the Harness-owned commit; the Task branch stays available by name.
- [ ] 5.7 Refuse write-capable launch on a non-git connected project. Do not refuse at connect time — read-only Chat investigation of a non-git repository stays supported.

## 6. Dirty-tree recovery

- [ ] 6.1 The cleanliness guardrail now blocks real launches; ensure the reason names the offending paths.
- [ ] 6.2 Blocking message only. No Needs You entry and no inline stash or commit action — the Harness does not mutate the operator's working tree on an unrequested action.

## 6b. Queue disposition backpressure

- [ ] 6b.1 Add a `Board Run Queue` stop condition: a Task launched by this queue run is awaiting operator disposition in Review. Serialization moves from Worker Run terminal state to Task terminal state, because this change makes Review non-terminal.
- [ ] 6b.2 Record it as an ordinary queue stop reason in automation evidence, alongside the existing reasons in `board_automation.py`.
- [ ] 6b.3 Do not add an auto-approve policy option. `Run Automation Policy`'s "no automatic Review disposition" rule stays as written.
- [ ] 6b.4 Confirm Auto Review still reads the Task Branch diff correctly when the diff is uncommitted, since Auto Review fires before Approve commit. Fix the diff capture if it assumes a commit range; do not reorder the actions.

## 7. Tests

- [ ] 7.1 Rewrite `tests/workers/test_write_capable_launch.py` to exercise the real default instead of injecting `launch_mode` by hand.
- [ ] 7.2 Add coverage: an `implementation` Task creates a branch and commits without any metadata flag.
- [ ] 7.3 Add coverage: an `acceptance_verification` Task launches read-only, creates no branch, and fails on repository mutation.
- [ ] 7.4 Add coverage: no verification command → Approve commit available → commit created with recorded authorization.
- [ ] 7.5 Add coverage: verification failed → both Approve commit and Block available.
- [ ] 7.6 Add coverage: Open PR offered only after a commit and with capability; failure preserves the commit.
- [ ] 7.7 Add coverage: two Tasks launched in sequence each branch from the base, and the second branch does not contain the first's commit.
- [ ] 7.8 Add coverage: acceptance fast-forwards the base; a diverged base is refused with the Task branch and commit intact.
- [ ] 7.9 Add a guard test that no Task in Review records a pending decision with no available action.
- [ ] 7.10 Add coverage: a queue run whose Task lands in Review awaiting Approve commit stops with that reason and launches no second Task.
- [ ] 7.11 Add coverage: HEAD is back on the operator's original branch after a write-capable run completes.
- [ ] 7.12 Add coverage: a non-git connected project is refused at write-capable launch and still permitted for read-only launch.

## 8. Docs

- [ ] 8.1 Update `CONTEXT.md` Repository Cleanliness Guardrail, Task Branch, Base Branch, Harness-Owned Commit, Optional Pull Request, Review Disposition, and Acceptance Verification with this change.
- [ ] 8.2 Update `CONTEXT.md` Board Run Queue stop conditions with the awaiting-disposition reason, and note in Run Automation Policy that the queue serializes on Task disposition rather than Worker Run completion.
- [ ] 8.3 Update `docs/HARNESS.md` launch guardrail and review sections.
- [ ] 8.4 Document the dirty-tree requirement and the base-branch setting in first-run and demo runbooks, since both are new operator-visible friction.
