## 0. Prerequisite

- [ ] 0.1 Land `pi-native-provider-orchestration` first (this builds on its native launch path, native-usage recorder, persona/tool-scoping mechanism, and one-shot `pi -p --mode json` support).

## 1. Submit tools

- [ ] 1.1 Define a tracked first-party pi extension `submit_estimate` whose `JsonSchema` parameters are the Estimation Drivers contract (files-to-read/modify, expected turns, test-needed, complexity, confidence, shadow token estimate) plus a low-confidence / investigation-recommended signal.
- [ ] 1.2 Define a tracked first-party pi extension `submit_breakdown` whose `JsonSchema` parameters are the Proposed Task Breakdown contract (candidates with kind, prompt, acceptance criteria; global summary; constraints; verification; rejected/non-task items; recommended sequence).

## 2. Per-job personas and tool allowlists

- [ ] 2.1 Add tracked estimator and breakdown personas under the pi profile (no secrets), encoding each job's contract and the instruction to terminate by calling its submit tool.
- [ ] 2.2 Configure each job's read-only tool allowlist: nav tools (`read,grep,find,ls`) + that job's `submit_*`; deny `bash,edit,write` and any launch capability.

## 3. Run estimation and breakdown as agent turns

- [ ] 3.1 Replace the estimation `llm_client.acompletion` structured call with an Orchestrator agent-turn run (`pi -p --mode json`) using the estimator persona/allowlist; take the `submit_estimate` arguments as the structured result.
- [ ] 3.2 Replace the task-breakdown structured call (`task_breakdown.py`) with an Orchestrator agent-turn run using the breakdown persona/allowlist; take the `submit_breakdown` arguments as the structured result.
- [ ] 3.3 Feed each job the existing curated lightweight project context; do NOT grant repository crawl.

## 4. Structured-output failure and Scout escalation

- [ ] 4.1 If a run ends without a valid submit call, surface a structured-output failure onto the existing recovery paths (manual estimate; breakdown-failed review) — never fabricate a result or fall back to a heuristic/deterministic split.
- [ ] 4.2 Wire the investigation-recommended signal from estimation/breakdown to the existing Scout path (low-confidence → linked Scout; breakdown `scout` candidate).

## 5. Accounting

- [ ] 5.1 Account estimation and breakdown spend from native usage as Orchestration Tokens labeled `estimation` / `task breakdown`, separate from `worker_execution` (reuse the native-usage recorder from `pi-native-provider-orchestration`).
- [ ] 5.2 Confirm per-job model overrides (`estimator_model` / `task_breakdown_model`, falling back to `orchestrator_model`) still apply on the agent-turn path.

## 6. Tests

- [ ] 6.1 A completed estimation emits its result via `submit_estimate` with schema-valid arguments carrying the drivers; driver arithmetic and coefficients are unchanged.
- [ ] 6.2 A completed breakdown emits its result via `submit_breakdown`; Task Breakdown Review consumes the contract unchanged; golden decomposition/estimation fixtures still pass.
- [ ] 6.3 A run that never validly submits yields a structured-output failure on the recovery path, not a fabricated result.
- [ ] 6.4 Estimation/breakdown turns are accounted from native usage, labeled correctly, excluded from Worker actuals/caps; low-confidence surfaces a Scout rather than crawling the repo.
- [ ] 6.5 The jobs cannot write code, run a shell, or launch Workers (allowlist enforced).

## 7. Validation

- [ ] 7.1 `openspec validate orchestrator-structured-jobs-on-pi --strict` and `openspec validate --all --strict` green.
- [ ] 7.2 `uv run pytest` and `npm run check` green; drive one real estimation and one real breakdown as agent turns end to end (schema-valid submit, native usage recorded, downstream review/routing unchanged).
