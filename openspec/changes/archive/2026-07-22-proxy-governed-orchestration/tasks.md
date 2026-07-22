## 1. Spike & baseline

- [x] 1.1 pi-startup spike (non-gating): point pi — or any OpenAI-compatible client — at a throwaway logging endpoint and record which HTTP endpoints it calls, the request/stream/auth shape (`/v1/chat/completions` only vs `/v1/models` probe, `stream_options`, `Authorization: Bearer`), and pi's config-file + plugin layout. Capture findings as change notes to feed M2; do not let them change this change's contract.
- [x] 1.2 Establish the additive baseline: confirm existing tests pin the six fixed `by_category` keys and that `budgeted_token_usage` sums all tracked rows, so the `planning` classification lands additively with no fixed-key contract change.

## 2. Session kind

- [x] 2.1 Add a session **kind** additively (Worker default, no destructive migration of existing rows) with a canonical reader: legacy and Worker-launched sessions resolve to the Worker kind; orchestration metering anchors resolve to `planning`.
- [x] 2.2 Add a planning-session creation helper that reuses the synthetic `session_key_hash` anchor pattern and returns a bearer an external agent can present as a proxy API key.
- [x] 2.3 Filter `planning`-kind sessions out of Worker session listings (`list_sessions` / portal Worker-session projections).
- [x] 2.4 Tests: legacy/Worker sessions read as Worker; a planning anchor reads as `planning`; a planning session is excluded from Worker listings.

## 3. Planning spend classification

- [x] 3.1 Add `planning → planning` to `_spend_category_for_usage_kind` and `planning → harness_proxy` to `_usage_source_for_usage_kind`; leave the fixed `by_category` keys in `_summarize_token_turns` unchanged so `planning` aggregates under `other` at the rollup level while staying `planning` on the token row.
- [x] 3.2 Tests: a `planning` turn has `spend_category = planning` and `usage_source = harness_proxy`; it is included in `budgeted_token_usage` for the daily window; it is not added to Worker `actual_tokens` and not counted against a per-session Worker cap.

## 4. Proxy session-derived classification

- [x] 4.1 In `routes/proxy.py` `_persist_turn`, derive `usage_kind` from the authenticated session's kind instead of defaulting to `worker`, and pass it to `record_token_turn` (covers both the non-stream and streamed `_stream_chunks` paths, which share `_persist_turn`).
- [x] 4.2 Tests: a completion on a `planning` session is recorded as a `planning` turn through the existing budget-zone/guardrail-snapshot path; a completion on a Worker session is classified as Worker execution as before.

## 5. End-to-end proof

- [x] 5.1 Client-agnostic proof test: an OpenAI-compatible client authenticated as a planning session posts one completion and exactly one `planning` token turn is recorded, with an identical result regardless of which compatible client produced the request.
- [x] 5.2 Demonstration (non-gating): attempted with pi 0.80.10 — its built-in `openai` provider ignores `OPENAI_BASE_URL` (returns 401 without hitting the proxy), so a real pi turn through the proxy needs a custom provider and is deferred to M2. The M1 contract is proven client-agnostically by task 5.1; findings recorded in `pi_spike_notes.md`.

## 6. Validation

- [x] 6.1 Run `openspec validate proxy-governed-orchestration --strict` and resolve any errors.
- [x] 6.2 Run `uv run pytest` (repo-required fresh check after edits) and confirm green, isolating any pre-existing worktree failures unrelated to this change.
