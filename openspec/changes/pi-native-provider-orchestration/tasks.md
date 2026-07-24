## 1. Confirm pi's native provider surface

- [ ] 1.1 Confirm the launch contract: `pi --provider <p> --model <orchestrator_model> --mode json --append-system-prompt <persona> --tools read,grep,find,ls`, reading the operator's real pi auth. Capture the exact `--mode json` usage-event shape for one turn and confirm per-model-call summation matches pi's own totals (for the native-usage recorder).

## 2. Launch pi on its own provider

- [ ] 2.1 In `pi_adapter.py`, add a native launch path: use `--provider <p> --model <orchestrator_model>` and let pi read the operator's real pi auth, instead of the `harness`/`proxy` `models.json` override, the isolated tmp agent dir, and the injected planning bearer.
- [ ] 2.2 Preserve persona (`--append-system-prompt`) and read-only tools (`--tools`) verbatim on the native path.
- [ ] 2.3 Ensure the operator's provider auth is read, never copied into the tracked profile, logs, or a retained tmp dir.

## 3. Native-usage accounting for planning

- [ ] 3.1 Record orchestration spend for planning turns from pi's native usage evidence (reuse `native_usage.py` / `tracking_modes.py`), summing per-model-call usage into the planning turn, held separate from `worker_execution`.
- [ ] 3.2 Do not fabricate spend when pi emits no usage for a turn.
- [ ] 3.3 Mark the planning session's tracking mode `native_usage` while keeping session kind `planning`.

## 4. Model setting + states

- [ ] 4.1 Treat `orchestrator_model` as a pi provider/model id for the native planning path (default `gpt-5.4` already valid); document the semantics and that provider auth is established through pi, not a harness field.
- [ ] 4.2 Surface a clear provider-auth-missing state in Planning Chat when the configured provider's auth is absent/expired (no dead UI, no silent empty turn).

## 5. Spec-debt fix

- [ ] 5.1 Rewrite the `orchestrator-runtime` capability off the proxy per the spec delta: remove the proxy-custom-provider and planning-bearer requirements; re-meter ACP/persona/tools/cancellation/held-conversation as native usage.

## 6. Tests

- [ ] 6.1 Backend: planning launch uses `--provider <p> --model <orchestrator_model>` on the operator's real pi auth (not the proxy profile/bearer); persona + tool allowlist present; no provider auth written to the tracked profile/logs.
- [ ] 6.2 Backend: a native-usage planning turn records orchestration spend from pi evidence and is excluded from Worker actuals/caps; a no-evidence turn records no fabricated spend; ACP cancellation and multi-turn still hold under native metering.
- [ ] 6.3 Frontend/backend: absent/expired provider auth renders the sign-in-required state rather than an empty turn.

## 7. Validation

- [ ] 7.1 `openspec validate pi-native-provider-orchestration --strict` and `openspec validate --all --strict` green.
- [ ] 7.2 `uv run pytest` and `npm run check` green; drive one real planning turn on the native provider end to end (persona reaches the provider, model is the configured one, usage recorded).
