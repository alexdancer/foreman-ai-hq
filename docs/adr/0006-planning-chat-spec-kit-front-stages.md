# ADR-0006: Planning Chat models spec-kit's specify/clarify front stages

**Date**: 2026-07-21
**Status**: superseded by [ADR-0011](0011-chat-is-the-front-door-and-scout-retires.md)

## Context

We want an in-Portal planning surface that lets an operator shape a fuzzy idea
into governed, estimated work. Two mature external workflows were on the table as
models: **GitHub spec-kit** (a prompt-only, single-`spec.md` flow of
`constitution → specify → clarify → plan → tasks → analyze → implement`) and
**Compozy** (a Go CLI + daemon whose workflow produces PRD + user stories +
TechSpec + test contract + task graph, with ACP runtimes).

Foreman AI HQ already owns the back half of both flows: a Task Breakdown Agent
(≈ `/tasks`), governed Worker Runs (≈ `/implement`), and Agent Review /
Acceptance Verification (≈ `/analyze`). It also already forbids a "magic chat box
with launch buttons and no evidence trail." The open question was which external
model to borrow for the *front* of the pipeline, and how much of it.

## Decision

We will model the Planning Chat on spec-kit's `specify` + `clarify` front stages
only — reimplemented natively, producing one durable **Spec** that feeds the
existing Task Breakdown Agent — and adopt neither Compozy nor spec-kit as a
runtime dependency.

## Alternatives considered

| Alternative | Pros | Cons | Why rejected |
|---|---|---|---|
| Full Compozy workflow | Rich artifacts (PRD/TechSpec/tests/graph); parallel waves | Second execution engine (daemon/ACP); forks the Task Breakdown Agent; ungoverned parallel-truth artifacts | Duplicates owned stages and violates "one evidence system" |
| Both spec-kit and Compozy | Most capable on paper | Two stage vocabularies and two artifact conventions | Parallel truths; unjustified surface area |
| Import spec-kit/Compozy as a dependency | Less to build | Their model calls bypass harness token governance; second runtime | Un-metered helper spend is a thesis violation |
| **spec-kit specify+clarify front stages, native** | One new noun (Spec); reuses breakdown/review/estimation; every turn metered | Must build a native clarify loop | **Chosen** |

## Consequences

- One new domain term, **Spec**, enters the glossary; the chat converges on it and
  hands off to the existing Task Breakdown Review flow — no second decomposition
  engine, no auto-created Tasks.
- The Planning Chat is an **additional** intake front door; Markdown Task Intake
  is unchanged. Because a Spec is Markdown, handoff reuses the Markdown intake
  path.
- spec-kit's later stages (`plan`/`tasks`/`analyze`/`implement`) are deliberately
  not built; they map onto capabilities Foreman AI HQ already governs. Adding a
  spec-kit `/plan` (TechSpec) stage later remains possible as a second artifact.
- The clarify discipline (one question at a time, lead with a recommendation) is
  now a product behavior, mirroring how the harness itself is designed.
