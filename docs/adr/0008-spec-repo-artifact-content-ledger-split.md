# ADR-0008: The Spec is a repo-committed artifact with a content/ledger split

**Date**: 2026-07-21
**Status**: superseded by the recorded intake provenance defined in [ADR-0011](0011-chat-is-the-front-door-and-scout-retires.md) and the canonical OpenSpec suite

## Context

The Planning Chat produces a Spec. Spec-driven development treats the spec as a
versioned file that travels with the code, is diffable in review, and is readable
by the coding agent at implementation time — a real strength we want. But this
project's governance model stores durable, auditable records in the Harness
database and forbids "parallel truths," and a repo file can be edited or deleted
outside the Harness while a database record cannot.

So the Spec appears to live in two places, and we must decide which is
authoritative without creating drift or a second source of truth.

## Decision

We will store the Spec's **content** as a repo-committed markdown file
(`specs/<slug>/spec.md`, auto-committed by the Harness when the Spec is finalized)
and store only a **governance ledger** in the database (conversation transcript,
`planning` token spend, status, and the link to the Proposed Task Breakdown it
produced) — so no single fact is authoritative in two places.

## Alternatives considered

| Alternative | Pros | Cons | Why rejected |
|---|---|---|---|
| Database authoritative, file is a generated export | No drift; regenerable | Editing the file does nothing; not spec-kit-faithful | Loses the "spec travels with code, editable in git" value |
| File authoritative, DB only points at it | Purest spec-kit | Audit trail only as durable as a deletable file | Weakens the governance ledger |
| **Content in repo, ledger in DB (split)** | Spec-kit fidelity + durable provenance | Two stores to reason about | **Chosen** |

## Consequences

- The repo `spec.md` is the editable, versioned source of Spec content; the
  Task Breakdown Agent and a Worker's coding agent can read it as project context.
- The database ledger survives even if the file is edited or deleted: it records
  which Spec content fed which breakdown, preserving the audit chain.
- The Harness auto-commits the Spec at finalize (reusing the existing
  Harness-owned commit path) on the current branch, keeping the working tree clean
  so the launch write-cleanliness guardrail still passes. Writing the Spec on
  every chat turn is avoided; the write happens once at finalize.
- Spec writes are bounded and conventional (a fixed `specs/` path, spec markdown
  only), not arbitrary file IO, honoring the "no writes outside project/session
  evidence surfaces" rule.
- This mirrors an existing split in the product: a Worker Run's diff lives in the
  repo while its evidence and accounting live in the database.
