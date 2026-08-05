import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const frontendRoot = fileURLToPath(new URL("../", import.meta.url));
let server;
let mergeBoardLiveEvents;
let mergeLiveEvents;
let drainLiveEvents;
let runSingleFlight;
let liveEventText;
let liveEventTime;
let LiveEventRow;
let liveRunsFromTasks;
let selectedLiveRun;

before(async () => {
  server = await createServer({ root: frontendRoot, appType: "custom", logLevel: "silent", server: { middlewareMode: true } });
  ({ mergeBoardLiveEvents } = await server.ssrLoadModule("/src/views/Board.jsx"));
  ({ mergeLiveEvents } = await server.ssrLoadModule("/src/views/SessionReport.jsx"));
  ({ drainLiveEvents, runSingleFlight } = await server.ssrLoadModule("/src/live-events.js"));
  ({ liveEventText, liveEventTime, LiveEventRow } = await server.ssrLoadModule("/src/components/LiveEventFeed.jsx"));
  ({ liveRunsFromTasks, selectedLiveRun } = await server.ssrLoadModule("/src/components/LiveRunDock.jsx"));
});

after(async () => { await server?.close(); });

test("live Worker events append only to matching running Board and Session Report feeds", () => {
  const current = {
    data: {
      tasks_by_status: {
        Running: [{
          status: "Running",
          session_href: "/sessions/ses_demo_999",
          timeline: [{ id: 1, kind: "status" }],
        }],
      },
    },
  };
  const incoming = [{ id: 2, created_at: "2099-01-01T00:00:00Z", layer: "worker_harness", kind: "token", title: "Provisional usage", detail_summary: "total_tokens=9" }];

  const board = mergeBoardLiveEvents(current, "ses_demo_999", incoming);

  assert.equal(board.data.tasks_by_status.Running[0].timeline.length, 2);
  assert.equal(board.data.tasks_by_status.Running[0].timeline[1].detail_summary.text, "total_tokens=9");
  assert.deepEqual(mergeLiveEvents(incoming, incoming), incoming);
});

test("live event polling drains capped pages before advancing its cursor", async () => {
  const calls = [];
  const appended = [];
  const firstPage = Array.from({ length: 100 }, (_, index) => ({ id: index + 1 }));
  const cursor = await drainLiveEvents({
    sessionId: "ses_demo_999",
    sinceId: null,
    getEvents: async (url) => {
      calls.push(url);
      return calls.length === 1
        ? { events: firstPage, next_since_id: 100, has_more: true }
        : { events: [{ id: 101 }], next_since_id: 101, has_more: false };
    },
    append: (events) => appended.push(...events),
  });

  assert.equal(cursor, 101);
  assert.equal(appended.length, 101);
  assert.match(calls[1], /since_id=100/);
});

test("live event polling does not overlap active drains", async () => {
  const lock = { current: false };
  let started = 0;
  let release;
  const first = runSingleFlight(lock, async () => {
    started += 1;
    await new Promise((resolve) => { release = resolve; });
  });
  const second = runSingleFlight(lock, async () => { started += 1; });

  assert.equal(started, 1);
  release();
  await Promise.all([first, second]);
  assert.equal(lock.current, false);
});

test("liveEventText normalizes string and bounded summary shapes", () => {
  assert.equal(liveEventText("plain text"), "plain text");
  assert.equal(liveEventText({ text: "bounded text", truncated: false }), "bounded text");
  assert.equal(liveEventText({ text: "", truncated: false }), "");
  assert.equal(liveEventText(null), "");
  assert.equal(liveEventText(undefined), "");
});

test("LiveEventRow renders a token event with provisional usage note", () => {
  const markup = renderToStaticMarkup(React.createElement(LiveEventRow, {
    event: {
      id: 3,
      kind: "token",
      title: "Provisional usage",
      created_at: "2099-01-01T00:00:00Z",
      layer: "worker_harness",
      detail_summary: "input_tokens=12; output_tokens=3",
    },
  }));
  assert.ok(markup.includes("input_tokens=12; output_tokens=3"));
  assert.ok(markup.includes("provisional; final total recorded on completion."));
  // The kind must reach the class name, since per-kind colour keys off it.
  assert.ok(markup.includes("live-event-token"));
  assert.ok(markup.includes("event-row"));
});

test("liveEventTime shortens wire timestamps without shifting timezone", () => {
  assert.equal(liveEventTime("2026-07-20T18:40:57.345481+00:00"), "18:40:57");
  assert.equal(liveEventTime("2099-01-01T00:00:00Z"), "00:00:00");
  assert.equal(liveEventTime(""), "");
  assert.equal(liveEventTime(null), "");
});

test("the dock lists every running task so concurrent runs stay monitorable", () => {
  const runs = liveRunsFromTasks([
    { id: "T1", summary: { text: "snip save", truncated: false }, session_href: "/sessions/a", timeline: [{ id: 1 }] },
    { id: "T4", summary: { text: "", truncated: false }, session_href: "/sessions/b", timeline: [] },
  ]);

  assert.deepEqual(runs.map((run) => run.taskId), ["T1", "T4"]);
  assert.equal(runs[0].events.length, 1);
  // Titles must be unwrapped strings; a bounded object would crash the render.
  assert.equal(runs[0].title, "snip save");
  assert.equal(runs[1].title, "T4");
  assert.deepEqual(liveRunsFromTasks(undefined), []);
  assert.deepEqual(liveRunsFromTasks([]), []);
});

test("the dock falls back to a live run when the selected one finishes", () => {
  const runs = [{ taskId: "T1" }, { taskId: "T4" }];

  assert.equal(selectedLiveRun(runs, "T4").taskId, "T4");
  // T9 finished and left the Running column: fall back rather than blank out.
  assert.equal(selectedLiveRun(runs, "T9").taskId, "T1");
  assert.equal(selectedLiveRun(runs, null).taskId, "T1");
  assert.equal(selectedLiveRun([], "T1"), null);
});
