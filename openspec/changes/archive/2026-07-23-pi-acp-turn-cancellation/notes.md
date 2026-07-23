# Cancel wire discovery

- `pi-acp` 0.0.31 / `@agentclientprotocol/sdk` 0.26
- Cancel method: `session/cancel`
- Wire shape (JSON-RPC notification, no `id`):

```json
{"jsonrpc":"2.0","method":"session/cancel","params":{"sessionId":"<sessionId>"}}
```

- Handled by `AgentSideConnection` notification handler (`pi-acp/dist/index.js:180`) -> `agent.cancel(validatedParams)` -> `this.sessions.maybeGet(params.sessionId).cancel()`.
- `PiAcpSession.cancel()` sets `cancelRequested = true`, clears queued turns, then `await this.proc.abort()`.
- In-flight `session/prompt` resolves with result object containing `stopReason: "cancelled"` (`pi-acp/dist/index.js:2307-2308`):

```json
{"jsonrpc":"2.0","id":<id>,"result":{"stopReason":"cancelled"}}
```

- `session/prompt` normally returns `{stopReason: "end_turn"}`.
- `session/close` is not advertised by pi-acp; lifecycle stays in Python adapter.
