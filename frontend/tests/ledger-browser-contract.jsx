import React from "react";
import { createRoot } from "react-dom/client";

import { ConfirmSheet, Panel, PanelBody, PanelHeader, Skeleton, StatusPill } from "../src/components/ui/index.js";
import { NavContext } from "../src/nav.jsx";
import { BoardState, EvidenceDrawerState } from "../src/views/Board.jsx";
import { DashboardContent } from "../src/views/Dashboard.jsx";
import Alarms from "../src/views/Alarms.jsx";
import TaskHistory from "../src/views/TaskHistory.jsx";
import "../src/tokens.css";

const confirmSheetRef = React.createRef();

const pipelineTask = {
  id: "browser-task-999",
  status: "Estimated",
  summary: { text: "Browser launch contract", truncated: false },
  estimate_tokens: 120,
  actual_tokens: null,
  recommended_model: "gpt-browser-999",
  launch_model: null,
  session_href: null,
  task_kind: "implementation",
  blocked_condition: null,
  launch_failure: null,
  controls: {
    can_launch: true,
    can_refresh: false,
    can_archive: false,
    can_dismiss: false,
    requires_manual_estimate: false,
    budget_override_available: false,
    native_usage_override_ack_required: false,
    native_usage_override_ack_text: null,
    setup_href: "/settings/workers",
    can_save_review_prompt: false,
    can_agent_review: false,
    can_mark_done: false,
    can_block: false,
    can_approve_commit: false,
    can_open_pr: false,
    pr_unavailable_reason: null,
  },
};

const drawerReport = {
  summary: { adapter_id: "browser-adapter", tracking_mode: "native_usage" },
  freshness: { active: false },
  tokens: {
    log: {
      items: [{ usage_kind: "worker", model: "gpt-browser-999", prompt_tokens: 8, completion_tokens: 4, total_tokens: 12, cost: null, raw_usage: null }],
      pagination: { total: 1, has_more: false, next_href: null },
    },
  },
  zone_timeline: { items: [], pagination: { total: 0, has_more: false, next_href: null } },
  worker_timeline: {
    items: [{ id: 1, created_at: "2099-01-01T00:00:00Z", level: "info", layer: "worker", kind: "token", title: "Usage recorded", detail_summary: "total_tokens=12", detail: null }],
    pagination: { total: 1, has_more: false, next_href: null },
  },
  repo_context_briefs: { items: [], pagination: { total: 0, has_more: false, next_href: null } },
  alarms: { items: [], pagination: { total: 0, has_more: false, next_href: null } },
  checkpoints: { items: [], pagination: { total: 0, has_more: false, next_href: null } },
};

const pipelineData = {
  project: { id: "browser-project-999", name: "Browser project 999" },
  workspace: {
    project: {
      id: "browser-project-999",
      name: "Browser project 999",
      archived_at: null,
      capability: { state: "launch_ready", label: "Launch ready", reasons: [] },
      profile: {},
    },
    summary: { launch_ready: true, attention_actions: [] },
    controls: { can_restore: false },
    links: {},
  },
  needs_you: { project_id: "browser-project-999", count: 0, items: [] },
  adapters: [{
    id: "browser-adapter",
    name: "Browser adapter",
    is_default: true,
    launchable: true,
    allowed_models: ["gpt-browser-999"],
    tracking: { mode: "native_usage", label: "CLI native usage" },
  }],
  tasks_by_status: { Estimated: [pipelineTask], Running: [], Review: [], Done: [] },
  board_summary: {
    launch_ready: true,
    total_tasks: 1,
    counts: { Estimated: 1, Running: 0, Review: 0, Done: 0 },
  },
  automation: { queue: { status: "idle", auto_agent_review: false }, live_refresh_enabled: false },
};

const floorTask = {
  ...pipelineTask,
  id: "floor-running-999",
  status: "Running",
  session_href: "/sessions/floor-running-999",
  timeline: [{ id: 1, created_at: "2099-01-01T00:00:00Z", kind: "token", title: "Provisional usage", detail_summary: { text: "total_tokens=12", truncated: false } }],
  controls: { ...pipelineTask.controls, can_launch: false, can_refresh: true },
};
const floorData = {
  ...pipelineData,
  tasks_by_status: {
    Estimated: [],
    Running: [floorTask],
    Review: [{ ...floorTask, id: "floor-review-999", status: "Review", controls: { ...floorTask.controls, can_refresh: false } }],
    Done: [{ ...floorTask, id: "floor-done-999", status: "Done", actual_tokens: 89, controls: { ...floorTask.controls, can_refresh: false, can_archive: true } }],
  },
};

const dashboardData = {
  next_actions: [
    { label: "Review 1 task", detail: "Awaiting operator review", href: "/board", tone: "purple" },
    { label: "Open task board", detail: "Inspect project work", href: "/board", tone: "green" },
  ],
  budget: { total_tokens: 240, daily_cap: 1000, current_zone: "green", since: "2099-01-01T00:00:00Z" },
  worker_execution: {
    token_total: 150,
    status_split: { completed: 120, failed_retry: 30, unknown: 0 },
    components: { available: true, items: [{ label: "output", value: 30 }], cost: null },
  },
  spend: {
    worker_execution: 150,
    orchestration: 90,
    agent_review_reporting: 30,
    planning_estimation: 40,
    setup_verification: 20,
    other: 0,
    pricing_coverage: {
      worker_execution: { state: "unpriced", cost: null, priced_tokens: 0, unpriced_tokens: 150, coverage_percent: 0 },
      agent_review_reporting: { state: "unpriced", cost: null, priced_tokens: 0, unpriced_tokens: 30, coverage_percent: 0 },
      planning_estimation: { state: "unpriced", cost: null, priced_tokens: 0, unpriced_tokens: 40, coverage_percent: 0 },
      setup_verification: { state: "unpriced", cost: null, priced_tokens: 0, unpriced_tokens: 20, coverage_percent: 0 },
      other: { state: "no_usage", cost: 0, priced_tokens: 0, unpriced_tokens: 0, coverage_percent: 0 },
      orchestration: { state: "unpriced", cost: null, priced_tokens: 0, unpriced_tokens: 90, coverage_percent: 0 },
      total: { state: "unpriced", cost: null, priced_tokens: 0, unpriced_tokens: 240, coverage_percent: 0 },
    },
    cost_by_category: {
      control_plane: null,
      task_breakdown: null,
      worker_execution: null,
      adapter_verification: null,
      reporting_summary: null,
      other: 0,
    },
    total_cost: null,
    priced_tokens: 0,
    unpriced_tokens: 240,
  },
  needs_you: { count: 2, project_count: 1, projects_with_needs_you: 1 },
  estimation_coefficients: {
    available: true,
    scope: "default",
    factors: [
      { key: "g", label: "Context growth per turn", value: 115, provenance: "seed" },
      { key: "p", label: "Output per turn", value: 800, provenance: "fitted(3)" },
    ],
  },
  alarms: {
    total: 1,
    open: 1,
    critical: 0,
    recent: [{ id: "browser-alarm-999", type: "BUDGET_YELLOW", severity: "LOW", session_id: "browser-session-999", recommended_action: "Review spend." }],
  },
  active_sessions: [{ id: "browser-session-999", task_description: "Browser Dashboard task", model: "gpt-browser-999", status: "running" }],
  estimation_accuracy: { completed_count: 3, median_error_ratio: 1.1, within_2x_pct: 100 },
  projects: [{ id: "browser-project-999", name: "Browser project 999", task_count: 1, needs_you_count: 2, capability: { state: "launch_ready" } }],
};

const alarmContractData = {
  filters: [
    { label: "Open", value: "open", count: 1 },
    { label: "Resolved", value: "resolved", count: 1 },
    { label: "All", value: "all", count: 2 },
  ],
  alarms: [{
    id: "alarm-browser-999",
    type: "DAILY_CAP_EXCEEDED",
    severity: "HIGH",
    session_id: "session-alarm-999",
    session_href: "/sessions/session-alarm-999",
    context: { text: "Bounded browser alarm evidence", truncated: true },
    recommended_action: "Continue or raise the daily cap.",
    available_actions: [{
      action: "raise_budget",
      cap_key: "daily_cap_tokens",
      current_cap: 1000,
    }],
    resolved_at: null,
  }],
};

function taskHistoryContractData(filter = "all", tasks = null) {
  return {
    filters: [
      { label: "All", value: "all", count: 1, active: filter === "all" },
      { label: "Archived", value: "archived", count: 1, active: filter === "archived" },
    ],
    tasks: tasks ?? [{
      id: "task-history-browser-999",
      description: "Preserve browser history evidence",
      status: "Done",
      task_kind: "acceptance_verification",
      archived: true,
      archived_at: "2099-01-01T00:00:00Z",
      estimate_tokens: 1000,
      actual_tokens: 1200,
      session_href: "/sessions/session-history-999",
      worker_run_id: "run-history-browser-999",
    }],
  };
}

function deferredResponse() {
  let resolve;
  const promise = new Promise((next) => { resolve = next; });
  return { promise, resolve };
}

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function requireStatusLabels(surface, message) {
  const pills = [...surface.querySelectorAll(".status-pill")];
  requireContract(pills.length > 0, `${message} has no statuses`);
  requireContract(pills.every((pill) => (
    pill.querySelector(".status-pill-glyph")?.textContent.trim()
      && pill.querySelector(".status-pill-label")?.textContent.trim()
  )), `${message} loses a glyph or visible label`);
}

function PipelineContract() {
  const [selectedTask, setSelectedTask] = React.useState(null);
  return <>
    <section id="pipeline-interaction-contract">
      <BoardState
        projectId="browser-project-999"
        surface="pipeline"
        data={pipelineData}
        error={null}
        loading={false}
        action={() => {}}
        openEvidence={setSelectedTask}
      />
    </section>
    {selectedTask && <EvidenceDrawerState
      task={selectedTask}
      projectId="browser-project-999"
      data={drawerReport}
      error={null}
      loading={false}
      onClose={() => setSelectedTask(null)}
    />}
  </>;
}

function FloorContract() {
  return <section id="floor-interaction-contract">
    <BoardState
      projectId="browser-project-999"
      surface="floor"
      data={floorData}
      error={null}
      loading={false}
      action={() => {}}
    />
  </section>;
}

function ContractSurface() {
  const [confirming, setConfirming] = React.useState(false);
  return (
    <main>
      <div className="shell" id="rail-contract-shell">
        <aside className="sidebar">
          <div className="project-switcher">
            <label className="project-switcher-label" htmlFor="rail-contract-select">Project</label>
            <select id="rail-contract-select" aria-label="Switch project" defaultValue="demo"><option value="demo">DEMO 999</option></select>
          </div>
          <section className="rail-group" aria-label="Project">
            <h2 className="rail-group-title">Project</h2>
            <nav>
              <a id="rail-contract-link" data-rail-link="true" aria-label="Needs You, 3 Needs You" href="/projects/demo-999/needs-you">
                <span className="nav-glyph" aria-hidden="true">N</span><span className="rail-label">Needs You</span>
                <span className="nav-badge nav-badge-needs-you" aria-label="3 Needs You"><span aria-hidden="true">3</span></span>
              </a>
            </nav>
          </section>
        </aside>
        <div className="shell-workbench">
          <div className="context-bar" aria-label="Page context">Project / Needs You</div>
          <div className="main">
            <div className="task-breakdown-workbench" id="review-grid-contract">
              <header className="review-workbench-header">Review header</header>
              <div className="review-workbench-zones">
                {['Candidate navigator', 'Focused candidate editor', 'Task Breakdown context'].map((label) => (
                  <section key={label} className="review-zone" aria-label={label}>
                    <div style={{ height: 1200 }}>{label} scroll evidence</div>
                  </section>
                ))}
              </div>
              <div className="sticky-action-bar">Review actions</div>
            </div>
          </div>
        </div>
      </div>
      <button id="confirm-opener" type="button" onClick={() => setConfirming(true)}>Open confirmation</button>
      <ConfirmSheet
        ref={confirmSheetRef}
        open={confirming}
        onClose={() => setConfirming(false)}
        title="Confirm contract"
        description="Exercise modal focus ownership."
        actions={(
          <>
            <button id="confirm-first" type="button" onClick={() => setConfirming(false)}>Cancel</button>
            <button id="confirm-last" type="button">Confirm</button>
          </>
        )}
      >
        <p>Confirmation body</p>
      </ConfirmSheet>
      <Panel>
        <PanelHeader title="Ledger contract" badge={<span id="content-contract-badge" className="nav-badge">3</span>} />
        <PanelBody>
          <div id="select-track" style={{ display: "grid", gridTemplateColumns: "minmax(0, 180px)" }}>
            <label>Worker adapter<select id="contract-select" defaultValue="long"><option value="long">A deliberately long adapter option that must stay contained</option></select></label>
          </div>
          <div>
            <span className="live-pulse-dot" aria-label="Running live" />
            <StatusPill tone="running" label="running" />
          </div>
          <div className="board-intake-progress-track" role="progressbar" aria-label="Estimating task" aria-valuetext="Estimating task">
            <span className="board-intake-progress-bar" />
          </div>
          <Skeleton label="Loading evidence" />
        </PanelBody>
      </Panel>
      <Panel><PanelHeader title="Sibling panel" /></Panel>
      <section id="view-behavior-contract-root" />
      <button id="pipeline-outside-target" type="button">Outside target</button>
      <PipelineContract />
      <FloorContract />
      <section id="dashboard-interaction-contract">
        <DashboardContent data={dashboardData} />
      </section>
    </main>
  );
}

function requireContract(condition, message) {
  if (!condition) throw new Error(message);
}

async function waitForContract(condition, message) {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    if (condition()) return;
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  throw new Error(message);
}

async function inspect() {
  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));

  const behaviorRoot = createRoot(document.querySelector("#view-behavior-contract-root"));
  const originalFetch = window.fetch;
  const requests = [];
  const navigations = [];
  let alarmsMode = "populated";
  let alarmsPending = null;
  let alarmActionPending = null;
  let taskHistoryMode = "populated";
  let taskHistoryPending = null;
  window.fetch = async (input, options = {}) => {
    const url = typeof input === "string" ? input : input.url;
    const method = options.method || "GET";
    requests.push({ url, method, options, body: options.body ? JSON.parse(options.body) : null });
    if (url.startsWith("/api/alarms?")) {
      if (alarmsPending) return alarmsPending.promise;
      if (alarmsMode === "error") return jsonResponse({ detail: "synthetic alarm failure" }, 500);
      if (alarmsMode === "empty") return jsonResponse({ ...alarmContractData, alarms: [] });
      return jsonResponse(alarmContractData);
    }
    if (url === "/alarms/alarm-browser-999/resolve") {
      if (alarmActionPending) return alarmActionPending.promise;
      return jsonResponse({ ok: true });
    }
    if (url.startsWith("/api/projects/browser-project-999/task-history?")) {
      if (taskHistoryPending) return taskHistoryPending.promise;
      if (taskHistoryMode === "error") return jsonResponse({ detail: "synthetic history failure" }, 500);
      const filter = new URL(url, window.location.origin).searchParams.get("filter") || "all";
      return jsonResponse(taskHistoryContractData(filter, taskHistoryMode === "empty" ? [] : null));
    }
    if (url === "/projects/browser-project-999/tasks/task-history-browser-999/unarchive") {
      return jsonResponse({ ok: true, task_id: "task-history-browser-999" });
    }
    throw new Error(`Unexpected browser-contract request: ${method} ${url}`);
  };

  const renderBehavior = (element) => behaviorRoot.render(
    <NavContext.Provider value={(to) => navigations.push(to)}>{element}</NavContext.Provider>,
  );
  const behaviorSurface = () => document.querySelector("#view-behavior-contract-root");

  window.history.replaceState(null, "", "/alarms");
  alarmsPending = deferredResponse();
  renderBehavior(<Alarms key="alarms-loading" />);
  await waitForContract(
    () => behaviorSurface().textContent.includes("Loading Alarms"),
    "Alarms does not expose its loading state in the browser",
  );
  alarmsPending.resolve(jsonResponse(alarmContractData));
  alarmsPending = null;
  await waitForContract(
    () => behaviorSurface().querySelector('[role="table"][aria-label="Alarms"]'),
    "Alarms does not render its shared Ledger table",
  );
  let alarmsSurface = behaviorSurface();
  requireStatusLabels(alarmsSurface, "Alarms");
  requireContract(alarmsSurface.textContent.includes("Bounded browser alarm evidence"), "Alarms loses bounded context");
  requireContract(alarmsSurface.textContent.includes("(truncated)"), "Alarms loses bounded-context truncation evidence");
  requireContract(alarmsSurface.querySelector('a[href="/sessions/session-alarm-999"]'), "Alarms loses session evidence navigation");
  requireContract(!alarmsSurface.textContent.includes("Abort"), "Alarms exposes an unavailable Abort action");

  const alarmFilter = [...alarmsSurface.querySelectorAll('nav[aria-label="Alarm filters"] button')]
    .find((button) => button.textContent.includes("Resolved"));
  alarmFilter.focus();
  requireContract(alarmFilter.matches(":focus-visible"), "Alarm filter is not keyboard focus-visible");
  alarmFilter.click();
  await waitForContract(
    () => window.location.search === "?filter=resolved"
      && requests.some((request) => request.url === "/api/alarms?filter=resolved"),
    "Alarm filtering does not update the bookmarkable URL and request",
  );

  const raiseButton = [...alarmsSurface.querySelectorAll("button")]
    .find((button) => button.textContent.trim() === "Raise Budget");
  raiseButton.focus();
  raiseButton.click();
  await waitForContract(
    () => alarmsSurface.querySelector(".confirm-sheet")?.contains(document.activeElement),
    "Budget confirmation does not receive initial focus",
  );
  let confirmRaise = [...alarmsSurface.querySelectorAll("button")]
    .find((button) => button.textContent.trim() === "Confirm raise");
  requireContract(confirmRaise.disabled, "Budget confirmation is enabled without a positive cap");
  requireContract(
    alarmsSurface.textContent.includes("Enter a positive new budget cap before confirming."),
    "Budget confirmation omits its disabled reason",
  );
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
  await waitForContract(
    () => !alarmsSurface.querySelector(".confirm-sheet") && document.activeElement === raiseButton,
    "Escape does not dismiss budget confirmation and restore its opener",
  );

  raiseButton.click();
  await waitForContract(() => alarmsSurface.querySelector(".confirm-sheet input"), "Budget confirmation does not reopen");
  const capInput = alarmsSurface.querySelector(".confirm-sheet input");
  capInput.focus();
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(capInput, "1500");
  capInput.dispatchEvent(new Event("input", { bubbles: true }));
  await waitForContract(() => {
    confirmRaise = [...alarmsSurface.querySelectorAll("button")]
      .find((button) => button.textContent.trim() === "Confirm raise");
    return confirmRaise && !confirmRaise.disabled;
  }, "Budget confirmation does not accept keyboard-entered input");
  confirmRaise.focus();
  confirmRaise.click();
  await waitForContract(
    () => requests.some((request) => (
      request.url === "/alarms/alarm-browser-999/resolve"
        && request.method === "POST"
        && request.body?.action === "raise_budget"
        && request.body?.payload?.daily_cap_tokens === 1500
    )) && !alarmsSurface.querySelector(".confirm-sheet")
      && alarmsSurface.textContent.includes("raise_budget resolved for alarm alarm-browser-999"),
    "Budget confirmation does not submit the alarm resolve request",
  );

  alarmActionPending = deferredResponse();
  const continueButton = [...alarmsSurface.querySelectorAll("button")]
    .find((button) => button.textContent.trim() === "Continue");
  continueButton.focus();
  continueButton.click();
  await waitForContract(
    () => {
      const actionButtons = [...alarmsSurface.querySelectorAll("button")]
        .filter((button) => ["Continue", "Raise Budget"].includes(button.textContent.trim()));
      return actionButtons.length === 2
        && actionButtons.every((button) => button.disabled && button.getAttribute("aria-describedby"));
    },
    "Pending alarm actions do not expose disabled reasons",
  );
  alarmActionPending.resolve(jsonResponse({ ok: true }));
  alarmActionPending = null;
  await waitForContract(
    () => requests.some((request) => (
      request.url === "/alarms/alarm-browser-999/resolve"
        && request.body?.action === "continue"
    )) && alarmsSurface.textContent.includes("continue resolved for alarm alarm-browser-999"),
    "Continue does not submit the alarm resolve request",
  );

  alarmsMode = "error";
  window.history.replaceState(null, "", "/alarms");
  renderBehavior(<Alarms key="alarms-error" />);
  await waitForContract(
    () => behaviorSurface().querySelector('[role="alert"]')?.textContent.includes("Could not load Alarms"),
    "Alarms does not expose its error state in the browser",
  );
  alarmsMode = "empty";
  renderBehavior(<Alarms key="alarms-empty" />);
  await waitForContract(
    () => behaviorSurface().textContent.includes("No open alarms"),
    "Alarms does not expose its empty state in the browser",
  );

  taskHistoryMode = "populated";
  taskHistoryPending = deferredResponse();
  window.history.replaceState(null, "", "/projects/browser-project-999/task-history");
  renderBehavior(<TaskHistory key="history-loading" projectId="browser-project-999" />);
  await waitForContract(
    () => behaviorSurface().textContent.includes("Loading task history"),
    "Task History does not expose its loading state in the browser",
  );
  taskHistoryPending.resolve(jsonResponse(taskHistoryContractData()));
  taskHistoryPending = null;
  await waitForContract(
    () => behaviorSurface().querySelector('[role="table"][aria-label="Task history"]'),
    "Task History does not render its shared data table",
  );
  let historySurface = behaviorSurface();
  requireContract(
    historySurface.querySelector('[role="note"][aria-label="Task history is read-only"]'),
    "Task History does not expose its read-only state",
  );
  requireStatusLabels(historySurface, "Task History");
  requireContract(historySurface.textContent.includes("Archived"), "Task History loses archive evidence");
  requireContract(historySurface.textContent.includes("acceptance_verification"), "Task History loses task-kind evidence");
  requireContract(historySurface.textContent.includes("run-history-browser-999"), "Task History loses Worker Run evidence");
  const historySession = historySurface.querySelector('a[href="/sessions/session-history-999"]');
  historySession.focus();
  requireContract(historySession.matches(":focus-visible"), "Task History evidence link is not keyboard focus-visible");

  const archivedFilter = [...historySurface.querySelectorAll('section[aria-label="Archive filters"] button')]
    .find((button) => button.textContent.includes("Archived"));
  archivedFilter.focus();
  archivedFilter.click();
  await waitForContract(
    () => window.location.search === "?filter=archived"
      && requests.some((request) => request.url === "/api/projects/browser-project-999/task-history?filter=archived"),
    "Task History filtering does not update the URL and request",
  );

  const pipelineLink = historySurface.querySelector('a[href="/projects/browser-project-999"]');
  pipelineLink.focus();
  pipelineLink.click();
  requireContract(
    navigations.at(-1) === "/projects/browser-project-999",
    "Task History does not navigate back to Pipeline through the public link",
  );

  const unarchiveButton = [...historySurface.querySelectorAll("button")]
    .find((button) => button.textContent.trim() === "Unarchive");
  unarchiveButton.focus();
  unarchiveButton.click();
  await waitForContract(
    () => requests.some((request) => (
      request.url === "/projects/browser-project-999/tasks/task-history-browser-999/unarchive"
        && request.method === "POST"
        && request.options.headers?.Accept === "application/json"
        && request.options.credentials === "same-origin"
    ))
      && historySurface.textContent.includes("Task task-history-browser-999 unarchived.")
      && requests.filter((request) => (
        request.url === "/api/projects/browser-project-999/task-history?filter=archived"
      )).length >= 2,
    "Task History does not cross the unarchive HTTP boundary and report success",
  );

  taskHistoryMode = "error";
  window.history.replaceState(null, "", "/projects/browser-project-999/task-history");
  renderBehavior(<TaskHistory key="history-error" projectId="browser-project-999" />);
  await waitForContract(
    () => behaviorSurface().querySelector('[role="alert"]')?.textContent.includes("Could not load task history"),
    "Task History does not expose its error state in the browser",
  );
  taskHistoryMode = "empty";
  renderBehavior(<TaskHistory key="history-empty" projectId="browser-project-999" />);
  await waitForContract(
    () => behaviorSurface().textContent.includes("No tasks match this history filter"),
    "Task History does not expose its empty state in the browser",
  );

  behaviorRoot.unmount();
  window.fetch = originalFetch;
  const opener = document.querySelector("#confirm-opener");
  opener.focus();
  opener.click();
  await waitForContract(
    () => document.querySelector(".confirm-sheet") && document.activeElement === document.querySelector("#confirm-first"),
    "confirmation does not receive initial focus",
  );
  const dialog = document.querySelector(".confirm-sheet");
  const first = document.querySelector("#confirm-first");
  const last = document.querySelector("#confirm-last");
  requireContract(confirmSheetRef.current === dialog, "confirmation ref is not forwarded");
  last.focus();
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true }));
  requireContract(document.activeElement === first, "confirmation does not wrap forward focus");
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", shiftKey: true, bubbles: true, cancelable: true }));
  requireContract(document.activeElement === last, "confirmation does not wrap backward focus");
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
  await waitForContract(
    () => !document.querySelector(".confirm-sheet") && document.activeElement === opener,
    "Escape does not close confirmation and restore opener focus",
  );

  const pipeline = document.querySelector("#pipeline-interaction-contract");
  const pipelineButton = (label) => [...pipeline.querySelectorAll("button")]
    .find((button) => button.textContent.trim() === label);
  const launchTrigger = pipelineButton("Launch options");
  requireContract(launchTrigger, "Pipeline launch trigger is missing");
  launchTrigger.scrollIntoView({ block: "center" });
  await new Promise((resolve) => setTimeout(resolve, 0));
  launchTrigger.focus();
  launchTrigger.click();
  await waitForContract(() => {
    const panel = pipeline.querySelector(".launch-popover-panel");
    return panel?.matches(":popover-open") && document.activeElement === panel.querySelector("select");
  }, "Pipeline launch popover does not open with focus");
  const launchDialog = pipeline.querySelector(".launch-popover-panel");
  const launchRect = launchDialog.getBoundingClientRect();
  requireContract(
    launchRect.top >= 0 && launchRect.bottom <= innerHeight && launchRect.left >= 0 && launchRect.right <= innerWidth,
    "Pipeline launch popover escapes the viewport",
  );
  const launchControls = [...launchDialog.querySelectorAll(
    "button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href]",
  )];
  const launchFirst = launchControls[0];
  const launchLast = launchControls.at(-1);
  launchLast.focus();
  launchLast.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true }));
  requireContract(document.activeElement === launchFirst, "Pipeline launch popover does not wrap forward focus");
  launchFirst.focus();
  launchFirst.dispatchEvent(new KeyboardEvent("keydown", {
    key: "Tab", shiftKey: true, bubbles: true, cancelable: true,
  }));
  requireContract(document.activeElement === launchLast, "Pipeline launch popover does not wrap backward focus");
  launchDialog.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
  await waitForContract(
    () => !launchDialog.matches(":popover-open") && document.activeElement === launchTrigger,
    "Escape does not close Pipeline launch popover and restore trigger focus",
  );

  launchTrigger.click();
  await waitForContract(
    () => launchDialog.matches(":popover-open"),
    "Pipeline launch popover does not reopen",
  );
  document.querySelector("#pipeline-outside-target").dispatchEvent(new PointerEvent("pointerdown", {
    bubbles: true, cancelable: true, button: 0, pointerId: 1, isPrimary: true,
  }));
  await waitForContract(
    () => !launchDialog.matches(":popover-open") && launchTrigger.getAttribute("aria-expanded") === "false",
    "Pipeline launch popover does not light-dismiss",
  );

  const evidenceTrigger = pipelineButton("View evidence");
  requireContract(evidenceTrigger, "Pipeline evidence trigger is missing");
  evidenceTrigger.focus();
  evidenceTrigger.click();
  await waitForContract(() => {
    const drawer = document.querySelector(".evidence-drawer");
    return drawer && document.activeElement === drawer;
  }, "Pipeline evidence drawer does not receive focus");
  const evidenceDrawer = document.querySelector(".evidence-drawer");
  requireContract(evidenceDrawer.querySelector(".token-comparison"), "Evidence Drawer does not lead with shared estimate-versus-actual evidence");
  requireContract(
    evidenceDrawer.querySelector(".token-comparison-provenance")?.textContent.includes("browser-adapter · native_usage"),
    "Evidence Drawer omits adjacent spend-tracking provenance",
  );
  const evidenceDisclosures = [...evidenceDrawer.querySelectorAll(".evidence-disclosure")];
  const evidenceLabels = evidenceDisclosures.map((disclosure) => disclosure.querySelector(".disclosure-label")?.textContent);
  requireContract(
    JSON.stringify(evidenceLabels) === JSON.stringify([
      "Live Worker Run feed",
      "Worker Run timeline",
      "Token log",
      "Budget-zone timeline",
      "Repo Context Brief",
      "Alarms",
      "Checkpoint results",
    ]),
    `Evidence Drawer hierarchy is incorrect: ${evidenceLabels.join(", ")}`,
  );
  requireContract(evidenceDisclosures[0].open, "Evidence Drawer live feed is initially collapsed");
  requireContract(evidenceDisclosures[1].open, "Evidence Drawer Worker Run timeline is initially collapsed");
  requireContract(
    evidenceDisclosures.slice(2).every((disclosure) => !disclosure.open),
    "Evidence Drawer raw evidence disclosures are not initially collapsed",
  );
  const evidenceControls = [...evidenceDrawer.querySelectorAll(
    'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )];
  const evidenceFirst = evidenceControls[0];
  const evidenceLast = evidenceControls.at(-1);
  evidenceLast.focus();
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true }));
  requireContract(document.activeElement === evidenceFirst, "Pipeline evidence drawer does not wrap forward focus");
  evidenceFirst.focus();
  document.dispatchEvent(new KeyboardEvent("keydown", {
    key: "Tab", shiftKey: true, bubbles: true, cancelable: true,
  }));
  requireContract(document.activeElement === evidenceLast, "Pipeline evidence drawer does not wrap backward focus");
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
  await waitForContract(
    () => !document.querySelector(".evidence-drawer") && document.activeElement === evidenceTrigger,
    "Escape does not close Pipeline evidence drawer and restore trigger focus",
  );
  window.scrollTo(0, 0);
  await new Promise((resolve) => setTimeout(resolve, 0));

  const floor = document.querySelector("#floor-interaction-contract");
  for (const title of ["Active Worker Runs", "Review queue", "Recently finished"]) {
    requireContract([...floor.querySelectorAll("h3")].some((heading) => heading.textContent === title), `Execution Floor omits ${title}`);
  }
  const activeGrid = floor.querySelector(".floor-active-grid");
  const activePanel = activeGrid.querySelector(".floor-active-run");
  requireContract(activePanel?.querySelector(".live-run-dock"), "live-run dock is not folded into the active Worker Run panel");
  requireContract(!floor.querySelector(".floor-main > .live-run-dock"), "live-run dock remains detached from the active Worker Run panel");
  const sessionReportLinks = [...activePanel.querySelectorAll('a[href="/sessions/floor-running-999"]')];
  requireContract(
    sessionReportLinks.length === 1 && sessionReportLinks[0].textContent.trim() === "Session Report",
    "embedded live-run dock does not preserve its direct Session Report permalink",
  );
  requireContract(
    activePanel.querySelectorAll(".task-heading .task-id").length === 1
      && !activePanel.querySelector(".live-run-dock-task .task-id, .live-run-dock-title"),
    "embedded live-run dock duplicates the active task identity",
  );
  requireContract(
    [...activePanel.querySelectorAll("button")].some((button) => button.textContent.trim() === "View evidence"),
    "active Worker Run loses its Evidence Drawer entry point",
  );
  requireContract(activePanel.querySelector(".event-row"), "active Worker Run does not preserve shared live-event treatment");
  requireContract(getComputedStyle(activeGrid).gridTemplateColumns.split(" ").length === 1, "active Worker Runs are not full-width panels");
  requireContract(
    Math.abs(activePanel.getBoundingClientRect().width - activeGrid.getBoundingClientRect().width) < 1,
    "active Worker Run panel does not fill its Execution Floor section",
  );

  const dashboard = document.querySelector("#dashboard-interaction-contract");
  const dashboardOverview = dashboard.querySelector(".dashboard-overview");
  const dashboardLabels = [...dashboardOverview.querySelectorAll(".kpi > .label")]
    .map((label) => label.textContent.trim());
  requireContract(
    JSON.stringify(dashboardLabels) === JSON.stringify(["Daily governed budget", "Worker execution", "Orchestration", "Needs You"]),
    `Dashboard KPI order is incorrect: ${dashboardLabels.join(", ")}`,
  );
  requireContract(
    getComputedStyle(dashboardOverview).gridTemplateColumns.split(" ").length === 2,
    "Dashboard KPI overview does not collapse to two columns at 1100px",
  );
  const dashboardPanelTitleStyle = getComputedStyle(dashboard.querySelector(".panel-header h3"));
  requireContract(
    dashboardPanelTitleStyle.textTransform === "none" && dashboardPanelTitleStyle.fontFamily.includes("-apple-system"),
    "Dashboard panel titles do not use the accepted sentence-case sans tier",
  );
  requireContract(
    dashboard.querySelector(".dashboard-kpi-orchestration .value")?.textContent.trim() === "90",
    "Dashboard does not expose the authoritative orchestration total",
  );
  requireContract(
    dashboard.querySelector(".dashboard-kpi-orchestration")?.textContent.includes("90 unpriced tokens"),
    "Dashboard loses orchestration pricing coverage",
  );
  const planningSpendRow = [...dashboard.querySelectorAll('[role="table"][aria-label="Governed spend by category"] [role="row"]')]
    .find((row) => row.textContent.includes("Planning/estimation"));
  requireContract(planningSpendRow?.textContent.includes("40"), "Dashboard does not attribute Planning spend to orchestration");
  requireContract(!dashboard.textContent.includes("Other tracked spend"), "Dashboard still presents Planning spend as Other tracked spend");
  requireContract(
    dashboardOverview.querySelectorAll(".kpi")[1]?.querySelector(".value")?.textContent.trim() === "150",
    "Dashboard Worker execution KPI changed its authoritative total",
  );
  requireContract(
    dashboard.querySelector(".dashboard-kpi-needs-you .value")?.textContent.trim() === "2",
    "Dashboard does not expose the authoritative project-scoped Needs You count",
  );
  requireContract(
    dashboard.textContent.includes("Context growth per turn")
      && dashboard.textContent.includes("seed")
      && dashboard.textContent.includes("fitted(3)"),
    "Dashboard loses canonical estimation coefficient provenance",
  );
  requireContract(dashboard.textContent.includes("unpriced"), "Dashboard loses the unpriced provenance qualifier");
  requireContract(dashboard.querySelector('[role="table"][aria-label="Active sessions"]'), "Dashboard sessions do not use the shared data table");
  requireContract(dashboard.querySelector('[role="table"][aria-label="Recent open alarms"]'), "Dashboard alarms do not use shared Ledger rows");
  const dashboardSessionLink = dashboard.querySelector('a[href="/sessions/browser-session-999"]');
  requireContract(dashboardSessionLink, "Dashboard active-session navigation is missing");
  const dashboardAction = dashboard.querySelector(".dashboard-action-link");
  dashboardAction.focus();
  requireContract(dashboardAction.matches(":focus-visible"), "Dashboard action is not keyboard focus-visible");
  requireContract(
    getComputedStyle(dashboardAction).outlineColor === "rgb(92, 242, 196)",
    "Dashboard action focus outline is not mint",
  );
  requireContract(!dashboard.querySelector(".panel .panel"), "Dashboard renders nested panels");
  window.scrollTo(0, 0);
  await new Promise((resolve) => setTimeout(resolve, 0));

  const select = document.querySelector("#contract-select");
  const track = document.querySelector("#select-track");
  select.focus();
  const selectStyle = getComputedStyle(select);
  const selectBox = select.getBoundingClientRect();
  const trackBox = track.getBoundingClientRect();
  requireContract(select.matches(":focus-visible"), "select is not focus-visible");
  requireContract(selectStyle.outlineColor === "rgb(92, 242, 196)", "focus outline is not mint");
  requireContract(selectStyle.outlineStyle === "solid" && selectStyle.outlineWidth === "2px", "focus outline is not visible");
  requireContract(selectStyle.minWidth === "0px" && selectStyle.maxWidth === "100%", "select sizing contract is missing");
  requireContract(selectBox.left >= trackBox.left - 0.5 && selectBox.right <= trackBox.right + 0.5, "select escapes its layout track");

  const railShell = document.querySelector("#rail-contract-shell");
  const railLink = document.querySelector("#rail-contract-link");
  const railLabel = railLink.querySelector(".rail-label");
  requireContract(matchMedia("(max-width: 1200px)").matches, "narrow desktop rail contract is not active");
  requireContract(getComputedStyle(railShell).gridTemplateColumns.startsWith("72px"), "narrow desktop rail does not collapse");
  requireContract(getComputedStyle(railLabel).position === "absolute", "collapsed rail still renders full-width labels");
  railLink.focus();
  requireContract(railLink.matches(":focus-visible"), "collapsed rail link is not keyboard focusable");
  requireContract(railLink.getAttribute("aria-label") === "Needs You, 3 Needs You", "collapsed rail link loses its badge state");
  requireContract(getComputedStyle(railLabel).clip === "auto", "focused collapsed rail label stays clipped");
  requireContract(railLabel.getBoundingClientRect().width > 1, "focused collapsed rail label is not visible");
  const contentBadge = document.querySelector("#content-contract-badge");
  const contentBadgeHeader = contentBadge.closest(".panel-header");
  const contentBadgeBox = contentBadge.getBoundingClientRect();
  const contentBadgeHeaderBox = contentBadgeHeader.getBoundingClientRect();
  requireContract(getComputedStyle(contentBadge).position !== "absolute", "content badge inherits rail-only positioning");
  requireContract(
    contentBadgeBox.left >= contentBadgeHeaderBox.left && contentBadgeBox.right <= contentBadgeHeaderBox.right,
    "content badge escapes its panel header",
  );

  const reviewGrid = document.querySelector("#review-grid-contract");
  const reviewZones = reviewGrid.querySelector(".review-workbench-zones");
  const reviewActions = reviewGrid.querySelector(".sticky-action-bar");
  requireContract(getComputedStyle(reviewZones).gridRowStart === "3", "review zones leave the scrolling grid row when no notice renders");
  requireContract(getComputedStyle(reviewActions).gridRowStart === "4", "review actions leave the permanent action row when no notice renders");
  requireContract(reviewGrid.clientHeight === document.querySelector(".main").clientHeight, "review workbench exceeds its shell row");
  requireContract(Math.abs(reviewActions.getBoundingClientRect().bottom - innerHeight) < 1, "review actions fall below the viewport");
  for (const zone of reviewGrid.querySelectorAll(".review-zone")) {
    requireContract(getComputedStyle(zone).overflowY === "auto", "review zone does not own vertical scrolling");
    requireContract(zone.scrollHeight > zone.clientHeight, "review zone expands instead of scrolling independently");
  }

  const live = document.querySelector(".live-pulse-dot");
  const liveStyle = getComputedStyle(live);
  requireContract(matchMedia("(prefers-reduced-motion: reduce)").matches, "reduced motion is not active");
  requireContract(liveStyle.animationName === "none" && liveStyle.opacity === "1", "live status loses reduced-motion meaning");
  requireContract(document.querySelector(".status-pill-glyph")?.textContent.trim(), "status glyph is missing");
  requireContract(document.querySelector(".status-pill-label")?.textContent.trim() === "running", "status label is missing");

  const progressStyle = getComputedStyle(document.querySelector(".board-intake-progress-bar"));
  requireContract(progressStyle.animationName === "none" && progressStyle.transform === "none", "progress fallback still moves");
  const skeletonStyle = getComputedStyle(document.querySelector(".skeleton-bar"));
  requireContract(skeletonStyle.animationName === "none" && skeletonStyle.transform === "none", "skeleton is not static");
  requireContract(document.querySelectorAll(".panel .panel").length === 0, "panels are nested");
  document.documentElement.dataset.ledgerContract = "passed";
}

createRoot(document.querySelector("#root")).render(<ContractSurface />);
inspect().catch((error) => {
  document.documentElement.dataset.ledgerContract = "failed";
  document.documentElement.dataset.contractError = error.message;
  document.body.dataset.contractError = error.message;
});
