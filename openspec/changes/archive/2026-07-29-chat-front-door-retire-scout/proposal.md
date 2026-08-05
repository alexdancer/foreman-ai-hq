## Why

The Orchestration Board carries a Short Task Intake panel that is four front doors in one
form. `_requires_task_breakdown_review()` routes on `len(description.split()) >= 120`:
shorter plain text goes straight to Task Estimation, longer text and any Markdown paste or
upload opens a Task Breakdown Review. A `task_kind` dropdown sits alongside, letting an
operator mint a `scout` directly. The Planning Chat is a fifth path.

Two facts have changed underneath that design.

**The Orchestrator can read the repository.** `planning_conversation.py:151` launches pi
with `cwd=project["root_path"]` and the allowlist `("read", "grep", "find", "ls")`. When
ADR-0005 established the Scout on 2026-07-20, the orchestrator was two one-shot
`llm_client` calls with no tool access — "investigation must be a Worker Task launched
through an adapter" was not a preference but the only mechanism, because nothing else in
the harness could open a file. ADR-0009 changed that four days later; ADR-0005 was never
revisited.

**The Scout cannot launch on the documented happy path.** `task_launch.py:242` sets
`read_only_profile_required = (task_kind == "scout")`, and `_read_only_launchable()`
(`adapter_readiness.py:116-136`) is a literal `kind == "codex"` string test, while
`docs/HARNESS.md:135` names OpenCode as the first and only verified adapter. An operator
can select `scout`, spend Orchestration Tokens estimating it, receive an Estimated card,
and learn only at launch that their adapter can never run it.

So there are two intake surfaces, a word count standing in for judgment, a dropdown
minting Scouts detached from the target estimate they exist to de-risk, and roughly 850
lines in `estimate_decision.py` bridging a gap — between a detached Scout and the
estimator — that no longer needs to exist.

Per ADR-0011: **the Planning Chat is the only intake front door, and investigation becomes
a chat capability rather than a Task kind.**

## What Changes

- **Short Task Intake is deleted.** All work enters through the Planning Chat.
- **Judgment replaces the word count.** The Orchestrator decides `single_task` versus
  `needs_breakdown` as a structured submit-tool decision carrying a reason, recorded as
  intake provenance on the resulting card. Small work still reaches Task Estimation
  without Spec ceremony; the branch is never invisible. The `>= 120` threshold is removed.
- **Markdown stays first-class.** Paste and `.md` attachment arrive through the chat
  composer and still always reach Task Breakdown Review.
- **The chat renders as a collapsible pane on the Orchestration Board**, not a separate
  page — open by default on the Pipeline Surface where intake lived, collapsed to a rail
  on the Execution Floor so the Evidence Drawer keeps its width. Collapse is also the
  narrow-viewport behaviour. It is a pane on an existing surface, never a third surface
  duplicating board state.
- **A completed chat turn refreshes the board** regardless of
  `automation.live_refresh_enabled`, which governs background polling rather than operator
  actions.
- **The Scout Task retires.** The `scout` task kind, `read_only_profile_required` and its
  Codex gate, the linked-target and estimate-revision model, and the pending re-estimate
  claim/retry/two-phase-Apply loop are removed. `CANONICAL_TASK_KINDS` becomes
  `{implementation, acceptance_verification}`.
- **Low confidence routes to the chat.** The estimator keeps emitting
  `investigation_recommended`; the Needs You entry opens the Planning Chat with the
  question loaded, and pi re-estimates with findings already in context. Eight steps
  become two.
- **The curated-input boundary is unchanged.** Estimation, breakdown, and review keep the
  `read_curated_input`-only allowlist and still never crawl the repository inline. Only
  the signal's destination moves.

## Capabilities

### Modified Capabilities
- `planning-conversation`: the Planning Chat is the only intake front door; it records a
  structured single-task-versus-breakdown decision with its reason as intake provenance;
  it hosts repository investigation raised from low estimator confidence.
- `planning-chat-ui`: the chat renders as a collapsible board pane rather than a separate
  page, open on the Pipeline Surface and collapsed on the Execution Floor; a completed
  turn refreshes the board independently of background live refresh.
- `markdown-task-intake`: Markdown paste and `.md` attachment arrive through the chat
  composer instead of a board form, preserving review-first behaviour, file precedence,
  and validation.
- `scout-tasks`: retired. Investigation is a Planning Chat capability, not a Task kind. Its one
  surviving requirement — low-confidence advisory Needs You work — moves to `needs-you-queue`
  rather than dying with the file.
- `needs-you-queue`: gains the moved low-confidence requirement; the projection drops
  `scout_task_id` and the six Scout decision states, and the action set becomes acknowledge,
  manual estimate, and investigate-in-chat; the `/scout*` estimate-decision routes are removed.
- `react-board-workflow`: Scout kind selection is removed; card `task_kind` narrows to
  `implementation` and `acceptance_verification`; the low-confidence action becomes
  investigate-in-chat.
- `governed-worker-launch`: no Task kind requires an adapter-enforced read-only profile, and the
  launch-mode derivation rule drops its `scout` clause. The separate "Scout launch forces read-only
  mode" requirement was already removed by `governed-implementation-flow`, archived first, which
  folded that rule into the general derivation requirement; historical `scout` rows still launch
  read-only.
- `task-breakdown-review`: the `scout` candidate kind and both Scout candidate requirements are
  removed; candidate kind narrows to two values.
- `project-task-history`: `task_kind` narrows for new Tasks; historical `scout` rows keep their
  recorded kind.
- `estimation-accuracy-tracking`: the Scout exclusion rule is unnecessary because investigation
  produces no Task actuals.
- `orchestrator-structured-jobs`: the investigation-recommended signal escalates to the planning
  conversation instead of becoming a dispatched Scout Task.

## Impact

- **Backend.** `routes/tasks.py` (`_requires_task_breakdown_review`, the short-intake
  endpoint, `task_kind` validation), `task_kind.py`, `task_launch.py`
  (`read_only_profile_required`), `adapter_readiness.py` (`_read_only_launchable` and the
  Codex gate), `needs_you.py` (55 Scout-matching lines), `estimate_decision.py` (853 lines,
  93 Scout-matching lines — the claim/retry/apply/dismiss machinery), `task_slicing_policy.py`,
  `task_breakdown.py`, `estimation.py`, `routes/planning_conversation.py`.
- **Orchestrator profile.** The orchestrator persona gains the intake-decision contract;
  a submit tool carries `single_task` versus `needs_breakdown` with its reason.
- **Frontend.** `Board.jsx` (intake panel removed, chat pane added, collapse state,
  post-turn refresh), `PlanningChat.jsx` (composer with file attachment, embedded pane
  layout), board CSS for the split.
- **Specs.** `openspec/specs/scout-tasks/spec.md` (13.3 KB) is removed on archive, after its
  low-confidence requirement moves to `needs-you-queue`. Scout and Task-kind language also lives
  in `needs-you-queue`, `react-board-workflow`, `governed-worker-launch`,
  `task-breakdown-review`, `project-task-history`, `estimation-accuracy-tracking`, and
  `orchestrator-structured-jobs`; each carries a delta in this change.
- **Docs.** `CONTEXT.md` (Scout Task retired, Chat Investigation added, nine terms
  amended), `docs/HARNESS.md` Scout paragraphs, `docs/TODO.md`.

## Decisions

- **Chat investigation bounds** stay accounted rather than hard-capped, as this proposal
  already argues. What remains is persona prompt text, not architecture: the persona may
  propose stopping, and spend stays visible through the ordinary orchestration ledger.
  Revisit only if a real investigation runs away — a cap invented before that happens is the
  same magic number this change deletes, wearing a different name.
- **`estimate_decision.py` residue** is not a design decision but task 1.1: map the boundary
  between the Scout apply loop and the `acknowledge_low_confidence` / `apply_manual_estimate`
  paths that non-Scout flows use, then delete against that map. The task blocks deletion for
  exactly this reason and must not be skipped.
- **Existing Scout Tasks** are left readable as history. Rewriting `task_kind == "scout"` rows
  to `implementation` falsifies what actually happened, and archiving hides the evidence;
  leaving them costs no migration code.
- **Attachment transport** carries multipart on the chat submit path for the `.md` upload
  case and JSON otherwise, as this proposal already states.
