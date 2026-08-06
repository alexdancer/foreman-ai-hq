# Portal operator workbench — design record

The desktop Portal redesign accepted on 2026-08-03. This note is the index; the
normative material lives in the implementation specification. Captain-approved
consistency corrections made during handoff review are part of this authoritative
design record and supersede conflicting wording in the original ZIP handoff.

## Where things are

- **Implementation-ready specification, decisions, tests, and task intent** —
  `docs/design/portal-operator-workbench-spec.md`
- **Token, type, measurement, component, and interaction reference** —
  `DESIGN.md` (updated in the same change)
- **Design artifacts** — the baseline recreation, the three compared directions,
  the clickable prototype, and the printable handoff spec. These are design-tool
  documents, not repo source; they are the reference for anything the
  implementation specification and `DESIGN.md` do not pin down.

## The short version

Task Breakdown Review stopped being a wall of forms: candidates became a
navigable list plus one focused editor, selection separated from focus, and the
acceptance decision and its consequence became permanently visible with an
enumerated confirmation. Pipeline stopped hiding the workflow: a dominant
next-action banner, a stage rail that also filters, and one ledger across all
four task buckets with evidence one click from any row. Planning Inbox was
deleted and Needs You promoted to its own route, which is what removed the
duplication rather than relocating it. Underneath, the neutral ramp was renamed
by role, uppercase monospace was cut back to a single micro-label tier, and the
per-view CSS in `frontend/src/tokens.css` collapsed onto a shared set of
primitives.

## What did not change

No backend behaviour, no API contract, no projection, no mutation path, no
product terminology, and no canonical route except one addition
(`/projects/{project_id}/needs-you`). `Pipeline`, `Execution Floor`,
`Worker Run`, `Needs You`, and `Evidence` read verbatim. The Task Breakdown
Review data layer — `TEXT_FIELDS`, the draft builders, `loadCompletePage`,
`buildAcceptForm`, `submitBreakdownAction`, the navigation guard — and the
Evidence Drawer's modal contract were carried over unmodified.
