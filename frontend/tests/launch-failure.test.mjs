import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const frontendRoot = fileURLToPath(new URL("../", import.meta.url));
let server;
let BoardState;

before(async () => {
  server = await createServer({
    root: frontendRoot,
    appType: "custom",
    logLevel: "silent",
    server: { middlewareMode: true },
  });
  ({ BoardState } = await server.ssrLoadModule("/src/views/Board.jsx"));
});

after(async () => {
  await server?.close();
});

// An Estimated card whose last launch failed but stays retryable — the board
// contract carries a slim `launch_failure` the card must surface.
function pipelineData(launchFailure) {
  return {
    project: { name: "checkout-service" },
    workspace: {
      project: { name: "checkout-service", root_path: "/repo", capability: {}, profile: {} },
      summary: { launch_ready: true },
      controls: {},
      links: {},
    },
    needs_you: { count: 0, items: [] },
    board_empty_states: { Estimated: "No Estimated tasks" },
    adapters: [{ id: "codex", name: "Codex", is_default: true, launchable: true, allowed_models: ["gpt-5.6-terra"], tracking: {} }],
    automation: { queue: { status: "idle" } },
    tasks_by_status: {
      Estimated: [{
        id: "task-retry-1",
        status: "Estimated",
        summary: { text: "Add device-flow login" },
        estimate_tokens: 42000,
        actual_tokens: null,
        recommended_model: "gpt-5.6-terra",
        launch_model: null,
        session_href: null,
        blocked_condition: null,
        launch_failure: launchFailure,
        controls: { can_launch: true },
      }],
      Running: [],
      Review: [],
      Done: [],
    },
  };
}

const render = (launchFailure) =>
  renderToStaticMarkup(
    React.createElement(BoardState, {
      projectId: "demo",
      surface: "pipeline",
      data: pipelineData(launchFailure),
      error: null,
      loading: false,
      action: () => {},
    }),
  );

test("a retryable launch failure is annotated on the still-launchable card", () => {
  const markup = render({
    error: { text: "Worker adapter launch failed.", truncated: false },
    summary: { text: "Command timed out after 60 seconds.", truncated: false },
    returncode: 124,
    retryable: true,
    diagnostic: { text: "", truncated: false },
    next_action: { text: "Retry once the network settles.", truncated: false },
    setup_href: null,
  });
  assert.match(markup, /class="status-pill status-pill-danger"/);
  assert.match(markup, /class="status-pill-glyph" aria-hidden="true">✕<\/span>/);
  assert.match(markup, /Last launch failed · retryable/);
  assert.match(markup, /Worker adapter launch failed\./);
  assert.match(markup, /Command timed out after 60 seconds\. \(exit 124\)/);
  assert.match(markup, /Retry once the network settles\./);
  // It stays launchable — the annotation coexists with the launch form, not a gate.
  assert.match(markup, /<button[^>]*>Launch<\/button>/);
});

test("a setup diagnostic leads the reason when present", () => {
  const markup = render({
    error: { text: "Worker adapter launch failed.", truncated: false },
    summary: { text: "stderr detail", truncated: false },
    returncode: null,
    retryable: true,
    diagnostic: { text: "Not inside a trusted directory.", truncated: false },
    next_action: { text: "", truncated: false },
    setup_href: "/settings/workers?adapter_id=codex",
  });
  assert.match(markup, /Not inside a trusted directory\./);
});

test("no launch_failure means no failure annotation", () => {
  const markup = render(null);
  assert.doesNotMatch(markup, /Last launch failed/);
});
