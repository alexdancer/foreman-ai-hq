# orchestrator-model Specification

## Purpose
TBD - created by archiving change orchestrator-model-runtime. Update Purpose after archive.
## Requirements
### Requirement: The orchestrator has its own model setting
The system SHALL provide an orchestrator model setting that names the model used for every orchestration job — the governed planning conversation, task estimation, task breakdown, and agent review — distinct from any Worker adapter model. The setting SHALL be a provider-qualified model id for the orchestration runtime, resolved from the operator configuration and a single environment override. The system SHALL NOT define a built-in default orchestrator model: absent a configured value, the orchestrator SHALL be reported as not configured rather than falling back to a model name the runtime never offered. Estimation, task breakdown, and agent review SHALL read the orchestrator model setting rather than a separate control-plane or per-job model setting, and SHALL NOT require an operator-supplied provider, base URL, or API credential, because provider authentication belongs to the orchestration runtime. Legacy persisted `estimator_model` and `task_breakdown_model` values MAY be surfaced only as migration warnings and SHALL never select a runtime model; saving the Orchestrator Model SHALL remove those legacy values.

#### Scenario: Every orchestration job uses the orchestrator model
- **WHEN** the harness performs planning, intake judgment, task estimation, task breakdown, or agent review
- **THEN** the request model SHALL be the configured orchestrator model even when legacy per-job values diverge
- **AND** it SHALL NOT require an operator-configured provider, base URL, or API key

#### Scenario: Legacy per-job values are migration evidence only
- **WHEN** persisted `estimator_model` or `task_breakdown_model` values differ from the Orchestrator Model
- **THEN** the settings handoff MAY name them as migration warnings
- **AND** no orchestration request SHALL use either value
- **AND** saving the Orchestrator Model SHALL remove both legacy persisted values

#### Scenario: There is no built-in default orchestrator model
- **WHEN** the orchestrator model setting is absent from configuration and environment
- **THEN** the orchestrator SHALL be reported as not configured
- **AND** the harness SHALL NOT substitute a built-in model name

### Requirement: The control-plane model setting is retired with back-compat
The system SHALL retire the control-plane model setting in favor of the orchestrator model setting. Every caller that previously read the control-plane model SHALL read the orchestrator model. An existing operator configuration that still names the control-plane model SHALL be read as a candidate orchestrator model value and validated against the runtime inventory like any other value, so operators are not silently broken on upgrade and are not silently left on an unrunnable model.

#### Scenario: Legacy control-plane model config is honored
- **WHEN** an operator configuration names the control-plane model but not the orchestrator model
- **THEN** the named value SHALL be read as the orchestrator model candidate
- **AND** no caller SHALL still depend on a separate control-plane model setting

#### Scenario: No caller reads a separate control-plane model
- **WHEN** the harness resolves the model for planning, estimation, task breakdown, agent review, the CLI health check, or the portal settings surface
- **THEN** each SHALL resolve the orchestrator model
- **AND** no code path SHALL read a distinct control-plane model setting

### Requirement: Orchestration turns meter as orchestration spend
Orchestration turns — the planning conversation and any other orchestrator-model work metered through the governed proxy — SHALL be recorded with their existing spend classification (planning turns as planning spend), held separate from Worker execution spend, and SHALL NOT be counted as any Task's Worker execution actuals or against a per-session Worker execution cap. This capability SHALL NOT introduce a new operator-visible spend-category rollup key; orchestration spend continues to aggregate under the existing summary categories.

#### Scenario: Orchestration spend is separate from Worker execution
- **WHEN** an orchestration turn is recorded
- **THEN** it SHALL retain its existing spend classification rather than being counted as Worker execution
- **AND** it SHALL NOT be added to any Task's Worker execution actuals or a per-session Worker execution cap

### Requirement: The runtime inventory is the sole authority for the orchestrator model
The system SHALL treat the set of models the orchestration runtime reports as runnable as the only authority for which models the orchestrator may use. A valid orchestrator model value SHALL be a provider-qualified id present in that inventory. The system SHALL NOT maintain a harness-authored list of orchestrator models, SHALL NOT accept a bare or pattern-shaped model value, and SHALL NOT infer a provider for an unqualified value. A configured value that is absent from the inventory SHALL be reported as not configured rather than repaired by inference or accepted unvalidated.

#### Scenario: Only inventory models are selectable
- **WHEN** the operator chooses an orchestrator model
- **THEN** the choice SHALL be constrained to models present in the runtime inventory
- **AND** the stored value SHALL be provider-qualified

#### Scenario: A value absent from the inventory is not configured
- **WHEN** the configured orchestrator model does not appear in the runtime inventory
- **THEN** the orchestrator SHALL be reported as not configured
- **AND** the system SHALL NOT select a substitute model or infer a provider for it

#### Scenario: No harness-authored model list exists
- **WHEN** the portal offers orchestrator model choices
- **THEN** every offered choice SHALL originate from the runtime inventory
- **AND** no curated model list maintained by the harness SHALL be offered

### Requirement: Inventory discovery is explicit, evidenced, and revalidated on save
The system SHALL discover the orchestrator model inventory by asking the orchestration runtime, on explicit operator request rather than as a side effect of rendering a page. Discovery SHALL persist evidence including the discovered models and the time of discovery, and SHALL reject output that is not a model identifier. Ordinary page rendering SHALL read persisted evidence rather than invoking the runtime. Saving an orchestrator model SHALL revalidate the chosen value against a freshly discovered inventory, so a stale snapshot cannot persist an unrunnable setting. When the runtime reports no models — because the operator has not authenticated with any provider — the system SHALL present an actionable authenticate-with-the-runtime state rather than an empty selection.

#### Scenario: Discovery is explicit and evidenced
- **WHEN** the operator requests inventory discovery
- **THEN** the system SHALL query the orchestration runtime and persist the discovered models with a discovery timestamp
- **AND** output that is not a model identifier SHALL be rejected rather than stored as a model

#### Scenario: Page rendering does not invoke the runtime
- **WHEN** a portal surface displays orchestrator model state
- **THEN** it SHALL read persisted discovery evidence
- **AND** it SHALL NOT invoke the orchestration runtime to render

#### Scenario: Save revalidates against a fresh inventory
- **WHEN** the operator saves an orchestrator model
- **THEN** the system SHALL revalidate the chosen value against a freshly discovered inventory
- **AND** SHALL reject the save when the value is no longer present

#### Scenario: An empty inventory is actionable
- **WHEN** the orchestration runtime reports no runnable models
- **THEN** the system SHALL present a state directing the operator to authenticate through the runtime
- **AND** it SHALL NOT present an empty model selection as a normal state

### Requirement: Orchestrator verification runs a real turn and proves metering
The system SHALL prove the configured orchestrator model by running one real orchestration turn with a harmless sentinel prompt, through the same launch path, persona, and read-only tool policy used by governed work. Verification SHALL pass only when the sentinel response matched and a token turn was recorded for that run; a matched sentinel without recorded token evidence SHALL NOT pass, because it proves the command ran rather than that spend is accounted. Verification spend SHALL be recorded as orchestration spend labeled as adapter verification. The presence of a model in the inventory SHALL NOT by itself constitute verification. Changing the orchestrator model SHALL mark existing verification evidence as stale rather than blocking the save on a fresh run.

#### Scenario: Verification requires both sentinel and token evidence
- **WHEN** orchestrator verification runs
- **THEN** it SHALL pass only if the sentinel response matched and a token turn was recorded for that run
- **AND** a matched sentinel with no recorded token turn SHALL fail with that reason

#### Scenario: Inventory presence is not verification
- **WHEN** the configured orchestrator model appears in the inventory but has never been verified
- **THEN** the system SHALL NOT report the orchestrator as verified

#### Scenario: Verification spend is accounted
- **WHEN** an orchestrator verification turn produces usage evidence
- **THEN** the system SHALL record it as orchestration spend labeled as adapter verification
- **AND** it SHALL NOT be attached to any Task's Worker execution actuals

#### Scenario: Changing the model marks verification stale
- **WHEN** the operator saves a different orchestrator model
- **THEN** prior verification evidence SHALL be marked stale
- **AND** the save SHALL NOT be blocked pending a fresh verification run

### Requirement: Token turns record the model the runtime resolved
Every orchestration token turn SHALL record the model as the orchestration runtime reported it in its own usage evidence, in one provider-qualified convention across every orchestration job. When the runtime emits no model in its usage evidence, the system SHALL record the configured orchestrator model in the same convention. Different orchestration jobs SHALL NOT record different model strings for the same configured model.

#### Scenario: The recorded model comes from runtime evidence
- **WHEN** an orchestration turn produces usage evidence naming a provider and model
- **THEN** the recorded turn model SHALL be that provider-qualified value

#### Scenario: All orchestration jobs agree on the model string
- **WHEN** planning, estimation, task breakdown, and agent review each record a token turn on the same configured orchestrator model
- **THEN** every recorded turn SHALL carry the same model string

#### Scenario: Missing runtime model falls back to the setting
- **WHEN** an orchestration turn produces usage evidence with no model named
- **THEN** the recorded turn model SHALL be the configured orchestrator model in the same provider-qualified convention

### Requirement: An unconfigured orchestrator blocks orchestration but not evidence
When the orchestrator is not configured, the system SHALL refuse to start orchestration work — the planning conversation, task estimation, task breakdown, and agent review — and SHALL refuse board access and Worker launches, directing the operator to orchestrator setup. The system SHALL keep sign-in, every settings surface, and read-only evidence surfaces reachable, so an absent or expired provider authentication cannot deny the operator access to their own audit trail or to the pages required to fix the configuration. The refusal SHALL be evaluated from persisted configuration and discovery evidence rather than by invoking the orchestration runtime, and SHALL NOT be bypassable through an environment setting that weakens production behavior.

#### Scenario: Orchestration and board are blocked when unconfigured
- **WHEN** the orchestrator is not configured and the operator requests the board, a Worker launch, or any orchestration job
- **THEN** the system SHALL refuse and direct the operator to orchestrator setup
- **AND** the refusal SHALL NOT start a runtime turn or a Worker

#### Scenario: Settings and evidence remain reachable when unconfigured
- **WHEN** the orchestrator is not configured
- **THEN** sign-in, settings surfaces, and read-only evidence surfaces SHALL remain reachable
- **AND** the operator SHALL be able to inspect existing session, report, and alarm history

#### Scenario: The gate reads persisted state
- **WHEN** the system evaluates whether the orchestrator is configured
- **THEN** it SHALL read persisted configuration and discovery evidence
- **AND** it SHALL NOT invoke the orchestration runtime to make that determination
- **AND** no environment setting SHALL bypass the gate

