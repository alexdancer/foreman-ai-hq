# ADR-0011: The Planning Chat is the only intake front door, and the Scout Task retires

**Date**: 2026-07-25
**Status**: accepted
**Supersedes**: ADR-0005 (Scout Tasks replace Spike).
**Amends**: ADR-0009 decision 4 — the Scout *boundary* holds, the Scout *Task* does not.

## Context

The Orchestration Board carries a Short Task Intake panel that is four front doors in
one form. `_requires_task_breakdown_review()` routes on `len(description.split()) >= 120`:
shorter plain text goes straight to Task Estimation, longer text and any Markdown paste
or upload opens a Task Breakdown Review. A `task_kind` dropdown sits alongside, letting
an operator mint a `scout` directly. The Planning Chat is a fifth path, always producing
a Spec.

Two things have changed underneath that design.

**The Orchestrator can read the repository.** `planning_conversation.py` launches pi with
`cwd=project["root_path"]` and the allowlist `("read", "grep", "find", "ls")`. When
ADR-0005 was written on 2026-07-20, the orchestrator was two one-shot `llm_client` calls
with no tool access at all — "investigation must be a Worker Task launched through an
adapter" was not a preference but the only mechanism available, because nothing else in
the harness could open a file. ADR-0009 changed that four days later and ADR-0005 was
never revisited.

**The Scout cannot launch on the documented happy path.** `task_launch.py` sets
`read_only_profile_required = (task_kind == "scout")`, and `_read_only_launchable()` in
`adapter_readiness.py` is a literal string test — `kind == "codex"` — while `docs/HARNESS.md`
names OpenCode as the first and only verified adapter. An operator can select `scout`,
spend Orchestration Tokens estimating it, receive an Estimated card, and discover only at
launch that their adapter can never run it. Nothing upstream warns them.

The result is a product with two intake surfaces, a word-count heuristic standing in for
judgment, a dropdown minting Scouts detached from the target estimate they exist to
de-risk, and an investigation feature that is largely dark.

## Decision

**The Planning Chat is the only intake front door, and investigation becomes a chat
capability rather than a Task kind.**

1. **One front door.** Short Task Intake is deleted. All work enters through the chat.

2. **Judgment replaces the word count.** The Orchestrator decides `single_task` versus
   `needs_breakdown` as a structured submit-tool decision carrying a reason, recorded as
   intake provenance on the resulting card. Trivial work still reaches Task Estimation
   without Spec ceremony; the branch is never invisible. The `>= 120` word threshold is
   removed.

3. **Split view on the Pipeline Surface.** The chat occupies a pane where the intake
   panel was, on the existing project-home route. This is explicitly *not* a new surface:
   the Pipeline Surface already replaced the Workspace column preview for duplicating
   board state as a third surface, and a chat pane must not reintroduce that. One
   collapsible chat component serves both surfaces. The later accepted
   [Portal operator workbench specification](../design/portal-operator-workbench-spec.md)
   owns its presentation and supersedes the original default-open behavior.

4. **A completed chat turn refreshes the board** regardless of
   `automation.live_refresh_enabled`. That flag governs background polling; a resolved
   turn is a user-initiated action and does not spend what the flag protects.

5. **The Scout Task retires.** The `scout` task kind, the `read_only_profile_required`
   Codex gate, the linked-target and estimate-revision model, and the pending
   re-estimate claim/retry/two-phase-Apply loop are removed. Low estimator confidence
   raises a Needs You entry that opens the chat with the question loaded; pi reads the
   repository and re-estimates with the findings already in conversation context.

6. **The investigation signal survives; only its destination moves.** The estimator
   continues to emit `investigation_recommended`. It routes to the chat instead of to a
   Scout Task.

7. **The Scout boundary holds.** Estimation, Task Breakdown, and Agent Review keep the
   `read_curated_input`-only allowlist and still never crawl the repository inline. What
   changes is where the resulting signal goes, not whether bounded jobs may read code.

## Alternatives considered

| # | Alternative | Why rejected |
|---|---|---|
| 1 | Keep both surfaces, only remove the `task_kind` dropdown | Fixes orphan Scouts but leaves two front doors and the word-count heuristic; does not answer the operator's want for a single place to type. |
| 2 | One front door, Spec always — no shortcut | Uniform and trivially explained, but gives "fix the typo in README" a full Spec and breakdown review. The fast path exists precisely to avoid that latency and orchestration spend. |
| 3 | Chat as the project landing surface, board a secondary view | Closest to a plain coding harness, but buries the board — and the governed board is what makes this product not a coding harness. |
| 4 | Persistent chat with the Evidence Drawer overlaying it | The overlay hides the run list the drawer was opened from, and chat permanently costs ~40% of the densest screen. |
| 5 | Keep the Scout, narrowed to unattended investigation | Preserves hard-capped investigation spend, but retains ~850 lines of decoupling machinery and a 13 KB spec for a path that needs Codex to run at all, and leaves two unexplained ways to investigate. |
| 6 | Retire the Scout but cap the chat's repository reads | Makes "no hidden spend" provable rather than trusted, but interrupts a conversation at an arbitrary boundary and introduces a new magic number in place of the word count just removed. |
| 7 | Park the Scout decision, ship the front door, revisit with usage evidence | Defensible, but leaves the machinery live and maintained meanwhile and preserves the two-ways-to-investigate confusion for an unbounded period. |

## Consequences

- **Investigation spend moves from hard-capped to accounted.** Scout spend was Worker
  spend, subject to pre-flight caps and mid-run throttling for `proxy_governed`
  adapters. Chat investigation is orchestration spend, which ADR-0009 decision 3 made
  *accounted, not hard-capped*. This is the one governance property genuinely given up.
  It is bounded in practice by the operator watching each turn, and planning spend
  remains visible per turn, ledgered in the transcript, counted against the daily budget,
  and subject to overrun alarms.
- **The low-confidence recovery path shortens from eight steps to two.** ADR-0005
  explicitly accepted extra clicks as the price of visible spend; that trade is no longer
  necessary, because the chat's spend is already visible without a card.
- **Most of `estimate_decision.py` is removable.** Its claim, retry, apply, and dismiss
  machinery exists to write an estimate back across the gap between a detached Scout and
  the estimator. Collapsing the two removes the gap rather than simplifying the bridge.
- **`read_only_profile_required` and the `kind == "codex"` gate go with the Scout.** The
  plain `read_only` launch flag is used by other paths and stays. Removing the gate is
  not a relaxation of Worker sandboxing; it removes a requirement that only existed to
  serve Scout launches.
- **`acceptance_verification` survives** as a canonical task kind. `CANONICAL_TASK_KINDS`
  becomes `{implementation, acceptance_verification}`.
- **The Markdown intake path must survive the panel's deletion.** Markdown paste and
  `.md` upload remain first-class; the chat pane needs a file-attach affordance, because
  the server needs the file bytes.
- **Eleven `CONTEXT.md` terms change**, and `Scout Task` is retired as a domain term.
