from __future__ import annotations

TASK_BREAKDOWN_EXECUTION_MODES = {"AFK", "HITL"}
DEFAULT_TASK_BREAKDOWN_EXECUTION_MODE = "HITL"

TASK_SLICING_POLICY = """
Task Slicing Policy:
- Create the fewest Orchestration Board Tasks that preserve independent Worker execution, reviewability, and final acceptance proof.
- A candidate exists only if it delivers one behavior, coherent codebase seam, or bounded investigation with its own proof. Markdown bullets are evidence, not automatic Tasks.
- Reject setup prose, context-only notes, duplicate bullets, non-goals, constraints, verification notes, speculative future-proofing, and generic open-ended research as standalone Tasks.
- Prefer tracer-bullet vertical slices over horizontal layer slices such as models/routes/UI/tests unless the layer is independently useful and verifiable.
- Prefer the smallest honest slice: large enough for one Worker to complete without sibling context, small enough to avoid re-solving the full source task.
- Reuse existing repo patterns and likely entry points from repo_context hints; never invent framework or infrastructure work not required by source_text.
- If multiple requested items share one root cause or seam, prefer one shared-seam Task instead of duplicated caller-level Tasks.
- Every candidate must include an objective, proof/verification path, why it exists, why it is not smaller, why it is not larger, dependencies by candidate title when needed, likely repo entry points when known, and execution_mode AFK or HITL.
- Mark execution_mode AFK only when a Worker can complete and verify the Task without waiting for operator choices, credentials, external approval, or manual product judgment. Mark HITL with a concrete hitl_reason when human input is required.
- Keep source_text contract-authoritative. Use repo_context only as bounded hints for entry points, tests, docs, and constraints; do not merge it into or replace source_text.
- Scout candidates are read-only investigations: they must ask a concrete bounded question, declare an inspection boundary, list expected findings, and never request code edits, destructive commands, migrations, or commits. Reject any candidate that is open-ended research or lacks a verifiable proof.
""".strip()

TASK_BREAKDOWN_OUTPUT_SCHEMA = """
Call submit_breakdown exactly once with exactly these top-level fields:
- decision: single_task or proposed_task_breakdown
- candidates: array of candidate objects
- rejected_items: array of objects with text and reason
- global_contract_summary: string
- global_constraints: array of strings
- verification: array of strings
- non_goals: array of strings
- recommended_sequence: array of candidate titles
- confidence: number 0-1
- rationale: string

Each candidate object must include:
- kind: implementation, acceptance_verification, or scout
- title: concise board-card title
- objective: what this slice accomplishes (for scout, the concrete bounded investigation question)
- prompt: Worker-facing implementation, verification, or scout instructions
- acceptance_criteria: behavior-level criteria (for scout, what closes the investigation)
- constraints: array of task-specific constraints (for scout, include the read-only inspection boundary)
- proof: smallest executable or inspectable verification path for this candidate
- why_this_task_exists: why this deserves a board card
- why_not_smaller: why smaller substeps would be over-splitting or lose independent proof
- why_not_larger: why merging with adjacent work would make the Task too broad
- dependencies: array of candidate titles that should run first, empty when none
- likely_entry_points: array of likely files/modules/routes/tests/docs from repo_context, empty when unknown
- target_task_id: existing Harness Task id when a scout de-risks that Task, otherwise null
- execution_mode: AFK or HITL
- hitl_reason: required when execution_mode is HITL, empty only when AFK
- human_in_loop: boolean retained for compatibility; true when execution_mode is HITL
""".strip()
