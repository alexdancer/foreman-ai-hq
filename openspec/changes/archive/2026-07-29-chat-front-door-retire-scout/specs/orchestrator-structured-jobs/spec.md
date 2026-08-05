## MODIFIED Requirements

### Requirement: Jobs run on curated context and escalate deep reading to a Scout
The system SHALL run estimation and task breakdown on curated lightweight project context and SHALL NOT let a job crawl arbitrary repository source inline. When a job cannot produce a confident result from that context, it SHALL surface an explicit investigation-recommended signal that routes to the planning conversation, where the Orchestrator reads the repository under its read-only allowlist, rather than reading the repository inline as hidden orchestration spend or dispatching an investigation Task.

#### Scenario: A confident job produces a result without crawling the repository
- **WHEN** a job can produce a confident result from curated context
- **THEN** it SHALL return the structured result without reading arbitrary repository source inline

#### Scenario: A low-confidence job escalates to the conversation rather than crawling inline
- **WHEN** a job cannot produce a confident result from curated context
- **THEN** it SHALL surface an investigation-recommended signal that becomes an offer to investigate in the Planning Chat
- **AND** it SHALL NOT read arbitrary repository source inline as hidden orchestration spend
- **AND** it SHALL NOT create a dispatched investigation Task
