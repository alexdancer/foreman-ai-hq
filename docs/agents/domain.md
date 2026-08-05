# Domain docs

Foreman is a single-context repository. Before planning, implementation, testing, or terminology changes, read the root [`CONTEXT.md`](../../CONTEXT.md) and any applicable decisions under [`docs/adr/`](../adr/).

`CONTEXT.md` is the project glossary and domain source of truth; it contains no implementation plan. Durable trade-offs that are hard to reverse and surprising without context belong in `docs/adr/`. The accepted Portal workbench implementation specification lives at [`docs/design/portal-operator-workbench-spec.md`](../design/portal-operator-workbench-spec.md). Matt Pocock's workflow skills are optional operator-environment tooling, not committed repository assets.

## Use the glossary's vocabulary

When output names a domain concept—in an issue title, refactor proposal, hypothesis, or test name—use the term defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If a needed concept isn't in the glossary, reconsider whether the language belongs to the project or note the gap for `/domain-modeling`.

## Flag ADR conflicts

If output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 — but worth reopening because…_
