# Security Policy

## Supported versions

This project is pre-1.0. Security fixes target the current `main` branch unless a release branch exists.

## Reporting a vulnerability

Open a private security advisory on GitHub if available, or contact the maintainer before posting exploitable details publicly.

Do not include API keys, portal tokens, bearer tokens, `.foreman/secrets.env`, raw credential files, or private repository content in public issues. Redact secrets as `[REDACTED]`.

## Local secret model

- `.foreman/config.toml` is non-secret operator config.
- `.foreman/secrets.env` is ignored local secret storage.
- Harness Proxy upstream API credentials, when configured, stay in ignored local secret storage or environment variables and are never exposed as Orchestrator settings.
- Native Worker CLIs such as OpenCode, Claude Code, and Codex keep their own auth/config unless explicitly routed through the Harness Proxy.
