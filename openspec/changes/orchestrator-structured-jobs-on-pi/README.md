# orchestrator-structured-jobs-on-pi

Migrate Task Estimation and Task Breakdown from single-shot `llm_client` calls to Orchestrator (pi) agent turns: per-job personas and read-only tool allowlists, structured output enforced through `submit_estimate` / `submit_breakdown` tools, curated context with Scout escalation, and `native_usage` accounting. Gated on `pi-native-provider-orchestration`. Implements the second half of ADR-0009.
