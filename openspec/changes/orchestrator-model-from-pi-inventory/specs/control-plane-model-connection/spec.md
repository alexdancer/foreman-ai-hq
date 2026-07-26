## MODIFIED Requirements

### Requirement: Control-plane model connection
The system SHALL retain a direct provider model connection solely as Harness Proxy upstream configuration for `proxy_governed` Worker traffic. This connection SHALL NOT be the orchestration model connection: planning, task estimation, task breakdown, and agent review SHALL run on the orchestration runtime and its own provider authentication, and SHALL NOT read this connection's provider, base URL, or API credential. The connection SHALL NOT be presented as an operator-facing orchestration setting, and no portal surface SHALL describe it as configuring estimation, breakdown, planning, review, or reports.

#### Scenario: Orchestration does not use the direct connection
- **WHEN** the harness performs planning, task estimation, task breakdown, or agent review
- **THEN** it SHALL use the orchestration runtime and its own provider authentication
- **AND** it SHALL NOT read the direct connection's provider, base URL, or API credential

#### Scenario: The direct connection serves proxy-governed Workers
- **WHEN** a `proxy_governed` Worker Run sends model traffic through the Harness Proxy
- **THEN** the proxy SHALL use the configured direct provider connection upstream

#### Scenario: The connection is not an orchestration setting
- **WHEN** a portal surface presents orchestration model configuration
- **THEN** it SHALL NOT present provider, base URL, or API key fields for orchestration
- **AND** it SHALL NOT describe the direct connection as powering estimation, breakdown, planning, review, or reports

## REMOVED Requirements

### Requirement: Control-plane connection test
**Reason**: The test exercised the direct HTTP connection, which orchestration no longer uses, so it could pass while the orchestrator was unable to run. Replaced by orchestrator verification, which runs a real orchestration turn and requires recorded token evidence.
**Migration**: Operators verify the orchestrator through the orchestrator model surface. Existing persisted control-plane test status is superseded by orchestrator verification evidence.

### Requirement: Portal-managed control-plane API key entry
**Reason**: The orchestration runtime authenticates through its own provider sign-in; a key pasted into the portal was never read by any orchestration job. Retaining the field implied a credential relationship that did not exist.
**Migration**: Provider authentication for orchestration is established through the orchestration runtime's own sign-in. Any existing key in local secret storage remains readable by the Harness Proxy for `proxy_governed` Workers and is not deleted.

### Requirement: Curated control-plane model list has a single authoritative source
**Reason**: The orchestration runtime's reported inventory is now the sole authority for orchestrator model choices, so a harness-authored curated list has no authoritative role. Its provider names did not correspond to runtime provider ids.
**Migration**: Model choices are discovered from the orchestration runtime. A configured model that is not present in the discovered inventory is reported as not configured.

### Requirement: Control-plane split-model default
**Reason**: One orchestrator model now serves every orchestration job, so the coupling option has no meaning. Its disabled branch silently preserved stale estimator and breakdown models, which could leave orchestration jobs pointing at a model the runtime cannot run.
**Migration**: Saving the orchestrator model applies it to every orchestration job. Per-job model keys remaining in operator configuration are surfaced as a divergence warning rather than silently honored as normal state.
