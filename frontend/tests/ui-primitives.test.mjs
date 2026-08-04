import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const frontendRoot = fileURLToPath(new URL("../", import.meta.url));
let server;
let Button;
let Pill;
let Notice;
let EmptyState;
let Loading;
let Panel;
let PanelHeader;
let PanelBody;
let Fieldset;
let Disclosure;
let DataTable;
let Row;
let ColumnHead;
let DataCell;
let StatusPill;
let capabilityStatusTone;
let statusTone;
let trackingStatusTone;
let Skeleton;
let StickyActionBar;
let ConfirmSheet;
let Toast;
let TokenComparison;
let EventRow;
let EvidenceDisclosure;
let tokensCss;
let loginTemplate;
let portalSources;

async function readSourceTree(root) {
  const entries = await readdir(root, { withFileTypes: true });
  const contents = await Promise.all(entries.map(async (entry) => {
    const path = join(root, entry.name);
    return entry.isDirectory() ? readSourceTree(path) : readFile(path, "utf8");
  }));
  return contents.flat(Infinity).join("\n");
}

before(async () => {
  server = await createServer({
    root: frontendRoot,
    appType: "custom",
    logLevel: "silent",
    server: { middlewareMode: true },
  });
  ({
    Button,
    Pill,
    Notice,
    EmptyState,
    Loading,
    Panel,
    PanelHeader,
    PanelBody,
    Fieldset,
    Disclosure,
    DataTable,
    Row,
    ColumnHead,
    DataCell,
    StatusPill,
    capabilityStatusTone,
    statusTone,
    trackingStatusTone,
    Skeleton,
    StickyActionBar,
    ConfirmSheet,
    Toast,
    TokenComparison,
    EventRow,
    EvidenceDisclosure,
  } = await server.ssrLoadModule("/src/components/ui/index.js"));
  tokensCss = await readFile(new URL("../src/tokens.css", import.meta.url), "utf8");
  loginTemplate = await readFile(new URL("../../src/foreman_ai_hq/templates/login.html", import.meta.url), "utf8");
  portalSources = [
    await readSourceTree(fileURLToPath(new URL("../src", import.meta.url))),
    await readSourceTree(fileURLToPath(new URL("../../src/foreman_ai_hq/templates", import.meta.url))),
  ].join("\n");
});

after(async () => {
  await server?.close();
});

const html = (element) => renderToStaticMarkup(element);

test("Button maps variant and size onto the shared .btn classes", () => {
  assert.match(html(React.createElement(Button, {}, "Go")), /^<button class="btn">Go<\/button>$/);
  assert.match(
    html(React.createElement(Button, { size: "small" }, "Go")),
    /class="btn small"/,
  );
  assert.match(
    html(React.createElement(Button, { size: "small", variant: "secondary" }, "Go")),
    /class="btn small secondary"/,
  );
  assert.match(
    html(React.createElement(Button, { variant: "danger" }, "Go")),
    /class="btn danger"/,
  );
});

test("Button is polymorphic and forwards arbitrary props", () => {
  const asAnchor = html(React.createElement(Button, { as: "a", href: "/x", variant: "secondary", size: "small" }, "Link"));
  assert.match(asAnchor, /^<a class="btn small secondary" href="\/x">Link<\/a>$/);

  const withType = html(React.createElement(Button, { type: "submit" }, "Save"));
  assert.match(withType, /type="submit"/);
});

test("Pill keeps its tone modifier and text label", () => {
  assert.match(html(React.createElement(Pill, { tone: "green" }, "ready")), /^<span class="pill green">ready<\/span>$/);
  assert.match(html(React.createElement(Pill, {}, "idle")), /^<span class="pill">idle<\/span>$/);
});

test("Notice maps variant to the shared classes and forwards role", () => {
  assert.match(html(React.createElement(Notice, {}, "fyi")), /^<div class="notice">fyi<\/div>$/);
  assert.match(html(React.createElement(Notice, { variant: "warning" }, "w")), /class="notice warning"/);
  assert.match(
    html(React.createElement(Notice, { variant: "danger", role: "alert" }, "e")),
    /class="notice danger" role="alert"/,
  );
});

test("EmptyState and Loading wrap their shared classes", () => {
  assert.match(html(React.createElement(EmptyState, {}, "nothing here")), /^<div class="empty-state">nothing here<\/div>$/);
  assert.match(html(React.createElement(Loading, {}, "Loading Pipeline…")), /^<p class="spinner">Loading Pipeline…<\/p>$/);
  assert.match(html(React.createElement(Loading, {})), /Loading…/);
});

test("Panel trio composes header markers three ways", () => {
  const withCount = html(React.createElement(PanelHeader, { title: "Estimated", count: 3 }));
  assert.match(withCount, /<div class="panel-header"><h3>Estimated<\/h3><span class="column-count">3<\/span><\/div>/);

  const badge = html(React.createElement(PanelHeader, { title: "Needs You", badge: React.createElement("span", { className: "nav-badge" }, 2) }));
  assert.match(badge, /<span class="nav-badge">2<\/span>/);
  assert.doesNotMatch(badge, /column-count/);

  const bare = html(React.createElement(PanelHeader, { title: "Only" }));
  assert.match(bare, /^<div class="panel-header"><h3>Only<\/h3><\/div>$/);

  const panel = html(
    React.createElement(Panel, { className: "planning-inbox", id: "p" },
      React.createElement(PanelBody, { className: "needs-you-list" }, "body")),
  );
  assert.match(panel, /^<section class="panel planning-inbox" id="p">/);
  assert.match(panel, /<div class="panel-body needs-you-list">body<\/div>/);

  const asHeader = html(React.createElement(Panel, { as: "header", className: "pipeline-header" }, "x"));
  assert.match(asHeader, /^<header class="panel pipeline-header">x<\/header>$/);
});

test("Fieldset and disclosures provide semantic grouping without nested panels", () => {
  const grouping = html(
    React.createElement(Panel, {},
      React.createElement(Fieldset, { legend: "Contract" },
        React.createElement(Disclosure, { label: "Slicing evidence", count: 3 }, "Evidence"),
        React.createElement(EvidenceDisclosure, { label: "Token log", count: 2 }, "Tokens"),
      )),
  );

  assert.match(grouping, /<fieldset class="workbench-fieldset">/);
  assert.match(grouping, /<legend[^>]*>Contract<\/legend>/);
  assert.match(grouping, /<details class="disclosure">/);
  assert.match(grouping, /<span class="disclosure-label">Slicing evidence<\/span>/);
  assert.match(grouping, /<span class="disclosure-count" aria-label="3 items">3<\/span>/);
  assert.match(grouping, /<details class="disclosure evidence-disclosure">/);
  assert.equal((grouping.match(/class="panel(?: |")/g) || []).length, 1);
  assert.doesNotMatch(grouping, /class="panel[^>]*>[\s\S]*class="panel/);
  assert.throws(
    () => html(React.createElement(Panel, {}, React.createElement(Panel, {}, "nested"))),
    /Panel cannot contain another Panel/,
  );
  assert.throws(
    () => html(React.createElement(Panel, {}, React.createElement("section", { className: "panel raw-panel" }, "nested"))),
    /Panel cannot contain another Panel/,
  );
  assert.throws(
    () => html(React.createElement(Disclosure, { label: "Evidence" }, "missing count")),
    /requires a visible count/,
  );
});

test("DataTable primitives expose table, row, and column semantics", () => {
  const table = html(
    React.createElement(DataTable, { label: "Task ledger", columns: "minmax(12rem, 1fr) 8rem" },
      React.createElement(Row, { header: true },
        React.createElement(ColumnHead, {}, "Task"),
        React.createElement(ColumnHead, {}, "Status"),
      ),
      React.createElement(Row, {},
        React.createElement(DataCell, {}, "DEMO task"),
        React.createElement(DataCell, {}, "Running"),
      ),
    ),
  );

  assert.match(table, /class="data-table-scroll"/);
  assert.match(table, /role="table" aria-label="Task ledger"/);
  assert.match(table, /style="--data-table-columns:minmax\(12rem, 1fr\) 8rem"/);
  assert.match(table, /class="data-table-row data-table-head" role="row"/);
  assert.equal((table.match(/role="columnheader"/g) || []).length, 2);
  assert.equal((table.match(/role="cell"/g) || []).length, 2);
});

test("StatusPill always renders a glyph and a text label", () => {
  const status = html(React.createElement(StatusPill, { tone: "running", label: "Running" }));
  assert.match(status, /^<span class="status-pill status-pill-running">/);
  assert.match(status, /<span class="status-pill-glyph" aria-hidden="true">◐<\/span>/);
  assert.match(status, /<span class="status-pill-label">Running<\/span>/);
  assert.throws(
    () => html(React.createElement(StatusPill, { tone: "danger" })),
    /requires a visible text label/,
  );
  assert.equal(trackingStatusTone("native_usage"), "info");
  assert.equal(trackingStatusTone("proxy_governed"), "info");
  assert.equal(trackingStatusTone("native_usage", true), "success");
  assert.equal(trackingStatusTone("proxy_governed", true), "success");
  assert.equal(trackingStatusTone("observed_only"), "warning");
  assert.equal(trackingStatusTone("unverified"), "warning");
  assert.equal(statusTone("blocked"), "warning");
  assert.equal(statusTone("failed"), "danger");
  assert.equal(capabilityStatusTone("blocked"), "warning");
});

test("loading, action, confirmation, and toast primitives expose accessible semantics", () => {
  const skeleton = html(React.createElement(Skeleton, { label: "Loading task ledger", lines: 2 }));
  assert.match(skeleton, /class="skeleton" role="status" aria-label="Loading task ledger"/);
  assert.equal((skeleton.match(/class="skeleton-bar"/g) || []).length, 2);

  const actionBar = html(React.createElement(StickyActionBar, {
    consequence: "Accepting creates 2 Tasks.",
    reason: "Load the complete candidate text first.",
    actions: React.createElement("button", { type: "button" }, "Review"),
  }));
  assert.match(actionBar, /class="sticky-action-bar"/);
  assert.match(actionBar, /Accepting creates 2 Tasks\./);
  assert.match(actionBar, /class="sticky-action-reason" role="status"/);

  const sheet = html(React.createElement(ConfirmSheet, {
    open: true,
    onClose: () => {},
    title: "Create Tasks?",
    description: "This confirmation does not submit on its own.",
    actions: React.createElement("button", { type: "button" }, "Confirm"),
  }, React.createElement("p", {}, "Task A")));
  assert.match(sheet, /class="confirm-sheet" role="dialog" aria-modal="true"/);
  assert.match(sheet, /aria-labelledby=/);
  assert.match(sheet, /aria-describedby=/);
  assert.match(sheet, /tabindex="-1"/);
  assert.match(sheet, /This confirmation does not submit on its own\./);
  assert.throws(
    () => html(React.createElement(ConfirmSheet, { open: true, title: "Missing close" })),
    /requires onClose while open/,
  );

  const toast = html(React.createElement(Toast, { title: "Saved" }, "Draft remains local."));
  assert.match(toast, /class="toast" role="status" aria-live="polite"/);
  assert.match(toast, /<strong>Saved<\/strong>/);
  const dangerToast = html(React.createElement(Toast, { tone: "danger", title: "Failed" }, "Retry."));
  assert.match(dangerToast, /class="toast toast-danger" role="alert" aria-live="assertive"/);
});

test("disabled controls render and associate a persistent reason", () => {
  assert.throws(
    () => html(React.createElement(Button, { disabled: true }, "Edit")),
    /requires disabledReason/,
  );
  const button = html(React.createElement(Button, {
    disabled: true,
    disabledReason: "Load the complete field before editing.",
  }, "Edit"));
  assert.match(button, /class="disabled-control"/);
  assert.match(button, /<button class="btn" disabled="" aria-describedby="[^"]+">Edit<\/button>/);
  assert.match(button, /class="disabled-reason"[^>]*>Load the complete field before editing\.<\/span>/);

  assert.throws(
    () => html(React.createElement(Fieldset, { legend: "Proof", disabled: true }, "fields")),
    /requires disabledReason/,
  );
  const fieldset = html(React.createElement(Fieldset, {
    legend: "Proof",
    disabled: true,
    disabledReason: "Load the complete evidence first.",
  }, React.createElement("input", { value: "preview", readOnly: true })));
  assert.match(fieldset, /<fieldset class="workbench-fieldset" disabled="" aria-describedby="[^"]+">/);
  assert.match(fieldset, /class="disabled-reason" id="[^"]+">Load the complete evidence first\.<\/p>/);
});

test("TokenComparison and EventRow provide shared ledger evidence presentation", () => {
  const comparison = html(React.createElement(TokenComparison, {
    estimate: 100,
    actual: 89,
    provenance: "native usage",
  }));
  assert.match(comparison, /class="token-comparison" aria-label="Estimate versus actual tokens"/);
  assert.match(comparison, /<small>Estimate<\/small><strong>100<\/strong>/);
  assert.match(comparison, /<small>Actual · −11%<\/small><strong>89<\/strong>/);
  assert.match(comparison, /class="token-comparison-provenance">Spend tracking · native usage<\/p>/);

  const event = html(React.createElement(EventRow, {
    time: "00:00:00",
    kind: "token",
    note: " · provisional",
  }, "15 tokens"));
  assert.match(event, /^<li class="live-event live-event-token event-row">/);
  assert.match(event, /<span class="live-event-time">00:00:00<\/span>/);
  assert.match(event, /<span class="live-event-kind">token<\/span>/);
  assert.match(event, /15 tokens<em class="live-event-note"> · provisional<\/em>/);
});

test("Ledger CSS publishes role tokens and removes only the retired alias", () => {
  for (const contract of [
    "--surface-canvas: #0a0e11;",
    "--surface-sunken: #0b1013;",
    "--surface-panel: #10161a;",
    "--surface-raised: #161d23;",
    "--surface-hover: #131a20;",
    "--text-primary: #e8eef3;",
    "--text-secondary: #a8b4be;",
    "--text-tertiary: #6f7c88;",
    "--text-quiet: #4a555f;",
    "--line: #1e262d;",
    "--line-faint: #131a20;",
    "--line-strong: #2b353e;",
    "--mint: #5cf2c4;",
    "--mint-edge: #2a8d72;",
    "--mint-ink: #04120e;",
    "--info: #5cb8f2;",
    "--warn: #f2c45c;",
    "--danger: #f25c5c;",
    "--purple: #b58cf2;",
    "--bg-0: var(--surface-canvas);",
    "--bg-1: var(--surface-panel);",
    "--bg-2: var(--surface-raised);",
    "--line-2: var(--line-strong);",
    "--fg-0: var(--text-primary);",
    "--fg-1: var(--text-secondary);",
    "--fg-2: var(--text-tertiary);",
    "--fg-3: var(--text-quiet);",
    "--accent: var(--mint);",
    "--accent-dim: var(--mint-edge);",
  ]) assert.ok(tokensCss.includes(contract), `missing token contract: ${contract}`);
  assert.doesNotMatch(portalSources, /--bg-3\b|var\(--bg-3\)/);
});

test("Ledger CSS preserves focus, reduced-motion, and select sizing contracts", () => {
  assert.match(tokensCss, /:where\(a, area\[href\], button, input, select, textarea, summary, \[contenteditable="true"\], \[tabindex\]:not\(\[tabindex="-1"\]\)\):focus-visible/);
  assert.match(tokensCss, /outline: 2px solid var\(--mint\)/);
  assert.match(tokensCss, /select\s*\{[^}]*width: 100%;[^}]*max-width: 100%;[^}]*min-width: 0;/s);
  assert.doesNotMatch(tokensCss, /skeleton-sweep|\.skeleton-bar::after/);
  assert.doesNotMatch(tokensCss, /\.disclosure-chevron\s*\{[^}]*transition:/s);
  assert.equal((tokensCss.match(/animation:[^;{}]*infinite/g) || []).length, 2);
  assert.match(tokensCss, /@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.live-pulse-dot\s*\{[^}]*animation: none;[^}]*opacity: 1;/);
  assert.match(tokensCss, /@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.board-intake-progress-bar\s*\{[^}]*animation: none;/);
  assert.match(loginTemplate, /:where\(a, button, input\):focus-visible\s*\{[^}]*outline: 2px solid var\(--mint\)/);
  assert.doesNotMatch(`${tokensCss}\n${loginTemplate}`, /:focus(?:-visible)?[^\{]*\{[^}]*outline:\s*(?:none|0(?:\D|$))/s);
});
