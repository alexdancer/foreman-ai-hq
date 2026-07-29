# DEMO 2099 Long OpenCode Comparison Task: Incident Ledger CLI

> DEMO DATA ONLY — This task, all examples, and all expected fixtures are synthetic. Use only 2099 dates, DEMO names, `.invalid` email addresses, DEMO addresses, and 999-style fake account numbers. Do not use real customer data. Do not call real external services.

## Purpose

Build a local Python CLI project named `incident-ledger`. This is a deliberately long coding task for comparing two execution paths:

1. OpenCode run directly on this task file.
2. OpenCode launched through Foreman AI HQ using the same task file and a separately configured harness Worker budget.

The goal is not to prove magic token compression. The goal is to create enough realistic implementation work for meaningful token usage while showing what the harness adds: estimate visibility, budget gating, usage authority, launch evidence, alarms or overrides, and review-state evidence.

## Starting Point for the Worker

Create or update a small local Python project in the working directory. If the directory is empty, create the project. If a minimal scaffold already exists, preserve useful files and implement the missing behavior.

## Foreman AI HQ Launch Notes

- The connected project must be a Git repository for a write-capable `implementation` launch.
- The operator must confirm the project base branch and any verification command in `/settings/project` before the first launch; the Harness detects candidates but does not execute or branch from unconfirmed values.
- Commit or stash uncommitted operator changes before launch; the Harness refuses a dirty working tree and names the offending paths, but it does not stash or commit them for you.

Expected package name:

```text
incident_ledger
```

Expected console command:

```text
incident-ledger
```

Recommended implementation constraints:

- Use Python standard library where practical.
- Use `argparse` for CLI parsing unless an existing project already uses another CLI library.
- Use `sqlite3` for persistence.
- Use `json`, `csv`, `datetime`, `pathlib`, `hashlib`, and `re` as needed.
- Add pytest tests. If pytest is unavailable in the scaffold, document the setup and still write tests.
- Do not add network dependencies.
- Do not call real external APIs.
- Do not add auth, billing, deployment, web UI, or cloud integrations.

## Synthetic Data Rules

All sample data and test fixtures must be obviously fake.

Required markers:

- Dates: use year `2099` only.
- Names: include `DEMO`, such as `DEMO North Ops`.
- Email addresses: use `.invalid`, such as `demo.dispatch.2099@example.invalid`.
- Addresses: include `DEMO`, such as `999 DEMO Harbor Loop, Demo City, ZZ 99999`.
- Account IDs: use `999`-style values, such as `ACCT-999-2099-0001`.
- Incident IDs: use `DEMO-INC-2099-0001` style values.

Forbidden:

- Real emails.
- Real addresses.
- Real tokens, secrets, passwords, API keys, or connection strings.
- Commands that send data to real external APIs.
- Instructions to publish to any gist, ticket, issue, email, webhook, or cloud object service.

## Product Goal

`incident-ledger` helps a synthetic operations team ingest incident records, normalize them into a local SQLite database, detect likely duplicates, score incident severity, and generate local reports.

The tool should be useful enough for a reviewer to run it end-to-end with DEMO fixtures:

```bash
incident-ledger ingest examples/demo_incidents_2099.jsonl --db .demo/incident-ledger.sqlite
incident-ledger ingest examples/demo_incidents_2099.md --db .demo/incident-ledger.sqlite
incident-ledger dedupe --db .demo/incident-ledger.sqlite
incident-ledger score --db .demo/incident-ledger.sqlite
incident-ledger list --db .demo/incident-ledger.sqlite --status open
incident-ledger report --db .demo/incident-ledger.sqlite --format markdown --output .demo/report.md
incident-ledger export --db .demo/incident-ledger.sqlite --format json --output .demo/export.json
```

## Required CLI Commands

### `incident-ledger ingest <path>`

Ingest incidents from either JSONL or Markdown.

Options:

- `--db <path>`: SQLite database path. Default: `.incident-ledger.sqlite` in the current directory.
- `--source-name <name>`: Optional label for the input source.
- `--dry-run`: Parse and validate input without writing rows.
- `--strict`: Fail the whole ingest if any record is invalid.

Behavior:

- Create the database and schema if missing.
- Normalize records into a common shape.
- Store raw source text or raw JSON for audit/debugging.
- Print a short summary: inserted, skipped, invalid, source type.
- Use deterministic validation errors that include a record number or heading.

### `incident-ledger list`

List incidents from the local database.

Options:

- `--db <path>`
- `--status open|closed|watching|all`
- `--severity low|medium|high|critical|all`
- `--owner <name>`
- `--limit <n>`
- `--json`: Emit JSON instead of table text.

Behavior:

- Default status filter is `all`.
- Default severity filter is `all`.
- Sort by severity rank descending, then incident date descending, then incident ID ascending.
- If no incidents match, print a clear empty-state message and exit 0.

### `incident-ledger dedupe`

Detect likely duplicate incidents and record duplicate groups.

Options:

- `--db <path>`
- `--threshold <integer>` default `75`
- `--explain`: Print why incidents were grouped.
- `--apply`: Persist duplicate-group assignments. Without `--apply`, run as preview only.

Behavior:

- Use deterministic local matching only.
- Do not add fuzzy matching dependencies.
- Suggested scoring:
  - same normalized account ID: +30
  - same system/component: +20
  - same 2099 calendar day: +15
  - overlapping normalized title tokens: up to +20
  - overlapping impact keywords: up to +15
- Preview mode must not mutate the database.
- Apply mode should assign stable group IDs such as `DEMO-DUPE-2099-0001`.

### `incident-ledger score`

Calculate severity for incidents.

Options:

- `--db <path>`
- `--incident-id <id>` optional single-incident mode
- `--explain`: Print component scores.

Severity levels:

- `low`: total score 0-29
- `medium`: total score 30-59
- `high`: total score 60-84
- `critical`: total score 85+

Suggested weighted factors:

- customer impact count: 0-25
- payment or safety keyword: 0-20
- outage duration minutes: 0-20
- data exposure flag: 0-25
- repeat incident / duplicate group: 0-10

Behavior:

- Persist numeric score and severity label.
- Preserve manual severity if the input explicitly marks `manual_severity=true`; still store computed score separately.
- Explanations should be deterministic and testable.

### `incident-ledger report`

Generate a local report.

Options:

- `--db <path>`
- `--format markdown|json`
- `--output <path>` optional; if omitted, print to stdout.
- `--include-closed`
- `--owner <name>` optional filter.

Markdown report must include:

- DEMO banner.
- Generated-at timestamp using a deterministic value in tests when an environment variable is set.
- Summary counts by severity.
- Top 5 incidents by severity score.
- Duplicate groups.
- Data-quality warnings.

JSON report must include:

- `demo_banner`
- `generated_at`
- `summary`
- `top_incidents`
- `duplicate_groups`
- `warnings`

### `incident-ledger export`

Export normalized data.

Options:

- `--db <path>`
- `--format json|csv`
- `--output <path>`
- `--status open|closed|watching|all`

Behavior:

- JSON export should be an array of normalized incident objects.
- CSV export should include stable headers.
- Parent directories for output should be created if missing.

## Input Format: JSONL

Each line is a JSON object. Required fields:

- `incident_id`
- `title`
- `occurred_at`
- `account_id`
- `owner`
- `status`
- `system`
- `impact_summary`

Optional fields:

- `customer_impact_count`
- `outage_duration_minutes`
- `data_exposure`
- `manual_severity`
- `tags`
- `contact_email`
- `address`

Example:

```json
{"incident_id":"DEMO-INC-2099-0001","title":"DEMO checkout delay for account ACCT-999-2099-0001","occurred_at":"2099-03-14T09:15:00Z","account_id":"ACCT-999-2099-0001","owner":"DEMO North Ops","status":"open","system":"checkout-demo","impact_summary":"DEMO payment queue delayed for synthetic shoppers","customer_impact_count":999,"outage_duration_minutes":47,"data_exposure":false,"tags":["DEMO","payments","2099"],"contact_email":"demo.dispatch.2099@example.invalid","address":"999 DEMO Harbor Loop, Demo City, ZZ 99999"}
{"incident_id":"DEMO-INC-2099-0002","title":"DEMO checkout queue delay duplicate signal","occurred_at":"2099-03-14T09:22:00Z","account_id":"ACCT-999-2099-0001","owner":"DEMO North Ops","status":"watching","system":"checkout-demo","impact_summary":"DEMO payment queue still delayed, possible duplicate of DEMO-INC-2099-0001","customer_impact_count":899,"outage_duration_minutes":52,"data_exposure":false,"tags":["DEMO","payments","duplicate-check"],"contact_email":"demo.queue.2099@example.invalid","address":"999 DEMO Harbor Loop, Demo City, ZZ 99999"}
{"incident_id":"DEMO-INC-2099-0003","title":"DEMO reporting dashboard stale totals","occurred_at":"2099-04-01T15:30:00Z","account_id":"ACCT-999-2099-0002","owner":"DEMO Analytics Ops","status":"closed","system":"reporting-demo","impact_summary":"DEMO dashboard totals lagged behind synthetic batch processing","customer_impact_count":99,"outage_duration_minutes":18,"data_exposure":false,"tags":["DEMO","reporting","2099"],"contact_email":"demo.analytics.2099@example.invalid","address":"999 DEMO Ledger Plaza, Demo City, ZZ 99999"}
```

## Input Format: Markdown

Markdown incidents use level-2 headings and bullet fields.

Example:

```markdown
# DEMO 2099 Incident Batch

## DEMO-INC-2099-0101 — DEMO synthetic login surge

- occurred_at: 2099-05-02T10:00:00Z
- account_id: ACCT-999-2099-0101
- owner: DEMO Identity Ops
- status: open
- system: identity-demo
- customer_impact_count: 299
- outage_duration_minutes: 34
- data_exposure: false
- contact_email: demo.identity.2099@example.invalid
- address: 999 DEMO Identity Way, Demo City, ZZ 99999
- tags: DEMO, identity, 2099

Impact summary:
DEMO login throttling caused synthetic users to retry against the 2099 identity sandbox.

## DEMO-INC-2099-0102 — DEMO synthetic audit flag

- occurred_at: 2099-05-03T11:45:00Z
- account_id: ACCT-999-2099-0102
- owner: DEMO Audit Ops
- status: watching
- system: audit-demo
- customer_impact_count: 49
- outage_duration_minutes: 5
- data_exposure: true
- contact_email: demo.audit.2099@example.invalid
- address: 999 DEMO Audit Road, Demo City, ZZ 99999
- tags: DEMO, audit, synthetic-data

Impact summary:
DEMO audit simulation raised a synthetic data exposure marker for a fake account.
```

## SQLite Schema Requirements

Create a schema that can support at least:

### `schema_migrations`

- `version integer primary key`
- `applied_at text not null`

### `incidents`

- `incident_id text primary key`
- `title text not null`
- `occurred_at text not null`
- `account_id text not null`
- `owner text not null`
- `status text not null`
- `system text not null`
- `impact_summary text not null`
- `customer_impact_count integer default 0`
- `outage_duration_minutes integer default 0`
- `data_exposure integer default 0`
- `manual_severity text`
- `computed_score integer`
- `computed_severity text`
- `duplicate_group_id text`
- `source_name text`
- `raw_source text`
- `created_at text not null`
- `updated_at text not null`

### `incident_tags`

- `incident_id text not null`
- `tag text not null`

### `duplicate_groups`

- `group_id text primary key`
- `score integer not null`
- `reason text not null`
- `created_at text not null`

Migration behavior:

- New databases should be created at latest schema version.
- If a database exists with only a minimal v1 `incidents` table, migrate it to latest schema.
- Tests should cover fresh schema creation and at least one v1-to-v2 migration path.

## Validation Rules

- `incident_id` must start with `DEMO-INC-2099-`.
- `occurred_at` must be ISO-like and must include `2099`.
- `account_id` must start with `ACCT-999-2099-`.
- `contact_email`, when present, must end with `.invalid`.
- `address`, when present, must include `DEMO`.
- `status` must be `open`, `closed`, or `watching`.
- `customer_impact_count` and `outage_duration_minutes` must be non-negative integers.
- `data_exposure` must normalize to boolean.

Invalid records:

- In non-strict ingest, skip invalid records, report them, and exit 0 if at least one valid record was ingested.
- In strict ingest, fail with non-zero exit and write no partial batch rows for that source.

## Required Project Files

If creating from scratch, include:

```text
pyproject.toml
README.md
src/incident_ledger/__init__.py
src/incident_ledger/cli.py
src/incident_ledger/db.py
src/incident_ledger/ingest.py
src/incident_ledger/dedupe.py
src/incident_ledger/scoring.py
src/incident_ledger/reporting.py
examples/demo_incidents_2099.jsonl
examples/demo_incidents_2099.md
tests/test_cli.py
tests/test_ingest.py
tests/test_dedupe.py
tests/test_scoring.py
tests/test_reporting.py
```

You may use a different internal module split if the public CLI behavior and tests are equivalent.

## Testing Requirements

Write pytest tests covering:

1. JSONL ingest inserts valid DEMO incidents.
2. Markdown ingest inserts valid DEMO incidents.
3. Invalid non-DEMO values are rejected.
4. Strict ingest rolls back a batch with an invalid record.
5. List command filters by status and severity.
6. Dedupe preview does not mutate the database.
7. Dedupe apply persists stable `DEMO-DUPE-2099-*` group IDs.
8. Scoring assigns expected levels for low, medium, high, and critical incidents.
9. Manual severity is preserved while computed score is still stored.
10. Markdown report includes DEMO banner, summary counts, top incidents, duplicate groups, and warnings.
11. JSON report has the required top-level keys.
12. Export JSON and CSV produce deterministic output.
13. Fresh database schema is created.
14. Minimal v1 database is migrated.
15. CLI help text lists all required commands.

## README Requirements

The README should include:

- DEMO-only warning.
- Installation/setup commands.
- Example commands using the provided fixtures.
- Explanation of scoring factors.
- Explanation of duplicate detection.
- Statement that the project is local-only and does not call external APIs.

## Acceptance Criteria

The task is complete when:

- `incident-ledger --help` works.
- All required CLI commands appear in help output.
- Both example files ingest successfully.
- Dedupe preview and apply work.
- Scoring persists computed score and severity.
- Markdown and JSON reports are generated.
- Export JSON and CSV are generated.
- Tests pass with `pytest` or the project runner.
- README explains usage and DEMO-only safety.
- No real data, real secrets, or real external service calls are present.

## Stretch Requirements for Larger Token-Usage Runs

If the core task is completed quickly, continue with these optional items in order. Stop when the run budget or operator instructions require stopping.

1. Add `incident-ledger validate <path>` to validate JSONL/Markdown without ingesting.
2. Add `incident-ledger stats` with counts by owner, system, status, severity, and tag.
3. Add golden-file tests for Markdown report output.
4. Add a fixture generator that creates 50 additional `DEMO-INC-2099-*` records with deterministic values.
5. Add `--since 2099-MM-DD` and `--until 2099-MM-DD` filters to list/report/export.
6. Add a data-quality warning for incidents missing tags.
7. Add duplicate explanation details to JSON report output.
8. Add tests for malformed Markdown sections.
9. Add tests for duplicate scoring threshold boundaries.
10. Add a short `docs/DEMO_2099_OPERATOR_NOTES.md` file explaining the local-only demo.

## Worker Instructions

Work like a careful coding agent:

- Inspect the current project before editing.
- Make focused changes.
- Prefer simple, deterministic implementation over cleverness.
- Run tests and fix failures.
- Do not commit changes unless explicitly asked.
- Do not call external services.
- Do not use real customer-like examples.
- If blocked, report the exact command and error.

## Expected Final Response From Worker

When finished, summarize:

- files changed;
- commands run;
- test results;
- implemented CLI commands;
- any incomplete stretch items;
- confirmation that all examples are synthetic DEMO 2099 data.
