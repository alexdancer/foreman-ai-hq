## REMOVED Requirements

### Requirement: Scout is a canonical Task kind
**Reason**: Investigation existed as a Task kind because the orchestrator of the time had no tool access and a Worker was the only component in the harness that could read a file. The orchestration runtime now reads the repository directly under a read-only allowlist, so a separate dispatched Task is no longer the mechanism by which investigation happens.
**Migration**: Canonical Task kinds become `implementation` and `acceptance_verification`. Investigation is performed in the Planning Chat. Existing Tasks recorded as `scout` remain readable as history.

### Requirement: Scout uses ordinary governed Task lifecycle
**Reason**: There is no longer a Task to move through the lifecycle. Investigation happens inside the planning conversation, which has its own session, transcript, and spend ledger.
**Migration**: Investigation spend is recorded as `planning` orchestration spend on the planning session rather than as Worker actuals on a Task card.

### Requirement: Scout produces a Session Report
**Reason**: The report artifact existed because a dispatched Worker had to return findings across a process boundary. Findings now remain in the conversation the operator is reading, and the transcript is itself a durable ledger.
**Migration**: Investigation findings are preserved in the planning conversation transcript.

### Requirement: Linked Scout does not mutate target estimate
**Reason**: The linkage, estimate revision, and non-mutation guarantee existed to keep a detached investigation from silently rewriting an estimate the operator had already seen. With investigation inside the conversation, there is no detached actor and no estimate written behind the operator's back.
**Migration**: A re-estimate requested after investigation is an ordinary operator-initiated estimation with the findings in context.

### Requirement: Scout-informed re-estimation is explicit
**Reason**: The pending-result, claim, retry, and two-phase Apply machinery existed to write a number back across the gap between a detached Scout and the estimator. Removing the gap removes the reconciliation problem rather than simplifying it.
**Migration**: The operator requests a re-estimate in the conversation; the result is applied as an ordinary estimate with its provenance recorded.

### Requirement: Scout accounting and calibration remain isolated
**Reason**: The isolation rule existed because Scout actuals were Worker spend that would otherwise contaminate implementation coefficient fitting. Investigation spend is now orchestration spend and is already excluded from Task actuals and coefficient fitting by that classification.
**Migration**: No Task actuals are produced by investigation, so no kind-based exclusion is required. Coefficient fitting continues to use Done implementation Tasks with trustworthy actuals.

### Requirement: Low estimator confidence creates advisory Needs You work
**Reason**: The requirement survives the Scout's retirement but cannot live in a capability that is being removed. Its home is the Needs You queue, which already owns the low-confidence projection and its mutation contracts.
**Migration**: Moved verbatim to `needs-you-queue`, with the linked-Scout action replaced by opening the Planning Chat with the investigation question loaded. The `0.60` threshold and its boundary behaviour are unchanged.
