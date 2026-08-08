import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { act, create } from "react-test-renderer";
import { createServer } from "vite";

import { runRenderedBrowserContract } from "./browser-contract.mjs";

const frontendRoot = fileURLToPath(new URL("../", import.meta.url));
let server;
let browserBaseUrl;
let EvidenceDrawer;
let EvidenceDrawerState;

function browserExecutable() {
  return [
    process.env.CHROME_BIN,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
  ].find((path) => path && existsSync(path)) || null;
}

before(async () => {
  server = await createServer({
    root: frontendRoot,
    appType: "mpa",
    logLevel: "silent",
    server: { host: "127.0.0.1", port: 0 },
  });
  await server.listen();
  browserBaseUrl = `http://127.0.0.1:${server.httpServer.address().port}`;
  ({ EvidenceDrawer, EvidenceDrawerState } = await server.ssrLoadModule("/src/views/Board.jsx"));
});

after(async () => {
  await server?.close();
});

const minimalTask = {
  id: "task-demo-999",
  summary: { text: "DEMO evidence task" },
  review_prompt: { text: "" },
  controls: {},
  estimate_tokens: 144,
  actual_tokens: 89,
};

const activeReport = {
  summary: { adapter_id: "demo-adapter", tracking_mode: "native_usage" },
  freshness: { active: true },
};

test("Evidence Drawer renders the dialog and estimate-versus-actual lead", () => {
  const markup = renderToStaticMarkup(
    React.createElement(EvidenceDrawerState, {
      task: minimalTask,
      projectId: "demo-999",
      data: activeReport,
      error: null,
      loading: false,
    }),
  );
  assert.match(markup, /role="dialog"/);
  assert.match(markup, /aria-modal="true"/);
  // The dialog must be programmatically focusable so focus can move into it on open.
  assert.match(markup, /<aside[^>]*\btabindex="-1"/);
  assert.match(markup, /aria-label="Evidence for DEMO evidence task"/);
  assert.match(markup, /class="token-comparison" role="group" aria-label="Estimate versus actual tokens"/);
  assert.match(markup, /<small>Estimate<\/small><strong>144<\/strong>/);
  assert.match(markup, /<small>Actual · −38%<\/small><strong>89<\/strong>/);
  assert.match(markup, /Spend tracking · demo-adapter · native_usage/);
});

test("active Evidence Drawer refreshes its Session Report every five seconds", async (t) => {
  const originalDocument = globalThis.document;
  const originalHTMLElement = globalThis.HTMLElement;
  const originalWindow = globalThis.window;
  let intervalCallback = null;
  let intervalMs = null;
  let requests = 0;
  globalThis.document = { activeElement: null, addEventListener() {}, removeEventListener() {} };
  globalThis.HTMLElement = class {};
  globalThis.window = {
    setInterval(callback, ms) {
      intervalCallback = callback;
      intervalMs = ms;
      return 999;
    },
    clearInterval() {},
  };
  t.after(() => {
    globalThis.document = originalDocument;
    globalThis.HTMLElement = originalHTMLElement;
    globalThis.window = originalWindow;
  });

  const task = { ...minimalTask, session_href: "/sessions/demo-999" };
  const getJSONImpl = async () => {
    requests += 1;
    return activeReport;
  };
  let renderer;
  await act(async () => {
    renderer = create(React.createElement(EvidenceDrawer, {
      task,
      projectId: "demo-999",
      getJSONImpl,
    }));
  });
  assert.equal(requests, 1);
  assert.equal(intervalMs, 5000);
  await act(async () => {
    intervalCallback();
    await new Promise((resolve) => setImmediate(resolve));
  });
  assert.equal(requests, 2);
  await act(async () => renderer.unmount());
});

test("Evidence Drawer contains Tab focus and restores its opener in rendered Portal behavior", { timeout: 30000 }, async () => {
  const browser = browserExecutable();
  assert.ok(browser, "Chromium or Chrome is required for the rendered Evidence Drawer contract");
  await runRenderedBrowserContract({
    browser,
    url: `${browserBaseUrl}/static/react/tests/ledger-browser-contract.html`,
    args: ["--force-prefers-reduced-motion=reduce", "--window-size=1100,900", "--virtual-time-budget=5000"],
  });
});
