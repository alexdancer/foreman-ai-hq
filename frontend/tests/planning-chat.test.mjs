import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { act, create } from "react-test-renderer";
import { createServer } from "vite";

const frontendRoot = fileURLToPath(new URL("../", import.meta.url));
let server;
let PlanningChatState;
let PlanningChat;
let drainPlanningEvents;
let breakdownReviewHref;
let NavContext;

before(async () => {
  server = await createServer({
    root: frontendRoot,
    appType: "custom",
    logLevel: "silent",
    server: { middlewareMode: true },
  });
  ({ PlanningChatState, breakdownReviewHref, drainPlanningEvents, default: PlanningChat } = await server.ssrLoadModule("/src/views/PlanningChat.jsx"));
  ({ NavContext } = await server.ssrLoadModule("/src/nav.jsx"));
});

after(async () => {
  await server?.close();
});

const baseProps = {
  projectId: "demo-999",
  loading: false,
  error: null,
  started: true,
  transcript: [],
  message: "",
  attachment: null,
  sending: false,
  onMessageChange: () => {},
  onFileChange: () => {},
  onSend: () => {},
  onIntake: () => {},
  onCancel: () => {},
};

const renderState = (overrides = {}) =>
  renderToStaticMarkup(React.createElement(PlanningChatState, { ...baseProps, ...overrides }));

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function makeFetch(events = []) {
  let messageResolve = null;
  let intakeResolve = null;
  const requests = [];
  const fetchMock = async (url, options = {}) => {
    requests.push({ url, options });
    if (url.includes("/planning/start")) {
      return jsonResponse({ planning_session_id: "sess-plan-999" });
    }
    if (url.includes("/planning/events")) {
      return jsonResponse({ events, next_since_id: events.length ? events.at(-1).id : 0, has_more: false });
    }
    if (url.includes("/planning/message")) {
      return new Promise((resolve) => {
        messageResolve = resolve;
      });
    }
    if (url.includes("/planning/intake")) {
      return new Promise((resolve) => {
        intakeResolve = resolve;
      });
    }
    if (url.includes("/planning/cancel")) {
      return jsonResponse({ cancelled: true });
    }
    return new Response("not found", { status: 404 });
  };
  return {
    fetchMock,
    requests,
    getMessageResolve: () => messageResolve,
    getIntakeResolve: () => intakeResolve,
  };
}

test("PlanningChatState renders the loading state while starting", () => {
  const markup = renderState({ loading: true, started: false });
  assert.match(markup, /Starting planning conversation…/);
});

test("PlanningChatState invites the first message when the conversation is empty", () => {
  const markup = renderState({ started: true, transcript: [] });
  assert.match(markup, /No turns yet/);
  assert.match(markup, /Send the first message/);
  // The spec requires the composer usable for that first message, not just the prompt.
  assert.doesNotMatch(markup.match(/<textarea[^>]*>/)[0], /disabled/);
});

test("PlanningChatState renders operator and orchestrator turns in the live-feed idiom", () => {
  const markup = renderState({
    transcript: [
      { id: 1, operator: "Add caching", content: "I will add a bounded cache.", stopReason: null },
    ],
  });
  assert.match(markup, /operator/);
  assert.match(markup, /Add caching/);
  assert.match(markup, /orchestrator/);
  assert.match(markup, /I will add a bounded cache\./);
});

test("PlanningChatState shows a cancelled indicator on a cancelled turn", () => {
  const markup = renderState({
    transcript: [
      { id: 1, operator: "Never mind", content: "partial response", stopReason: "cancelled" },
    ],
  });
  assert.match(markup, /cancelled/);
  assert.match(markup, /partial response/);
});

test("PlanningChatState renders a capacity state on 503", () => {
  const error = Object.assign(new Error("planning conversation capacity full"), { status: 503 });
  const markup = renderState({ started: false, error });
  assert.match(markup, /planning conversation capacity full/);
  assert.match(markup, /class="notice warning"/);
});

test("PlanningChatState renders a not-found state on 404 before start", () => {
  const error = Object.assign(new Error("project not found"), { status: 404 });
  const markup = renderState({ started: false, error });
  assert.match(markup, /Project not found/);
});

test("PlanningChatState renders a sign-in state on 401", () => {
  const error = Object.assign(new Error("unauthorized"), { status: 401 });
  const markup = renderState({ started: false, error });
  assert.match(markup, /requires sign-in/);
});

test("PlanningChatState renders the provider sign-in state on a provider-auth 401", () => {
  const error = Object.assign(
    new Error("Provider authentication required; run `pi /login` or add an API key in pi."),
    { status: 401 },
  );
  const markup = renderState({ started: false, error });
  assert.match(markup, /Provider authentication required/);
  assert.match(markup, /pi \/login/);
  assert.doesNotMatch(markup, /requires sign-in/);
});

test("PlanningChatState disables the composer while a turn is in flight and shows Cancel", () => {
  const markup = renderState({ started: true, sending: "message", message: "do this" });
  assert.match(markup, /disabled/);
  assert.match(markup, /Sending…/);
  assert.match(markup, /Cancel/);
});

test("PlanningChatState separates conversational Send from governed intake", () => {
  const markup = renderState({ message: "# Shape this\n\n- [ ] Preserve structure" });
  assert.match(markup, /<textarea[\s\S]*># Shape this\n\n- \[ \] Preserve structure<\/textarea>/);
  assert.match(markup, />Send</);
  assert.match(markup, /Create governed work/);
  assert.match(markup, /Markdown intake/);
});

test("PlanningChat drains every transcript page before enabling the composer", async () => {
  const requested = [];
  const pages = new Map([
    ["0", { events: [{ id: 1 }], next_since_id: 1, has_more: true }],
    ["1", { events: [{ id: 2 }], next_since_id: 2, has_more: true }],
    ["2", { events: [{ id: 3 }], next_since_id: 3, has_more: false }],
  ]);
  const events = await drainPlanningEvents("/api/projects/demo-999/planning", async (url) => {
    requested.push(url);
    return pages.get(new URL(url, "https://example.invalid").searchParams.get("since_id"));
  });

  assert.deepEqual(events.map((event) => event.id), [1, 2, 3]);
  assert.deepEqual(requested, [
    "/api/projects/demo-999/planning/events?since_id=0",
    "/api/projects/demo-999/planning/events?since_id=1",
    "/api/projects/demo-999/planning/events?since_id=2",
  ]);
});

test("PlanningChat loads the transcript on open", async () => {
  const events = [
    {
      id: 1,
      created_at: "2099-01-01T00:00:00Z",
      detail: { operator_message: "Plan auth", text: "Add token auth.", stop_reason: null },
    },
  ];
  const { fetchMock, requests } = makeFetch(events);
  globalThis.fetch = fetchMock;

  let renderer;
  await act(async () => {
    renderer = create(React.createElement(PlanningChat, { projectId: "demo-999" }));
  });

  assert.match(JSON.stringify(renderer.toJSON()), /Plan auth/);
  assert.match(JSON.stringify(renderer.toJSON()), /Add token auth\./);
  assert.ok(requests.some((r) => r.url.includes("/planning/start")));
  assert.ok(requests.some((r) => r.url.includes("/planning/events?since_id=0")));

  await act(async () => {
    renderer.unmount();
  });
});

test("PlanningChat sends a conversational message and appends the returned turn", async () => {
  const { fetchMock, requests, getMessageResolve } = makeFetch([]);
  globalThis.fetch = fetchMock;

  let renderer;
  await act(async () => {
    renderer = create(React.createElement(PlanningChat, { projectId: "demo-999" }));
  });

  const input = renderer.root.findByProps({ placeholder: "Describe the task or goal…" });
  const form = renderer.root.findByType("form");

  await act(async () => {
    input.props.onChange({ target: { value: "Add tests" } });
  });

  await act(async () => {
    form.props.onSubmit({ preventDefault: () => {} });
  });

  const messageRequests = requests.filter((r) => r.url.includes("/planning/message"));
  assert.equal(messageRequests.length, 1);
  assert.deepEqual(JSON.parse(messageRequests[0].options.body), { message: "Add tests" });
  assert.equal(requests.filter((r) => r.url.includes("/planning/intake")).length, 0);

  assert.equal(renderer.root.findByProps({ placeholder: "Describe the task or goal…" }).props.disabled, true);
  assert.ok(JSON.stringify(renderer.toJSON()).includes("Sending…"));

  await act(async () => {
    getMessageResolve()(jsonResponse({ content: "I'll add tests.", stop_reason: null }));
  });

  const markup = JSON.stringify(renderer.toJSON());
  assert.match(markup, /Add tests/);
  assert.match(markup, /I'll add tests\./);
  assert.equal(renderer.root.findByProps({ placeholder: "Describe the task or goal…" }).props.disabled, false);

  await act(async () => {
    renderer.unmount();
  });
});

test("PlanningChat submits governed intake only from the explicit intake action", async () => {
  const { fetchMock, requests, getIntakeResolve } = makeFetch([]);
  globalThis.fetch = fetchMock;

  let renderer;
  await act(async () => {
    renderer = create(React.createElement(PlanningChat, { projectId: "demo-999" }));
  });

  const input = renderer.root.findByProps({ placeholder: "Describe the task or goal…" });
  await act(async () => {
    input.props.onChange({ target: { value: "# Create a bounded task\n\n- [ ] Preserve line breaks" } });
  });
  const intakeButton = renderer.root.findAllByType("button")
    .find((button) => button.children.join("").includes("Create governed work"));

  await act(async () => {
    intakeButton.props.onClick();
  });

  const intakeRequests = requests.filter((request) => request.url.includes("/planning/intake"));
  assert.equal(intakeRequests.length, 1);
  assert.equal(
    intakeRequests[0].options.body.get("message"),
    "# Create a bounded task\n\n- [ ] Preserve line breaks",
  );
  assert.equal(requests.filter((request) => request.url.includes("/planning/message")).length, 0);
  assert.doesNotMatch(JSON.stringify(renderer.toJSON()), /Cancel/);

  await act(async () => {
    getIntakeResolve()(jsonResponse({
      content: "Intake decision: single_task. One bounded slice.",
      stop_reason: "end_turn",
      outcome: { decision: "single_task", reason: "One bounded slice." },
    }));
  });

  assert.match(JSON.stringify(renderer.toJSON()), /Intake decision: single_task/);

  await act(async () => {
    renderer.unmount();
  });
});

test("PlanningChat opens the validated review destination for breakdown intake", async () => {
  const { fetchMock, getIntakeResolve } = makeFetch([]);
  globalThis.fetch = fetchMock;
  const navigations = [];

  assert.equal(
    breakdownReviewHref({ decision: "needs_breakdown", next_href: "/task-breakdowns/bd-123/review" }),
    "/task-breakdowns/bd-123/review",
  );
  assert.equal(
    breakdownReviewHref({ decision: "needs_breakdown", next_href: "https://example.invalid/review" }),
    null,
  );
  assert.equal(
    breakdownReviewHref({ decision: "single_task", next_href: "/task-breakdowns/bd-123/review" }),
    null,
  );

  let renderer;
  await act(async () => {
    renderer = create(
      React.createElement(
        NavContext.Provider,
        { value: (href) => navigations.push(href) },
        React.createElement(PlanningChat, { projectId: "demo-999" }),
      ),
    );
  });

  const input = renderer.root.findByProps({ placeholder: "Describe the task or goal…" });
  await act(async () => {
    input.props.onChange({ target: { value: "# Split this work" } });
  });
  const intakeButton = renderer.root.findAllByType("button")
    .find((button) => button.children.join("").includes("Create governed work"));
  await act(async () => {
    intakeButton.props.onClick();
  });
  await act(async () => {
    getIntakeResolve()(jsonResponse({
      content: "Intake decision: needs_breakdown.",
      stop_reason: "end_turn",
      outcome: {
        decision: "needs_breakdown",
        reason: "Multiple bounded slices.",
        next_href: "/task-breakdowns/bd-123/review",
      },
    }));
  });

  assert.deepEqual(navigations, ["/task-breakdowns/bd-123/review"]);

  await act(async () => {
    renderer.unmount();
  });
});

test("PlanningChat cancels an in-flight turn and renders the partial result", async () => {
  const { fetchMock, requests, getMessageResolve } = makeFetch([]);
  globalThis.fetch = fetchMock;

  let renderer;
  await act(async () => {
    renderer = create(React.createElement(PlanningChat, { projectId: "demo-999" }));
  });

  const input = renderer.root.findByProps({ placeholder: "Describe the task or goal…" });
  const form = renderer.root.findByType("form");

  await act(async () => {
    input.props.onChange({ target: { value: "Big refactor" } });
  });

  await act(async () => {
    form.props.onSubmit({ preventDefault: () => {} });
  });

  let buttons = renderer.root.findAllByType("button");
  const cancelButton = buttons.find((b) => b.children.join("").includes("Cancel"));
  assert.ok(cancelButton);

  await act(async () => {
    cancelButton.props.onClick();
  });

  assert.ok(requests.some((r) => r.url.includes("/planning/cancel")));

  await act(async () => {
    getMessageResolve()(jsonResponse({ content: "partial plan", stop_reason: "cancelled" }));
  });

  const markup = JSON.stringify(renderer.toJSON());
  assert.match(markup, /Big refactor/);
  assert.match(markup, /partial plan/);
  assert.match(markup, /cancelled/);
  assert.equal(renderer.root.findByProps({ placeholder: "Describe the task or goal…" }).props.disabled, false);

  await act(async () => {
    renderer.unmount();
  });
});

// 9.7: the board refresh is an operator-initiated consequence of a completed turn,
// so it must fire exactly once per turn and never depend on background polling.
test("PlanningChat notifies once when a turn completes", async () => {
  const { fetchMock, getMessageResolve } = makeFetch([]);
  globalThis.fetch = fetchMock;

  const completions = [];
  let renderer;
  await act(async () => {
    renderer = create(React.createElement(PlanningChat, {
      projectId: "demo-999",
      onTurnComplete: (turn) => completions.push(turn),
    }));
  });

  const input = renderer.root.findByProps({ placeholder: "Describe the task or goal…" });
  const form = renderer.root.findByType("form");

  await act(async () => {
    input.props.onChange({ target: { value: "Add tests" } });
  });
  await act(async () => {
    form.props.onSubmit({ preventDefault: () => {} });
  });

  assert.equal(completions.length, 0, "an in-flight turn must not refresh the board");

  await act(async () => {
    getMessageResolve()(jsonResponse({ content: "I'll add tests.", stop_reason: null }));
  });

  assert.equal(completions.length, 1);

  await act(async () => {
    renderer.unmount();
  });
});
