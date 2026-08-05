# OpenRouter Control Plane plan history

This plan's proposed orchestration-model front door was superseded by
[ADR-0010](adr/0010-pi-inventory-is-the-sole-orchestrator-model-authority.md).
The Orchestrator Model now comes only from pi inventory and uses pi
authentication; provider, base URL, and API credentials never configure
orchestration.

The retained direct-provider connection, including OpenRouter transport and
provider-reported cost support, is owned by the canonical OpenSpec
specifications for `control-plane-model-connection` and
`proxy-governed-orchestration`. It applies only to governed Worker proxy
traffic.
