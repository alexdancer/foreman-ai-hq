# pi-native-provider-orchestration

Run the planning Orchestrator on its own configured model provider instead of the API-key Harness Proxy, moving planning to `native_usage` accounting. Provider-agnostic — ChatGPT-via-OAuth (`openai-codex`) is one instance, not the point. Rewrites the `orchestrator-runtime` capability off the proxy. Planning only; estimation and task breakdown migrate in the follow-on `orchestrator-structured-jobs-on-pi`.
