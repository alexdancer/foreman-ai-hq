# UI primitives

Thin React wrappers over the shared Ledger class vocabulary in `src/tokens.css`.
They keep behavior in views and own only semantic markup and shared presentation.
Adopting a primitive must not add data fetching, routing, persistence, or mutation.

Import through the barrel:

```jsx
import {
  Button, Pill, Notice, EmptyState, Loading,
  Panel, PanelHeader, PanelBody,
} from "../components/ui/index.js";
```

## Components

### `Button`

Wraps `.btn`. Polymorphic via `as` so one component covers real buttons,
in-shell `AppLink` navigation, and plain anchors.

```jsx
<Button size="small" type="button" onClick={launch}>Launch</Button>
<Button size="small" variant="secondary" as={AppLink} to={href}>Sessions</Button>
<Button size="small" variant="secondary" as="a" href={sessionHref}>Full Session Report</Button>
<Button size="small" variant="danger" type="button" onClick={block}>Block</Button>
```

- `variant`: `"primary"` (default, bare `.btn`) · `"secondary"` · `"danger"`
- `size`: `"small"` adds `.small`; omit for the default size
- everything else (`type`, `onClick`, `href`, `to`, `disabled`, `aria-*`) passes through
- whenever `disabled` is true, pass `disabledReason`; the visible reason is joined to the control with `aria-describedby`

### `Pill`

Wraps `.pill`. `tone` is the semantic modifier; always keep a text label.

```jsx
<Pill tone={launchReady ? "green" : "yellow"}>{launchReady ? "launch ready" : "setup needed"}</Pill>
<Pill tone={queueRunning ? "running" : "idle"}>Queue {status}</Pill>
```

### `Notice`

Wraps `.notice`. `variant` is `"info"` (default) · `"warning"` · `"danger"`.
Pass `role="alert"` for live error notices.

```jsx
<Notice variant="danger">{message}</Notice>
<Notice variant="danger" role="alert">{error}</Notice>
<Notice variant="warning"><strong>Archived project</strong><p className="muted">Restore first.</p></Notice>
```

### `EmptyState` / `Loading`

```jsx
<EmptyState>No completed runs await review.</EmptyState>
<Loading>Loading Pipeline…</Loading>
```

### `Panel` / `PanelHeader` / `PanelBody`

Wraps `.panel` / `.panel-header` / `.panel-body`. `Panel` is polymorphic (`as`,
default `<section>`); `id` and extra classes pass through.

```jsx
<Panel className="needs-you">
  <PanelHeader title="Needs You" badge={<span className="nav-badge">{count}</span>} />
  <PanelBody className="needs-you-list">{/* … */}</PanelBody>
</Panel>

// Custom trailing marker (nav badge, bare span) → pass `badge`:
<PanelHeader title="Needs You" badge={<span className="nav-badge">{count}</span>} />
<PanelHeader title="Active Worker Runs" badge={<span>{running.length}</span>} />
```

## Ledger foundations

- `Fieldset` groups controls inside a Panel. A Panel must never contain another Panel.
- `Disclosure` renders a native disclosure with a label, visible quantity, and chevron. `EvidenceDisclosure` is the evidence-specific class variant.
- `DataTable`, `Row`, `ColumnHead`, and `DataCell` render ARIA table semantics over grid rows. Set `columns` on `DataTable`; the wrapper scrolls horizontally before columns collapse.
- `StatusPill` always renders both a glyph and a text `label`. `Pill` remains the legacy compatibility primitive for existing views.
- `Skeleton` exposes a loading label through static placeholder bars.
- `StickyActionBar` keeps consequence and any blocking reason visible beside its actions.
- `ConfirmSheet` owns dialog markup, modal focus, Escape dismissal, and opener focus restoration. Callers provide `open` and `onClose`, own the existing mutation callback, and the sheet never submits by itself.
- `Toast` uses a polite status region by default and an assertive alert for danger/error messages.
- `TokenComparison` renders estimate versus actual with optional adjacent spend provenance.
- `EventRow` is the presentation shell used by `LiveEventFeed`; event normalization and polling stay in the feature component.

Every interactive control receives the shared mint `:focus-visible` treatment.
Selects are full-width, `max-width: 100%`, and `min-width: 0`. New disabled
controls must render a persistent reason rather than relying on a tooltip.

## Migration pattern

Replace hand-written presentation with a primitive while keeping callbacks,
conditions, labels, and data formatting unchanged. Keep panels flat: use a
fieldset or disclosure for grouping inside them.
