# ADR-0008: The Spec is a repo-committed artifact with a content/ledger split

**Date**: 2026-07-21
**Status**: superseded by the recorded intake provenance defined in [ADR-0011](0011-chat-is-the-front-door-and-scout-retires.md)

## Superseded decision

This ADR recorded a proposal to persist Planning Chat content in the repository
while keeping governance provenance in the Harness database. That proposal no
longer governs implementation.

## Current authority

Current product language and behavior live in `CONTEXT.md`. ADR-0011 defines
the durable intake provenance. The project maintains no separate repository
specification directory for this flow.
