# pi / OpenAI-compatible client startup spike notes

Non-gating findings for M2. pi 0.80.10 is installed at `/Users/alex/Library/pnpm/bin/pi` but has no local config dir (`~/.config/pi` absent), so no configured custom providers yet.

To discover the request/auth shape without needing pi configured, a throwaway logging endpoint was run on `127.0.0.1:9998` and an OpenAI-compatible client (`curl`) was pointed at it.

## Observed HTTP surface

- Endpoint: `POST /v1/chat/completions`
- Auth: `Authorization: Bearer <token>`
- Non-streaming body:
  ```json
  {"model":"claude-haiku","messages":[{"role":"user","content":"hi"}],"stream":false}
  ```
- Streaming body:
  ```json
  {"model":"claude-haiku","messages":[{"role":"user","content":"hi"}],"stream":true}
  ```
- Response shape (server-emulated):
  ```json
  {"id":"echo","choices":[{"message":{"role":"assistant","content":"ok"}}],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}
  ```
- No `/v1/models` probe was issued by the test client. Whether a real agent like pi calls `/v1/models` on startup is still TBD for M2.
- The Harness Proxy currently only exposes `/v1/chat/completions`. If a client probes `/v1/models`, a stub may be needed in M2.

## 5.2 Demonstration attempt

pi 0.80.10's built-in `openai` provider does not honor `OPENAI_BASE_URL` in this install: a throwaway server on `127.0.0.1:9999` logged no requests while `OPENAI_BASE_URL=http://127.0.0.1:9999 OPENAI_API_KEY=sk_test pi -p --provider openai --model claude-haiku ...` returned an OpenAI API 401. A custom provider/plugin is likely required in M2. This is non-gating; the M1 contract is proven client-agnostically by `test_chat_completions_planning_is_client_agnostic`.

## M2 implications

- pi custom provider config lives wherever pi stores providers; on this machine there is none yet.
- A minimal provider entry needs `baseUrl` pointing at the Harness Proxy and `apiKey` set to the planning session bearer key.
- The request shape is standard OpenAI chat-completions, so the M1 proxy-governed contract should be compatible once the provider is wired.
