import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { accessSync, constants, existsSync, mkdtempSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { homedir, tmpdir } from "node:os";
import { basename, join } from "node:path";
import { promisify } from "node:util";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { act, create } from "react-test-renderer";
import { createServer } from "vite";

const frontendRoot = fileURLToPath(new URL("../", import.meta.url));
const execFileAsync = promisify(execFile);
let server;
let browserBaseUrl;
let Shell;
let Sidebar;
let App;
let DashboardState;
let BoardState;
let EvidenceDrawerState;
let loadEvidenceDrawer;
let loadBoardRunProvenance;
let launchPopoverPlacement;
let boardNoticeFromSearch;
let mergeBoardStatus;
let taskDisplayName;
let investigationMessage;
let parseRoute;
let ProjectsState;
let pollBoardStatus;
let submitBoardAction;
let WorkspaceState;
let submitProjectRestore;
let SessionsState;
let AlarmsState;
let SessionReportState;
let SetupState;
let TaskBreakdownReviewState;
let TaskBreakdownReview;
let projectIdFromBoardHref;
let submitBreakdownAction;
let TaskHistoryState;
let buildAcceptForm;
let confirmReviewNavigation;
let preventReviewUnload;
let NavContext;
let NavigationGuardContext;
let OwnedLink;
let isReactOwnedPath;
let BudgetSettingsState;
let WorkerSettingsState;
let ControlPlaneSettingsState;
let ProjectSettingsState;

const browserNames = new Set(["chrome", "chrome-headless-shell", "headless_shell", "Chromium"]);

function executable(path) {
  if (!path || !existsSync(path)) return false;
  try {
    accessSync(path, constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

function browserUnder(root, depth = 0) {
  if (!root || !existsSync(root) || depth > 4) return null;
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const path = join(root, entry.name);
    if (entry.isDirectory()) {
      const nested = browserUnder(path, depth + 1);
      if (nested) return nested;
    } else if (browserNames.has(basename(path)) && executable(path)) {
      return path;
    }
  }
  return null;
}

function browserExecutable() {
  const direct = [
    process.env.CHROME_BIN,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
  ];
  for (const directory of String(process.env.PATH || "").split(":")) {
    for (const name of ["google-chrome", "chromium", "chromium-browser"]) direct.push(join(directory, name));
  }
  for (const root of [join(homedir(), ".cache", "ms-playwright"), join(homedir(), "Library", "Caches", "ms-playwright")]) {
    if (!existsSync(root)) continue;
    const shells = readdirSync(root, { withFileTypes: true })
      .filter((entry) => entry.isDirectory() && entry.name.startsWith("chromium_headless_shell-"))
      .sort((left, right) => right.name.localeCompare(left.name));
    for (const shell of shells) {
      const cached = browserUnder(join(root, shell.name));
      if (cached) return cached;
    }
  }
  return direct.find(executable) || null;
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
  ({ default: App } = await server.ssrLoadModule("/src/App.jsx"));
  ({ default: Shell, Sidebar } = await server.ssrLoadModule("/src/components/Shell.jsx"));
  ({ DashboardState } = await server.ssrLoadModule("/src/views/Dashboard.jsx"));
  ({ ProjectsState } = await server.ssrLoadModule("/src/views/Projects.jsx"));
  ({
    BoardState,
    boardNoticeFromSearch,
    EvidenceDrawerState,
    loadEvidenceDrawer,
    loadBoardRunProvenance,
    launchPopoverPlacement,
    mergeBoardStatus,
    pollBoardStatus,
    submitBoardAction,
    taskDisplayName,
    investigationMessage,
  } = await server.ssrLoadModule("/src/views/Board.jsx"));
  ({ WorkspaceState, submitProjectRestore } = await server.ssrLoadModule("/src/views/Workspace.jsx"));
  ({ SessionsState } = await server.ssrLoadModule("/src/views/Sessions.jsx"));
  ({ AlarmsState } = await server.ssrLoadModule("/src/views/Alarms.jsx"));
  ({ SessionReportState } = await server.ssrLoadModule("/src/views/SessionReport.jsx"));
  ({ SetupState } = await server.ssrLoadModule("/src/views/Setup.jsx"));
  ({
    default: TaskBreakdownReview,
    TaskBreakdownReviewState,
    submitBreakdownAction,
    buildAcceptForm,
    confirmReviewNavigation,
    preventReviewUnload,
    projectIdFromBoardHref,
  } = await server.ssrLoadModule("/src/views/TaskBreakdownReview.jsx"));
  ({ NavContext, NavigationGuardContext, OwnedLink, isReactOwnedPath } = await server.ssrLoadModule("/src/nav.jsx"));
  ({ parseRoute } = await server.ssrLoadModule("/src/routes.js"));
  ({ TaskHistoryState } = await server.ssrLoadModule("/src/views/TaskHistory.jsx"));
  ({ BudgetSettingsState } = await server.ssrLoadModule("/src/views/BudgetSettings.jsx"));
  ({ WorkerSettingsState } = await server.ssrLoadModule("/src/views/WorkerSettings.jsx"));
  ({ ControlPlaneSettingsState } = await server.ssrLoadModule("/src/views/ControlPlaneSettings.jsx"));
  ({ ProjectSettingsState } = await server.ssrLoadModule("/src/views/ProjectSettings.jsx"));
});

after(async () => {
  await server?.close();
});

function renderSidebar(overrides = {}) {
  const props = {
    activeProjectId: null,
    activeView: "dashboard",
    data: { portal_auth_required: false, sidebar_projects: [] },
    error: null,
    loading: false,
    ...overrides,
  };
  return renderToStaticMarkup(React.createElement(Sidebar, props));
}

function assertStatusPillsHaveGlyphs(markup) {
  const statuses = (markup.match(/class="status-pill status-pill-/g) || []).length;
  assert.ok(statuses > 0, "expected at least one rendered status pill");
  assert.equal((markup.match(/class="status-pill-glyph"/g) || []).length, statuses);
  assert.equal((markup.match(/class="status-pill-label"/g) || []).length, statuses);
}

function assertNoNestedPanels(markup) {
  const voidTags = new Set(["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"]);
  const stack = [];
  for (const match of markup.matchAll(/<(\/)?([a-z][\w:-]*)([^>]*)>/gi)) {
    const [, closing, rawTag, attributes] = match;
    const tag = rawTag.toLowerCase();
    if (closing) {
      while (stack.length) {
        const open = stack.pop();
        if (open.tag === tag) break;
      }
      continue;
    }
    const classes = attributes.match(/\bclass="([^"]*)"/)?.[1].split(/\s+/) || [];
    const isPanel = classes.includes("panel");
    assert.ok(!isPanel || !stack.some((open) => open.isPanel), `rendered nested panel at <${tag}>`);
    if (!voidTags.has(tag) && !attributes.trimEnd().endsWith("/")) stack.push({ tag, isPanel });
  }
}

function assertDisabledControlsHaveReasons(markup) {
  const controls = [...markup.matchAll(/<(button|input|select|textarea|fieldset)\b[^>]*disabled=""[^>]*>/g)];
  assert.ok(controls.length > 0, "expected at least one disabled control");
  for (const [control] of controls) {
    const describedBy = control.match(/aria-describedby="([^"]+)"/)?.[1];
    assert.ok(describedBy, `disabled control has no associated reason: ${control}`);
    for (const id of describedBy.split(/\s+/)) {
      assert.ok(markup.includes(`id="${id}"`), `disabled reason ${id} is not rendered`);
    }
  }
}

function dashboardData(overrides = {}) {
  return {
    next_actions: [{
      label: "Open task board",
      detail: "Estimate, launch, refresh, review, or block tasks",
      href: "/board",
      tone: "green",
    }],
    budget: {
      total_tokens: 150,
      daily_cap: 1_000,
      current_zone: "green",
      since: "2099-01-01T00:00:00+00:00",
    },
    worker_execution: {
      token_total: 150,
      status_split: { completed: 100, failed_retry: 50, unknown: 0 },
      components: { available: true, items: [{ label: "output", value: 50 }], cost: 0.0123 },
    },
    spend: {
      worker_execution: 150,
      agent_review_reporting: 0,
      planning_estimation: 0,
      setup_verification: 0,
      other: 0,
      cost_by_category: {
        control_plane: 1.0,
        task_breakdown: 0.5,
        worker_execution: 0.01,
        adapter_verification: 0,
        reporting_summary: 0,
        other: 0,
      },
      total_cost: 1.51,
      priced_tokens: 150,
      unpriced_tokens: 0,
    },
    alarms: {
      total: 1,
      open: 1,
      critical: 0,
      recent: [{
        id: "alarm-demo-999",
        type: "BUDGET_YELLOW",
        severity: "LOW",
        session_id: "sess-demo-999",
        recommended_action: "Review spend.",
      }],
    },
    active_sessions: [{
      id: "sess-demo-999",
      task_description: "DEMO dashboard task",
      model: "opencode/gpt-5.1",
      status: "running",
    }],
    estimation_accuracy: {
      completed_count: 3,
      median_error_ratio: 1.1,
      within_2x_pct: 100,
    },
    projects: [{
      id: "demo-999",
      name: "DEMO 999",
      task_count: 1,
      capability: { state: "launch_ready" },
    }],
    ...overrides,
  };
}

function renderDashboard(state) {
  return renderToStaticMarkup(React.createElement(DashboardState, state));
}

function workspaceData(overrides = {}) {
  return {
    project: {
      id: "demo-999",
      name: "DEMO workspace 999",
      root_path: "/DEMO/2099/repo",
      archived_at: null,
      capability: {
        state: "launch_ready",
        label: "Launch ready",
        reasons: [],
      },
      profile: {
        git_branch: "implementation/demo-999",
        language_hints: ["Python", "JavaScript"],
        framework_hints: ["FastAPI", "React"],
        package_manager_hints: ["uv", "npm"],
        test_command: "uv run pytest",
        run_command: "uv run foremanctl serve",
        relevant_docs: ["README.md", "CONTEXT.md"],
      },
    },
    summary: {
      counts: { Estimated: 1, Running: 2, Review: 3, Done: 4, Blocked: 5 },
      total_tasks: 15,
      launch_ready: true,
      capability_state: "launch_ready",
      attention_actions: [{
        label: "Running work",
        detail: "2 slices need refresh",
        href: "/projects/demo-999/board",
        tone: "blue",
      }, {
        label: "Worker setup",
        detail: "Review adapter configuration",
        href: "/settings/workers",
        tone: "yellow",
      }],
    },
    controls: { can_open_board: true, can_restore: false },
    links: {
      board_href: "/projects/demo-999/board",
      task_history_href: "/projects/demo-999/task-history",
      sessions_href: "/sessions",
      worker_setup_href: "/settings/workers",
      project_settings_href: "/settings/project",
      restore_href: null,
    },
    ...overrides,
  };
}

function renderWorkspace(state) {
  return renderToStaticMarkup(React.createElement(WorkspaceState, state));
}

function boardData() {
  const emptyStates = Object.fromEntries(
    ["Estimated", "Running", "Review", "Done"].map((status) => [status, `No ${status} tasks`]),
  );
  const detail = {
    task_body: { text: "Full DEMO task body", truncated: false },
    token_components: {
      available: true,
      items: [{ key: "output", label: "Output", value: 21 }],
      cost: 0.01,
      turn_count: 2,
    },
    launch: {
      worker_run_id: "run-demo-999",
      adapter_id: "codex",
      model: "gpt-5.4",
      tracking_mode: "native_usage",
      usage_source: "codex_jsonl",
      status: "completed",
      returncode: 0,
      workdir: "/DEMO/2099",
      error: { text: "", truncated: false },
      blocked_reason: { text: "", truncated: false },
      retryable_failure: { returncode: null, summary: { text: "", truncated: false } },
      diagnostic: {
        summary: { text: "Launch ready", truncated: false },
        next_action: { text: "", truncated: false },
        setup_href: "/settings/workers",
      },
    },
    timeline: [{
      created_at: "2099-01-01T00:00:00Z",
      kind: "worker_completed",
      title: "Worker completed",
      detail_summary: { text: "DEMO timeline detail", truncated: false },
    }],
    logs: {
      stdout: { text: "DEMO stdout", truncated: false },
      stderr: { text: "", truncated: false },
    },
    review: {
      prompt: { text: "Check DEMO contract", truncated: false },
      agent_review: {
        status: "completed",
        recommendation: "accept",
        summary: { text: "Review passed", truncated: false },
        failure: { text: "", truncated: false },
        findings: [{ severity: "info", message: { text: "No defects", truncated: false }, path: null, line: null }],
        review_session_href: "/sessions/review-demo-999",
        model: "openai/gpt-4.1-mini",
        token_total: 34,
      },
    },
    blocked: { reason: { text: "Needs operator input", truncated: false }, requires_manual_estimate: true },
  };
  const card = (status, controls = {}) => ({
    id: `task-${status.toLowerCase()}-999`,
    status,
    summary: { text: `${status} DEMO task`, truncated: false },
    estimate_tokens: 100,
    actual_tokens: ["Review", "Done"].includes(status) ? 89 : null,
    recommended_model: "gpt-5.3",
    launch_model: status === "Review" ? "gpt-5.4" : null,
    session_href: status === "Review" ? "/sessions/session-demo-999" : null,
    blocked_condition: status === "Review"
      ? { reason: "Needs operator disposition", origin: "review", timestamp: "2099-01-01T00:00:00Z" }
      : null,
    review_prompt: detail.review.prompt,
    timeline: detail.timeline,
    controls: {
      can_launch: false,
      can_refresh: false,
      can_save_review_prompt: false,
      can_agent_review: false,
      can_mark_done: false,
      can_block: false,
      can_archive: false,
      can_dismiss: false,
      requires_manual_estimate: false,
      budget_override_available: false,
      native_usage_override_ack_required: false,
      native_usage_override_ack_text: null,
      setup_href: "/settings/workers",
      ...controls,
    },
  });
  return {
    project: { id: "demo-999", name: "DEMO 999" },
    workspace: workspaceData({
      links: {
        ...workspaceData().links,
        board_href: "/projects/demo-999",
        floor_href: "/projects/demo-999/floor",
      },
    }),
    needs_you: {
      project_id: "demo-999",
      count: 2,
      items: [
        { id: "breakdown:breakdown-demo-999", kind: "breakdown_review", title: "Review proposed Task Breakdown", reason: "Proposed Task Breakdown awaits review.", action_label: "Review breakdown", href: "/task-breakdowns/breakdown-demo-999/review", source: "DEMO_INTAKE_2099_999.md", candidate_count: 1, status: "proposed", created_at: "2099-01-01T00:00:00Z" },
        { id: "task:task-estimated-999", kind: "manual_estimate", title: "Manual estimate required", reason: "Automatic estimation needs operator input.", action_label: "Open task", href: "/projects/demo-999#task-task-estimated-999" },
      ],
    },
    columns: ["Estimated", "Running", "Review", "Done"],
    board_summary: {
      launch_ready: true,
      total_tasks: 4,
      counts: { Estimated: 1, Running: 1, Review: 1, Done: 1 },
      archived_count: 0,
      history_total_tasks: 4,
    },
    history_href: "/projects/demo-999/task-history",
    board_empty_states: emptyStates,
    automation: {
      counts: { Estimated: 1, Running: 1, Review: 1, Done: 1 },
      eligible_count: 1,
      queue: { status: "idle", auto_agent_review: false, latest_stop_reason: null },
      live_refresh_enabled: true,
    },
    adapters: [{
      id: "codex",
      name: "Codex",
      is_default: true,
      launchable: true,
      allowed_models: ["gpt-5.4"],
      tracking: {
        mode: "native_usage",
        label: "CLI: Track native usage after run",
        accounting: "Budget-authoritative after run",
      },
    }, {
      id: "proxy-adapter",
      name: "Proxy Adapter",
      is_default: false,
      launchable: true,
      allowed_models: ["gpt-5.4"],
      tracking: {
        mode: "proxy_governed",
        label: "API / Proxy: Governed through Harness Proxy",
        accounting: "Budget-authoritative during run",
      },
    }, {
      id: "observed-adapter",
      name: "Observed Adapter",
      is_default: false,
      launchable: false,
      allowed_models: ["gpt-5.4"],
      tracking: {
        mode: "observed_only",
        label: "CLI: Observe command only",
        accounting: "Not budget-authoritative",
      },
    }],
    tasks_by_status: {
      Estimated: [card("Estimated", {
        can_launch: true,
        can_dismiss: true,
        requires_manual_estimate: true,
        budget_override_available: true,
        native_usage_override_ack_required: true,
        native_usage_override_ack_text: "Acknowledge native usage overrun risk",
      })],
      Running: [card("Running", { can_refresh: true })],
      Review: [card("Review", {
        can_save_review_prompt: true,
        can_agent_review: true,
        can_mark_done: true,
        can_block: true,
      })],
      Done: [card("Done", { can_archive: true })],
    },
  };
}

function evidencePage(items = []) {
  return { items, pagination: { offset: 0, limit: 50, total: items.length, has_more: false, next_href: null } };
}

function sessionBounded(preview, truncated = false) {
  return { preview, truncated, full_href: truncated ? "/api/sessions/sess-demo-999/text/task" : null };
}

function reportData() {
  return {
    session: { id: "sess-demo-999", kind: "Worker Session", task: sessionBounded("DEMO task 2099", true), model: "gpt-5.5", status: "running", started_at: "2099-01-01T00:00:00Z", active: true },
    summary: {
      selected_project: sessionBounded("DEMO project 999"), launch_target: sessionBounded("opencode run"), adapter_id: "opencode", worker_model: "gpt-5.5", tracking_mode: "native_usage", status: "running", result: sessionBounded("Worker running"), requires_review: true,
      missing_labels: ["missing authoritative usage"], evidence_counts: { alarms: 1, checkpoints: 1, failed_checkpoints: 1, worker_runs: 1, worker_events: 1, error_events: 0 },
    },
    tokens: {
      provider_totals: { prompt_tokens: 30, completion_tokens: 20, total_tokens: 50 },
      normalized: { total_tokens: 40, by_category: { control_plane: 1, task_breakdown: 2, worker_execution: 30, adapter_verification: 3, reporting_summary: 4, other: 0 } },
      worker_components: { available: true, items: [{ key: "cache_read", label: "cache read/reused context", value: 10 }, { key: "output", label: "output", value: 20 }], cost: 0.01, turn_count: 1 },
      log: evidencePage([{ usage_kind: "worker", model: "gpt-5.5", prompt_tokens: 30, completion_tokens: 20, total_tokens: 50, cost: 0.01, raw_usage: sessionBounded("provider raw usage", true) }]),
    },
    zone_timeline: evidencePage([{ zone: "yellow", max_tokens: 2048, created_at: "2099-01-01T00:00:01Z" }]),
    worker_timeline: evidencePage([{ created_at: "2099-01-01T00:00:02Z", level: "info", layer: "worker_harness", kind: "launch", title: "Worker launched", detail_summary: "status=running", detail: sessionBounded("timeline detail", true) }]),
    repo_context_briefs: evidencePage([{ worker_run_id: "run-demo-999", documents: evidencePage([{ path: "AGENTS.md" }]), manifests: evidencePage(["pyproject.toml"]), text: sessionBounded("Repo Context Brief text", true) }]),
    alarms: evidencePage([{ id: "alarm-demo-999", type: "BUDGET_YELLOW", severity: "MEDIUM", recommended_action: "Review spend", created_at: "2099-01-01T00:00:03Z" }]),
    checkpoints: evidencePage([{ name: "budget_health", passed: false, details: sessionBounded("checkpoint detail", true) }]),
    related_agent_review: {
      status: "completed", recommendation: "approve", summary: sessionBounded("Agent Review summary", true), model: "claude-demo-999", reviewed_at: "2099-01-01T00:00:04Z", review_session_id: "review-demo-999", review_session_href: "/sessions/review-demo-999", review_total_tokens: 19, error: null,
      findings: evidencePage([sessionBounded("Agent Review finding", true)]),
    },
    freshness: { session_id: "sess-demo-999", status: "running", active: true, version: "a".repeat(64), last_evidence_at: "2099-01-01T00:00:04Z" },
    links: { sessions_href: "/sessions", self_href: "/sessions/sess-demo-999" },
  };
}

function completedReportData() {
  const data = reportData();
  data.session.status = "completed";
  data.session.active = false;
  data.summary.status = "completed";
  data.summary.result = sessionBounded("Worker completed");
  data.summary.missing_labels = [];
  data.freshness.status = "completed";
  data.freshness.active = false;
  return data;
}

test("only exact React routes are parsed as owned views", () => {
  assert.deepEqual(parseRoute("/app"), { view: "dashboard" });
  assert.deepEqual(parseRoute("/dashboard"), { view: "dashboard" });
  assert.deepEqual(parseRoute("/projects"), { view: "projects" });
  assert.deepEqual(parseRoute("/alarms"), { view: "alarms" });
  assert.deepEqual(parseRoute("/sessions"), { view: "sessions" });
  assert.deepEqual(parseRoute("/sessions/sess-demo-999"), {
    view: "sessionReport",
    sessionId: "sess-demo-999",
  });
  assert.deepEqual(parseRoute("/projects/demo-999"), {
    view: "pipeline",
    projectId: "demo-999",
  });
  assert.deepEqual(parseRoute("/projects/demo-999/floor"), {
    view: "floor",
    projectId: "demo-999",
  });
  assert.deepEqual(parseRoute("/projects/demo-999/plan"), {
    view: "planningChat",
    projectId: "demo-999",
  });
  assert.deepEqual(parseRoute("/projects/demo-999/needs-you"), {
    view: "needsYou",
    projectId: "demo-999",
  });
  assert.equal(parseRoute("/projects/demo-999/task-history").view, "taskHistory");
  assert.equal(parseRoute("/app/projects/demo-999/task-history").view, "notFound");
  for (const path of [
    "/app/settings",
    "/app/not-a-migrated-route",
    "/projects/demo-999/board",
    "/app/projects/demo-999",
    "/app/projects/demo-999/board",
    "/app/projects/demo-999/floor",
    "/app/projects/demo-999/needs-you",
    "/projects/demo-999/extra",
    "/projects/demo-999/board/extra",
    "/app/projects/demo-999/extra",
    "/app/projects/demo-999/board/extra",
    "/app/projects",
    "/app/dashboard",
  ]) {
    assert.deepEqual(parseRoute(path), { view: "notFound" });
  }
});

test("isReactOwnedPath derives ownership from parseRoute and ignores query or hash", () => {
  assert.equal(isReactOwnedPath("/settings/control-plane"), true);
  assert.equal(isReactOwnedPath("/settings/workers?adapter_id=opencode"), true);
  assert.equal(isReactOwnedPath("/sessions/sess-demo-999"), true);
  assert.equal(isReactOwnedPath("/task-breakdowns/demo-999/review"), true);
  assert.equal(isReactOwnedPath("/projects/demo-999/needs-you"), true);
  assert.equal(isReactOwnedPath("/app/projects/demo-999/needs-you"), false);
  assert.equal(isReactOwnedPath("/board"), false);
  assert.equal(isReactOwnedPath("/login"), false);
  assert.equal(isReactOwnedPath("/logout"), false);
  assert.equal(isReactOwnedPath("/unknown-route-2099"), false);
});

test("OwnedLink renders AppLink for React-owned routes and raw anchor for server routes", () => {
  function renderOwned(to) {
    return create(React.createElement(OwnedLink, { to, className: "test-link" }, "link"));
  }
  const owned = renderOwned("/settings/control-plane");
  const ownedAnchor = owned.root.findByType("a");
  assert.equal(ownedAnchor.props.href, "/settings/control-plane");
  assert.equal(typeof ownedAnchor.props.onClick, "function");

  const query = renderOwned("/settings/workers?adapter_id=opencode");
  const queryAnchor = query.root.findByType("a");
  assert.equal(queryAnchor.props.href, "/settings/workers?adapter_id=opencode");
  assert.equal(typeof queryAnchor.props.onClick, "function");

  const notOwned = renderOwned("/board");
  const notOwnedAnchor = notOwned.root.findByType("a");
  assert.equal(notOwnedAnchor.props.href, "/board");
  assert.equal(notOwnedAnchor.props.onClick, undefined);

  const login = renderOwned("/login");
  const loginAnchor = login.root.findByType("a");
  assert.equal(loginAnchor.props.href, "/login");
  assert.equal(loginAnchor.props.onClick, undefined);
});

test("grouped rail keeps project switching, active state, semantic badges, and keyboard labels", () => {
  const data = {
    portal_auth_required: true,
    sidebar_projects: [
      { id: "demo-999", name: "DEMO 999", task_count: 1, needs_you_count: 3 },
      { id: "other-999", name: "Other DEMO 999", task_count: 0, needs_you_count: 0 },
    ],
  };
  const markup = renderSidebar({
    activeView: "pipeline",
    activeProjectId: "demo-999",
    data,
    alarmCount: 2,
  });

  for (const label of ["Project", "Governance", "Configure", "Pipeline", "Needs You", "Execution Floor", "Planning", "Dashboard", "Sessions", "Alarms"]) {
    assert.match(markup, new RegExp(`>${label}<`));
  }
  assert.match(markup, /<select[^>]*aria-label="Switch project"[^>]*>/);
  assert.match(markup, /href="\/projects\/demo-999"[^>]*aria-current="page"/);
  assert.match(markup, /href="\/projects\/demo-999\/needs-you"[^>]*aria-label="Needs You, 3 Needs You"/);
  assert.doesNotMatch(markup, /href="\/projects\/demo-999"[^>]*aria-label="Pipeline, 3 Needs You"/);
  assert.match(markup, /href="\/alarms"[^>]*aria-label="Alarms, 2 open alarms"/);
  assert.match(markup, /action="\/logout"/);
  assert.doesNotMatch(markup, /└/);

  let destination;
  let tree;
  act(() => {
    tree = create(
      React.createElement(
        NavContext.Provider,
        { value: (to) => { destination = to; return true; } },
        React.createElement(Sidebar, {
          activeView: "pipeline",
          activeProjectId: "demo-999",
          data,
          error: null,
          loading: false,
          alarmCount: 2,
        }),
      ),
    );
  });
  const select = tree.root.findByProps({ "aria-label": "Switch project" });
  act(() => { select.props.onChange({ target: { value: "other-999" } }); });
  assert.equal(destination, "/projects/other-999");
  const railLinks = tree.root.findAll((node) => node.type === "a" && node.props["data-rail-link"]);
  assert.ok(railLinks.length > 0);
  for (const link of railLinks) {
    assert.ok(link.props.href, "rail navigation retains a real browser URL");
    assert.ok(link.props["aria-label"], "collapsed rail navigation retains its keyboard label");
  }
});

test("Needs You direct loads use the existing project projection without board data", async (t) => {
  const originalFetch = globalThis.fetch;
  const originalWindow = globalThis.window;
  const originalActFlag = globalThis.IS_REACT_ACT_ENVIRONMENT;
  t.after(() => {
    globalThis.fetch = originalFetch;
    globalThis.window = originalWindow;
    globalThis.IS_REACT_ACT_ENVIRONMENT = originalActFlag;
  });
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  globalThis.window = {
    location: {
      origin: "http://portal.test",
      pathname: "/projects/demo-999/needs-you",
      search: "",
    },
    history: { pushState: () => {} },
    addEventListener: () => {},
    removeEventListener: () => {},
    setInterval,
    clearInterval,
  };
  const requested = [];
  globalThis.fetch = async (url) => {
    requested.push(url);
    if (url === "/api/portal/nav") {
      return { ok: true, json: async () => ({
        portal_auth_required: false,
        sidebar_projects: [{ id: "demo-999", name: "DEMO 999", task_count: 1, needs_you_count: 1 }],
      }) };
    }
    if (url === "/api/alarms?filter=open") {
      return { ok: true, json: async () => ({ filters: [], alarms: [] }) };
    }
    if (url === "/api/projects/demo-999/workspace") {
      return { ok: true, json: async () => workspaceData() };
    }
    if (url === "/api/projects/demo-999/needs-you") {
      return { ok: true, json: async () => ({
        project_id: "demo-999",
        count: 1,
        items: [{ id: "breakdown:demo-999", kind: "breakdown_review", title: "Task breakdown awaits review", reason: "Review the proposed vertical slices.", action_label: "Review breakdown", href: "/task-breakdowns/demo-999/review" }],
      }) };
    }
    throw new Error(`Unexpected fetch: ${url}`);
  };

  let renderer;
  await act(async () => { renderer = create(React.createElement(App)); });
  const markup = JSON.stringify(renderer.toJSON());
  assert.match(markup, /Task breakdown awaits review/);
  assert.ok(requested.includes("/api/projects/demo-999/needs-you"));
  assert.ok(requested.includes("/api/projects/demo-999/workspace"));
  assert.ok(!requested.includes("/api/projects/demo-999/board"));
  await act(async () => { renderer.unmount(); });
});

test("project switching preserves App Back and Forward history", async (t) => {
  const originalFetch = globalThis.fetch;
  const originalWindow = globalThis.window;
  const originalActFlag = globalThis.IS_REACT_ACT_ENVIRONMENT;
  t.after(() => {
    globalThis.fetch = originalFetch;
    globalThis.window = originalWindow;
    globalThis.IS_REACT_ACT_ENVIRONMENT = originalActFlag;
  });
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;

  const location = { origin: "http://portal.test", pathname: "/app", search: "" };
  const entries = ["/app"];
  let entryIndex = 0;
  let popstate;
  const applyLocation = (to) => {
    const next = new URL(to, location.origin);
    location.pathname = next.pathname;
    location.search = next.search;
  };
  const history = {
    pushState: (_state, _title, to) => {
      entries.splice(entryIndex + 1);
      entries.push(String(to));
      entryIndex = entries.length - 1;
      applyLocation(to);
    },
    back: () => {
      if (entryIndex === 0) return;
      entryIndex -= 1;
      applyLocation(entries[entryIndex]);
      popstate();
    },
    forward: () => {
      if (entryIndex >= entries.length - 1) return;
      entryIndex += 1;
      applyLocation(entries[entryIndex]);
      popstate();
    },
    replaceState: () => {},
  };
  globalThis.window = {
    location,
    history,
    addEventListener: (name, listener) => { if (name === "popstate") popstate = listener; },
    removeEventListener: () => {},
    setInterval,
    clearInterval,
    confirm: () => true,
  };

  const navigation = {
    portal_auth_required: true,
    sidebar_projects: [
      { id: "demo-999", name: "DEMO 999", task_count: 1, needs_you_count: 3 },
      { id: "other-999", name: "Other DEMO 999", task_count: 0, needs_you_count: 0 },
    ],
  };
  const otherBoard = boardData();
  otherBoard.project = { id: "other-999", name: "Other DEMO 999" };
  otherBoard.workspace = workspaceData({ project: otherBoard.project });
  otherBoard.automation.live_refresh_enabled = false;
  const requested = [];
  globalThis.fetch = async (url) => {
    requested.push(url);
    if (url === "/api/portal/nav") return { ok: true, json: async () => navigation };
    if (url === "/api/alarms?filter=open") {
      return { ok: true, json: async () => ({ filters: [{ value: "open", count: 2 }], selected_filter: "open", alarms: [] }) };
    }
    if (url === "/api/dashboard") return { ok: true, json: async () => dashboardData() };
    if (url === "/api/projects/other-999/workspace") return { ok: true, json: async () => otherBoard.workspace };
    if (url === "/api/projects/other-999/board") return { ok: true, json: async () => otherBoard };
    if (url === "/api/projects/other-999/needs-you") return { ok: true, json: async () => otherBoard.needs_you };
    throw new Error(`Unexpected fetch: ${url}`);
  };

  let renderer;
  await act(async () => { renderer = create(React.createElement(App)); });
  const activeHref = () => renderer.root.findAllByType("a").find((link) => link.props["aria-current"] === "page")?.props.href;
  assert.equal(activeHref(), "/app");
  assert.equal(requested.filter((url) => url === "/api/dashboard").length, 1);
  assert.ok(requested.includes("/api/alarms?filter=open"));
  const alarmsLink = renderer.root.findAllByType("a").find((link) => link.props.href === "/alarms");
  assert.equal(alarmsLink.props["aria-label"], "Alarms, 2 open alarms");

  const switcher = renderer.root.findByProps({ "aria-label": "Switch project" });
  await act(async () => { switcher.props.onChange({ target: { value: "other-999" } }); });
  assert.equal(location.pathname, "/projects/other-999");
  assert.equal(activeHref(), "/projects/other-999");

  await act(async () => { history.back(); });
  assert.equal(location.pathname, "/app");
  assert.equal(activeHref(), "/app");

  await act(async () => { history.forward(); });
  assert.equal(location.pathname, "/projects/other-999");
  assert.equal(activeHref(), "/projects/other-999");
  await act(async () => { renderer.unmount(); });
});

test("authenticated shell supplies per-page context without retired brand chrome", () => {
  const markup = renderToStaticMarkup(
    React.createElement(Shell, { activeView: "dashboard", activeProjectId: null }, "Dashboard content"),
  );
  assert.match(markup, /aria-label="Page context"/);
  assert.match(markup, /Governance/);
  assert.match(markup, /Dashboard/);
  assert.doesNotMatch(markup, /<header/);
  assert.doesNotMatch(markup, /shell-footer|operator-controlled budget governance/);
});

test("grouped rail Configure links stay in-shell while login remains a recovery navigation", () => {
  let tree;
  act(() => {
    tree = create(React.createElement(Sidebar, {
      activeView: "dashboard",
      activeProjectId: null,
      data: { portal_auth_required: false, sidebar_projects: [] },
      error: null,
      loading: false,
    }));
  });
  const links = tree.root.findAll((node) => node.type === "a" && node.props.href);
  const byHref = Object.fromEntries(links.map((node) => [node.props.href, node]));
  for (const href of ["/settings/control-plane", "/settings/budget", "/settings/project", "/settings/workers", "/projects"]) {
    assert.equal(typeof byHref[href].props.onClick, "function", `expected in-shell link for ${href}`);
  }
  assert.equal(byHref["/board"], undefined);
});

test("Projects and project settings mark only their canonical rail entries active", () => {
  const projects = renderSidebar({ activeView: "projects" });
  assert.match(projects, /href="\/projects"[^>]*aria-current="page"/);
  assert.doesNotMatch(projects, /href="\/settings\/project"[^>]*aria-current="page"/);

  const settings = renderSidebar({ activeView: "projectSettings" });
  assert.match(settings, /href="\/settings\/project"[^>]*aria-current="page"/);
  assert.doesNotMatch(settings, /href="\/projects"[^>]*aria-current="page"/);
});

test("Projects view renders empty, active, archived, and disabled runner states", () => {
  const loading = renderToStaticMarkup(React.createElement(ProjectsState, { data: null, error: null, loading: true, onRefresh: () => {} }));
  assert.match(loading, /Loading projects…/);

  const failed = renderToStaticMarkup(React.createElement(ProjectsState, {
    data: null,
    error: new Error("offline"),
    loading: false,
    onRefresh: () => {},
  }));
  assert.match(failed, /Could not load projects/);
  assert.match(failed, /href="\/projects"/);

  const empty = renderToStaticMarkup(React.createElement(ProjectsState, {
    data: { projects: [], archived_projects: [], local_runner_enabled: true },
    error: null,
    loading: false,
    onRefresh: () => {},
  }));
  assert.match(empty, /No projects yet/);
  assert.match(empty, /No archived projects/);

  const disabled = renderToStaticMarkup(React.createElement(ProjectsState, {
    data: { projects: [], archived_projects: [], local_runner_enabled: false },
    error: null,
    loading: false,
    onRefresh: () => {},
  }));
  assert.match(disabled, /Local Runner disabled/);

  const populated = renderToStaticMarkup(React.createElement(ProjectsState, {
    data: {
      projects: [
        { id: "active-999", name: "Active Repo", root_path: "/active", capability: { state: "launch_ready", label: "Launch-ready", reasons: [] } },
        { id: "blocked-999", name: "Blocked Repo", root_path: "/blocked", capability: { state: "blocked", label: "Blocked", reasons: ["Setup required"] } },
      ],
      archived_projects: [
        { id: "archived-999", name: "Archived Repo", root_path: "/archived", archived_at: "2099-01-01T00:00:00Z", capability: { state: "blocked", label: "Blocked", reasons: [] } },
      ],
      local_runner_enabled: true,
    },
    error: null,
    loading: false,
    onRefresh: () => {},
  }));
  assert.match(populated, /Active Repo/);
  assert.match(populated, /Blocked Repo/);
  assert.match(populated, /class="status-pill status-pill-warning"[^>]*>.*class="status-pill-label">Blocked<\/span>/s);
  assert.match(populated, /Archived Repo/);
  assert.match(populated, /Archived 2099-01-01T00:00:00Z/);
  assert.match(populated, /href="\/projects\/active-999"/);
  assert.match(populated, /href="\/projects\/archived-999"/);
});

test("Dashboard is the sole active home navigation item", () => {
  const markup = renderSidebar();
  assert.match(markup, /href="\/app"[^>]*aria-current="page"/);
  assert.doesNotMatch(markup, /href="\/sessions"[^>]*aria-current="page"/);
  assert.doesNotMatch(markup, /href="\/alarms"[^>]*aria-current="page"/);
});

test("Sessions sidebar and list preserve compact scan, states, and pagination", () => {
  const sidebar = renderSidebar({ activeView: "sessions" });
  assert.match(sidebar, /href="\/sessions"[^>]*aria-current="page"/);
  assert.doesNotMatch(sidebar, /href="\/app"[^>]*aria-current="page"/);

  const loading = renderToStaticMarkup(React.createElement(SessionsState, { data: null, error: null, loading: true }));
  assert.match(loading, /Loading Sessions/);
  const failed = renderToStaticMarkup(React.createElement(SessionsState, { data: null, error: new Error("secret"), loading: false }));
  assert.match(failed, /Could not load Sessions. Retry/);
  assert.doesNotMatch(failed, /secret/);
  const data = {
    sessions: [{ id: "sess-demo-999", kind: "Agent Review", task_preview: "DEMO review task", model: "claude-demo-999", status: "running", active: true, token_totals: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 }, evidence_counts: { worker_runs: 1, worker_events: 2, failed_checkpoints: 1 }, current_zone: "yellow", alarm_count: 1, report_href: "/sessions/sess-demo-999" }],
    pagination: { offset: 0, limit: 1, total: 2, has_more: true }, has_active: true, poll_after_ms: 5000,
  };
  const populated = renderToStaticMarkup(React.createElement(SessionsState, { data, error: null, loading: false }));
  for (const text of ["Agent Review", "DEMO review task", "claude-demo-999", "10 prompt", "5 completion", "15 total", "1 runs", "2 events", "1 failed checks", "yellow zone", "1 alarms", "Active sessions refresh every 5 seconds", "Next sessions"]) assert.match(populated, new RegExp(text));
  assert.match(populated, /href="\/sessions\/sess-demo-999"/);
  assertStatusPillsHaveGlyphs(populated);
  assert.match(populated, /status-pill-warning[^>]*>.*status-pill-label">yellow zone<\/span>/s);
});

test("Setup sidebar highlighting is exclusive and cards render backend readiness", () => {
  const sidebar = renderSidebar({ activeView: "setup" });
  assert.match(sidebar, /href="\/setup"[^>]*aria-current="page"/);
  assert.doesNotMatch(sidebar, /href="\/app"[^>]*aria-current="page"/);
  assert.doesNotMatch(sidebar, /href="\/sessions"[^>]*aria-current="page"/);
  assert.doesNotMatch(sidebar, /href="\/settings\/[^"]*"[^>]*aria-current="page"/);

  const data = {
    steps: [
      { name: "Control plane model", state: "ready", href: "/settings/control-plane", detail: "claude-demo-999" },
      { name: "Token budget", state: "ready", href: "/settings/budget", detail: "Daily 1,000 · Session 500" },
      { name: "Worker adapter", state: "needs setup", href: "/settings/workers?adapter_id=opencode", detail: "OpenCode" },
      { name: "Projects", state: "needs setup", href: "/settings/project", detail: "No launch-ready project" },
    ],
    ready_to_launch: false,
    next_step: { label: "Open Worker adapter", href: "/settings/workers?adapter_id=opencode", detail: "OpenCode" },
    active_adapter: { name: "OpenCode", verification_status: "verified", launchable: false, tracking_mode: "unverified" },
  };
  const populated = renderToStaticMarkup(React.createElement(SetupState, { data, error: null, loading: false }));
  for (const text of ["First-run setup", "Control plane model", "Token budget", "Worker adapter", "Projects", "No launch-ready project", "setup needed", "OpenCode", "unverified"]) {
    assert.match(populated, new RegExp(text));
  }
  assertStatusPillsHaveGlyphs(populated);
  assert.match(populated, /class="status-pill-label">false<\/span>/);
  assert.match(populated, /class="status-pill status-pill-warning"[^>]*>.*class="status-pill-label">unverified<\/span>/s);
  assert.doesNotMatch(populated, />not launchable</);
  // The forwarded adapter context reaches the destination link.
  assert.match(populated, /href="\/settings\/workers\?adapter_id=opencode"/);
  assert.doesNotMatch(populated, /Open task board/);

  const ready = renderToStaticMarkup(React.createElement(SetupState, {
    data: { ...data, ready_to_launch: true, steps: data.steps.map((step) => ({ ...step, state: "ready" })), next_step: { label: "Open task board", href: "/projects/proj-demo-999/board", detail: "Governed Worker launch is ready." } },
    error: null,
    loading: false,
  }));
  assert.match(ready, /Open task board/);
  assert.match(ready, /href="\/projects\/proj-demo-999\/board"/);

  const failed = renderToStaticMarkup(React.createElement(SetupState, { data: null, error: new Error("secret"), loading: false }));
  assert.match(failed, /Could not load setup state/);
  assert.doesNotMatch(failed, /secret/);
});

test("Project Settings does not expose the retired read-only proof task creator", () => {
  const data = {
    local_runner_enabled: true,
    backend_status: { online: true, name: "Local Runner" },
    connected_projects: [{
      id: "project-demo-999",
      name: "DEMO project 999",
      root_path: "/demo/project",
      capability: { state: "launch_ready", reasons: [] },
    }],
    archived_projects: [],
  };
  const markup = renderToStaticMarkup(React.createElement(ProjectSettingsState, {
    data,
    error: null,
    loading: false,
    onRefresh: () => {},
  }));
  assert.match(markup, /DEMO project 999/);
  assert.doesNotMatch(markup, /Run read-only proof|Read-only proof launched|Read-only proof blocked/);
});

test("Alarms sidebar and list render from available_actions and bookmarkable filters", () => {
  const sidebar = renderSidebar({ activeView: "alarms" });
  assert.match(sidebar, /href="\/alarms"[^>]*aria-current="page"/);
  assert.doesNotMatch(sidebar, /href="\/app"[^>]*aria-current="page"/);

  const data = {
    filters: [
      { label: "Open", value: "open", selected: true, count: 1 },
      { label: "Resolved", value: "resolved", selected: false, count: 0 },
      { label: "All", value: "all", selected: false, count: 1 },
    ],
    selected_filter: "open",
    alarms: [{
      id: "alarm-demo-999",
      type: "DAILY_CAP_EXCEEDED",
      severity: "HIGH",
      session_id: "sess-demo-999",
      session_href: "/sessions/sess-demo-999",
      context: { text: "{\"daily_cap_tokens\":1000,\"daily_used_tokens\":900}", truncated: false },
      recommended_action: "Raise budget.",
      available_actions: [
        { action: "continue" },
        { action: "raise_budget", cap_key: "daily_cap_tokens", current_cap: 1000 },
      ],
      resolved_action: null,
      resolved_payload_summary: null,
      resolved_at: null,
    }],
  };
  const loading = renderToStaticMarkup(React.createElement(AlarmsState, { data: null, error: null, loading: true, filter: "open", onFilter: () => {}, onRefresh: () => {}, retry: () => {} }));
  assert.match(loading, /Loading Alarms/);

  const failed = renderToStaticMarkup(React.createElement(AlarmsState, { data: null, error: Object.assign(new Error("unauthorized"), { status: 401 }), loading: false, filter: "open", onFilter: () => {}, onRefresh: () => {}, retry: () => {} }));
  assert.match(failed, /Alarms require sign-in/);

  const populated = renderToStaticMarkup(React.createElement(AlarmsState, { data, error: null, loading: false, filter: "open", onFilter: () => {}, onRefresh: () => {}, retry: () => {} }));
  for (const text of ["DAILY_CAP_EXCEEDED", "HIGH", "alarm-demo-999", "sess-demo-999", "Raise budget.", "Continue", "Raise Budget", "Open", "Resolved", "All", "1000"]) {
    assert.match(populated, new RegExp(text));
  }
  assert.match(populated, /href="\/sessions\/sess-demo-999"/);
  assertStatusPillsHaveGlyphs(populated);
  assert.match(populated, /class="status-pill-label">HIGH<\/span>/);
  assert.doesNotMatch(populated, /Abort/);
  assert.doesNotMatch(populated, /adjust_guardrail/);
});

test("resolving an alarm refreshes both the list and shell badge", async (t) => {
  const originalFetch = globalThis.fetch;
  const originalActFlag = globalThis.IS_REACT_ACT_ENVIRONMENT;
  t.after(() => {
    globalThis.fetch = originalFetch;
    globalThis.IS_REACT_ACT_ENVIRONMENT = originalActFlag;
  });
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "/alarms/alarm-demo-999/resolve");
    assert.equal(options.method, "POST");
    return { ok: true, json: async () => ({ ok: true }) };
  };
  const data = {
    filters: [],
    alarms: [{
      id: "alarm-demo-999",
      type: "DAILY_CAP_EXCEEDED",
      severity: "HIGH",
      session_id: null,
      context: { text: "DEMO", truncated: false },
      recommended_action: "Continue.",
      available_actions: [{ action: "continue" }],
      resolved_at: null,
    }],
  };
  let listRefreshes = 0;
  let shellRefreshes = 0;
  let renderer;
  await act(async () => {
    renderer = create(React.createElement(AlarmsState, {
      data,
      error: null,
      loading: false,
      filter: "open",
      onFilter: () => {},
      onRefresh: async () => { listRefreshes += 1; },
      onStateChanged: () => { shellRefreshes += 1; },
      retry: () => {},
    }));
  });
  const continueButton = renderer.root.findAllByType("button").find((button) => button.children.join("") === "Continue");
  await act(async () => { await continueButton.props.onClick(); });
  assert.equal(listRefreshes, 1);
  assert.equal(shellRefreshes, 1);
  await act(async () => { renderer.unmount(); });
});

test("Session Report renders compact governance plus every bounded evidence path", () => {
  const markup = renderToStaticMarkup(React.createElement(SessionReportState, {
    data: reportData(), error: null, loading: false,
    freshnessNotice: { version: "b".repeat(64) },
    refreshError: "Could not check for new session evidence. Retry Refresh.",
  }));
  for (const text of [
    "Governance summary", "DEMO task 2099", "DEMO project 999", "opencode", "native_usage", "review needed", "missing authoritative usage",
    "Provider / raw totals", "Normalized budget total", "control_plane: 1", "worker_execution: 30", "reporting_summary: 4", "cache read/reused context",
    "Token log", "provider raw usage", "Budget-zone timeline", "yellow zone", "Worker Run timeline", "worker_harness", "Repo Context Brief", "AGENTS.md", "pyproject.toml",
    "Alarms", "BUDGET_YELLOW", "Checkpoint results", "FAIL", "Related Agent Review", "review/control-plane evidence", "19 review/control-plane tokens", "Agent Review finding",
    "Preview truncated", "Load full text", "New session evidence available", "Could not check for new session evidence",
  ]) assert.match(markup, new RegExp(text));
  assert.match(markup, /href="\/sessions\/review-demo-999"/);
  assert.match(markup, /aria-live="polite"/);
  assertStatusPillsHaveGlyphs(markup);
  for (const label of ["MEDIUM", "FAIL", "completed"]) assert.match(markup, new RegExp(`class="status-pill-label">${label}<\\/span>`));
  assert.ok(markup.indexOf("Governance summary") < markup.indexOf("Token log"));
});

test("Session Report refresh remounts paged evidence and labels review-session outcomes", () => {
  const data = reportData();
  data.session.kind = "Agent Review";
  const markup = renderToStaticMarkup(React.createElement(SessionReportState, { data, error: null, loading: false }));
  assert.match(markup, /Agent Review outcome/);
  const source = readFileSync(new URL("../src/views/SessionReport.jsx", import.meta.url), "utf8");
  for (const key of ["tokens-${version}", "zones-${version}", "worker-${version}", "repo-${version}", "alarms-${version}", "checkpoints-${version}"]) {
    assert.ok(source.includes(key));
  }
});

test("dashboard renders loading, error, populated, and empty states", () => {
  const loading = renderDashboard({ data: null, error: null, loading: true });
  assert.match(loading, /Loading dashboard…/);

  const failed = renderDashboard({ data: null, error: new Error("offline"), loading: false });
  assert.match(failed, /Could not load dashboard/);
  assert.doesNotMatch(failed, /server-rendered dashboard/);
  assert.match(failed, /href="\/dashboard"/);

  const populated = renderDashboard({ data: dashboardData(), error: null, loading: false });
  assert.match(populated, /Daily governed budget/);
  assert.match(populated, /Worker token component breakdown/);
  assert.match(populated, /href="\/board"/);
  assert.match(populated, /href="\/projects"/);
  assert.match(populated, /href="\/projects\/demo-999"/);
  assert.match(populated, /href="\/projects\/demo-999\/floor"/);
  assert.match(populated, /href="\/sessions\/sess-demo-999"/);
  assertStatusPillsHaveGlyphs(populated);
  assert.match(populated, /status-pill-success[^>]*>.*status-pill-label">launch_ready<\/span>/s);

  const aborted = renderDashboard({
    data: dashboardData({
      active_sessions: [{
        id: "sess-aborted-999",
        task_description: "DEMO aborted task",
        model: "opencode/gpt-5.1",
        status: "aborted",
      }],
    }),
    error: null,
    loading: false,
  });
  assert.match(aborted, /status-pill-danger[^>]*>.*status-pill-label">aborted<\/span>/s);

  const empty = renderDashboard({
    data: dashboardData({
      next_actions: [],
      alarms: { total: 0, open: 0, critical: 0, recent: [] },
      active_sessions: [],
      estimation_accuracy: { completed_count: null, median_error_ratio: null, within_2x_pct: null },
      projects: [],
    }),
    error: null,
    loading: false,
  });
  assert.match(empty, /No active sessions/);
  assert.match(empty, /No open alarms/);
  assert.doesNotMatch(empty, /Estimation accuracy/);
  assert.match(empty, /No projects are connected yet/);
  assert.match(empty, /href="\/settings\/project"/);
});

test("dashboard spend breakdown shows priced USD per category, unpriced labels, and coverage", () => {
  const populated = renderDashboard({ data: dashboardData(), error: null, loading: false });
  assert.match(populated, /Worker execution/);
  assert.match(populated, /\$0\.0100/);
  assert.match(populated, /Planning\/estimation/);
  assert.match(populated, /\$1\.5000/);
  assert.match(populated, /Priced spend/);
  assert.match(populated, /\$1\.5100/);
  assert.match(populated, /100% of tokens priced/);

  const unpriced = renderDashboard({
    data: dashboardData({
      spend: {
        worker_execution: 50,
        agent_review_reporting: 0,
        planning_estimation: 0,
        setup_verification: 0,
        other: 0,
        cost_by_category: {
          control_plane: null,
          task_breakdown: null,
          worker_execution: null,
          adapter_verification: 0,
          reporting_summary: null,
          other: 0,
        },
        total_cost: null,
        priced_tokens: 0,
        unpriced_tokens: 50,
      },
    }),
    error: null,
    loading: false,
  });
  assert.match(unpriced, /unpriced/);
  assert.match(unpriced, /no priced spend recorded/);
  assert.match(unpriced, /0% of tokens priced/);
});

test("dashboard estimation accuracy panel shows absent, progress, and figures states", () => {
  const absent = renderDashboard({
    data: dashboardData({ estimation_accuracy: { completed_count: null, median_error_ratio: null, within_2x_pct: null } }),
    error: null,
    loading: false,
  });
  assert.doesNotMatch(absent, /Estimation accuracy/);

  const progress = renderDashboard({
    data: dashboardData({ estimation_accuracy: { completed_count: 1, median_error_ratio: null, within_2x_pct: null } }),
    error: null,
    loading: false,
  });
  assert.match(progress, /Estimation accuracy/);
  assert.match(progress, /1 of 3 needed/);

  const figures = renderDashboard({
    data: dashboardData({ estimation_accuracy: { completed_count: 3, median_error_ratio: 1.1, within_2x_pct: 100 } }),
    error: null,
    loading: false,
  });
  assert.match(figures, /Completed tasks tracked/);
  assert.match(figures, /Median error ratio/);
  assert.match(figures, /Within 2× estimate/);
});

test("React workspace renders active summary, profile, and route-owned links", () => {
  const markup = renderWorkspace({
    projectId: "demo-999",
    data: workspaceData(),
    error: null,
    loading: false,
  });

  for (const text of [
    "DEMO workspace 999",
    "/DEMO/2099/repo",
    "Worker launch is ready",
    "15 tasks",
    "Launch ready",
    "Running work",
    "2 slices need refresh",
    "Repo profile",
    "implementation/demo-999",
    "Python, JavaScript",
    "FastAPI, React",
    "uv, npm",
    "uv run pytest",
    "uv run foremanctl serve",
    "README.md, CONTEXT.md",
  ]) assert.match(markup, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  for (const href of [
    "/projects/demo-999/board",
    "/projects/demo-999/task-history",
    "/sessions",
    "/settings/workers",
    "/settings/project",
  ]) assert.match(markup, new RegExp(`href="${href.replaceAll("/", "\\/")}"`));
  assert.ok(markup.indexOf("15 tasks") < markup.indexOf("Repo profile"));
  assert.doesNotMatch(markup, /Restore project/);

  const source = fileURLToPath(new URL("../src/views/Workspace.jsx", import.meta.url));
  const sourceText = readFileSync(source, "utf8");
  assert.match(sourceText, /<AppLink className="btn" to=\{links\.board_href\}/);
  assert.match(sourceText, /<a className="btn secondary" href=\{links\.sessions_href\}/);
});

test("React workspace renders safe missing, loading, error, and empty states", () => {
  const loading = renderWorkspace({ projectId: "demo-999", data: null, error: null, loading: true });
  assert.match(loading, /Loading project workspace…/);

  const failed = renderWorkspace({
    projectId: "demo-999", data: null, error: new Error("offline"), loading: false,
  });
  assert.match(failed, /Could not load workspace/);
  assert.doesNotMatch(failed, /offline/);
  assert.doesNotMatch(failed, /server-rendered/);

  const empty = renderWorkspace({ projectId: "demo-999", data: null, error: null, loading: false });
  assert.match(empty, /No project workspace state available/);

  const missingData = workspaceData();
  missingData.project.root_path = "";
  missingData.project.capability = { state: "", label: "", reasons: [] };
  missingData.project.profile = {
    git_branch: null,
    language_hints: [],
    framework_hints: [],
    package_manager_hints: [],
    test_command: null,
    run_command: null,
    relevant_docs: [],
  };
  const missing = renderWorkspace({
    projectId: "demo-999", data: missingData, error: null, loading: false,
  });
  assert.match(missing, /Root path unavailable/);
  assert.match(missing, /Unknown/);
  assert.match(missing, /not detected/);
  assert.match(missing, />none</);
  assert.doesNotMatch(missing, /undefined/);
});

test("archived React workspace is restore-first and preserves evidence links", () => {
  const data = workspaceData();
  data.project.archived_at = "2099-01-01T00:00:00Z";
  data.summary.launch_ready = false;
  data.summary.capability_state = "archived";
  data.controls = { can_open_board: false, can_restore: true };
  data.links.board_href = null;
  data.links.restore_href = "/projects/demo-999/restore";
  const markup = renderWorkspace({
    projectId: "demo-999",
    data,
    error: null,
    loading: false,
    restoreError: "Could not restore project.",
    restoreRetryHref: "/projects",
  });

  assert.match(markup, /Archived project/);
  assert.match(markup, /2099-01-01T00:00:00Z/);
  assert.match(markup, /Restore project/);
  assert.match(markup, /Could not restore project/);
  assert.match(markup, /href="\/projects">Open projects/);
  assert.match(markup, /href="\/projects\/demo-999\/task-history"/);
  assert.match(markup, /href="\/sessions"/);
  assert.doesNotMatch(markup, />Open board</);
  assert.doesNotMatch(markup, /Worker launch is ready/);
});

test("project Restore controller refetches only after bounded success", async () => {
  let successCalls = 0;
  let request;
  const success = await submitProjectRestore({
    url: "/projects/demo-999/restore",
    fetchImpl: async (url, options) => {
      request = { url, options };
      return {
        ok: true,
        json: async () => ({
          ok: true,
          error: null,
          next_href: "/projects/demo-999",
          retry_href: null,
          project: { id: "demo-999", archived: false },
        }),
      };
    },
    onSuccess: async () => { successCalls += 1; },
  });
  assert.deepEqual(success, { ok: true, error: null, retryHref: null });
  assert.equal(successCalls, 1);
  assert.equal(request.url, "/projects/demo-999/restore");
  assert.equal(request.options.method, "POST");
  assert.equal(request.options.headers.Accept, "application/json");
  assert.equal(request.options.credentials, "same-origin");

  const longError = "e".repeat(1200);
  const failure = await submitProjectRestore({
    url: "/projects/demo-999/restore",
    fetchImpl: async () => ({
      ok: false,
      json: async () => ({ ok: false, error: longError, retry_href: "/projects" }),
    }),
    onSuccess: async () => { successCalls += 1; },
  });
  assert.equal(failure.ok, false);
  assert.equal(failure.error.length, 1000);
  assert.equal(failure.retryHref, "/projects");
  assert.equal(successCalls, 1);

  const invalid = await submitProjectRestore({
    url: "/projects/demo-999/restore",
    fetchImpl: async () => ({ ok: false, json: async () => { throw new Error("raw body"); } }),
    onSuccess: async () => { successCalls += 1; },
  });
  assert.deepEqual(invalid, {
    ok: false,
    error: "Restore returned an invalid response.",
    retryHref: null,
  });
  assert.equal(successCalls, 1);
});

test("archived React board error routes to workspace Restore only", () => {
  const error = new Error("restore archived project before opening its active board");
  error.status = 409;
  const markup = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999", data: null, error, loading: false,
  }));
  assert.match(markup, /Archived project/);
  assert.match(markup, /href="\/projects\/demo-999"/);
  assert.doesNotMatch(markup, /href="\/projects\/demo-999\/board"/);
  assert.doesNotMatch(markup, /Run next|Start queue|Launch/);
});

test("archived Pipeline is restore-first and does not expose active workflow controls", () => {
  const data = boardData();
  data.workspace.project.archived_at = "2099-01-01T00:00:00Z";
  data.workspace.controls = { can_open_board: false, can_restore: true };
  data.workspace.links.restore_href = "/projects/demo-999/restore";
  const markup = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999", surface: "pipeline", data, error: null, loading: false, action: () => {},
  }));
  assert.match(markup, /Restore project/);
  assert.match(markup, /Archived project/);
  assert.doesNotMatch(markup, /Planning Chat|Active Worker Runs|Execution Floor<\/a>/);

  const needsYouMarkup = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999", surface: "needsYou", data, error: null, loading: false, action: () => {},
  }));
  assert.match(needsYouMarkup, /Restore project/);
  assert.match(needsYouMarkup, /Archived project/);
  assert.doesNotMatch(needsYouMarkup, /Needs You|Enter manual estimate/);
});

test("Pipeline makes the next action and one four-bucket ledger primary without duplicating Needs You", async () => {
  const loading = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999", data: null, error: null, loading: true,
  }));
  assert.match(loading, /Loading Pipeline…/);

  const failed = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999", data: null, error: { message: "offline", status: 500 }, loading: false,
  }));
  assert.match(failed, /Could not load board/);
  assert.doesNotMatch(failed, /offline|server-rendered/);
  assert.doesNotMatch(failed, /href="\/projects\/demo-999\/board"/);

  const data = boardData();
  data.tasks_by_status.Estimated[0].launch_failure = {
    retryable: true,
    diagnostic: { text: "Verify the Worker adapter, then retry." },
    error: { text: "Worker returned a nonzero exit." },
    summary: { text: "DEMO launch failure" },
    next_action: { text: "Open Worker Setup." },
  };
  data.tasks_by_status.Running[0].session_href = "/sessions/proxy-demo-999";
  data.tasks_by_status.Done[0].session_href = "/sessions/observed-demo-999";
  let renderer;
  const runProvenance = {
    "/sessions/session-demo-999": {
      adapterId: "opencode",
      trackingMode: "native_usage",
    },
    "/sessions/proxy-demo-999": {
      adapterId: "proxy-adapter",
      trackingMode: "proxy_governed",
    },
    "/sessions/observed-demo-999": {
      adapterId: "observed-adapter",
      trackingMode: "observed_only",
    },
  };
  await act(async () => {
    renderer = create(React.createElement(BoardState, {
      projectId: "demo-999", surface: "pipeline", data, error: null, loading: false, action: () => {}, runProvenance,
    }));
  });
  const pipeline = JSON.stringify(renderer.toJSON());
  for (const text of [
    "Next required action",
    "Review proposed Task Breakdown",
    "Proposed Task Breakdown awaits review.",
    "Review breakdown",
    "Pipeline stages",
    "Project task ledger",
    "Evidence and provenance",
    "Estimated DEMO task",
    "Running DEMO task",
    "Review DEMO task",
    "Done DEMO task",
    "Current launch · CLI: Track native usage after run",
    "opencode · native_usage · Budget-authoritative after run · Session Report",
    "proxy-adapter · proxy_governed · Budget-authoritative during run · Session Report",
    "observed-adapter · observed_only · Not budget-authoritative · Session Report",
    "Needs operator disposition",
    "Last launch failed · retryable",
    "Launch options",
    "Manual token estimate",
    "Approve budget override",
    "Acknowledge native usage overrun risk",
  ]) assert.match(pipeline, new RegExp(text));
  assert.doesNotMatch(pipeline, /Running work|2 slices need refresh/);
  assert.equal((pipeline.match(/View evidence/g) || []).length, 4);
  for (const status of ["estimated", "running", "review", "done"]) {
    assert.match(pipeline, new RegExp(`"id":"task-task-${status}-999"`));
  }
  assert.match(pipeline, /"aria-expanded":false/);
  assert.match(pipeline, /"hidden":true/);
  assert.match(pipeline, /"data-pipeline-stage":"intake"/);
  assert.match(pipeline, /"data-pipeline-stage":"review"/);
  assert.match(pipeline, /"data-pipeline-stage":"acceptance"/);
  assert.doesNotMatch(pipeline, /"data-pipeline-stage":"done"/);
  assert.equal((pipeline.match(/Review proposed Task Breakdown/g) || []).length, 1);
  assert.doesNotMatch(pipeline, /Planning Inbox|DEMO_INTAKE_2099_999\.md/);

  const stage = (id) => renderer.root.findByProps({ "data-pipeline-stage": id });
  const attentionStage = (id) => renderer.root.findAllByType("a").find((link) => link.props["data-pipeline-stage"] === id);
  assert.equal(attentionStage("intake").props.href, "/projects/demo-999/needs-you");
  assert.equal(attentionStage("review").props.href, "/projects/demo-999/needs-you");
  await act(async () => { stage("estimated").props.onClick(); });
  let filtered = JSON.stringify(renderer.toJSON());
  assert.match(filtered, /"data-task-status":"Estimated"/);
  assert.doesNotMatch(filtered, /"data-task-status":"Running"|"data-task-status":"Review"|"data-task-status":"Done"/);
  await act(async () => { stage("running").props.onClick(); });
  filtered = JSON.stringify(renderer.toJSON());
  assert.match(filtered, /"data-task-status":"Running"/);
  assert.doesNotMatch(filtered, /"data-task-status":"Estimated"|"data-task-status":"Review"|"data-task-status":"Done"/);
  await act(async () => { stage("acceptance").props.onClick(); });
  filtered = JSON.stringify(renderer.toJSON());
  assert.match(filtered, /"data-task-status":"Review"/);
  assert.doesNotMatch(filtered, /"data-task-status":"Estimated"|"data-task-status":"Running"|"data-task-status":"Done"/);
  const showAll = renderer.root.findAllByType("button").find((button) => button.props.children === "Show all work");
  await act(async () => { showAll.props.onClick(); });

  const launchOptions = renderer.root.findAllByType("button").find((button) => button.props.children === "Launch options");
  await act(async () => { launchOptions.props.onClick(); });
  const launchDialog = renderer.root.findByProps({ role: "dialog" });
  assert.equal(launchDialog.props.popover, "auto");
  assert.equal(launchDialog.props["aria-hidden"], false);
  await act(async () => { launchDialog.props.onKeyDown({ key: "Escape", preventDefault() {} }); });
  assert.equal(launchOptions.props["aria-expanded"], false);
  await act(async () => { renderer.unmount(); });

  const reportUrls = [];
  const loadedProvenance = await loadBoardRunProvenance(data.tasks_by_status, async (url) => {
    reportUrls.push(url);
    return completedReportData();
  });
  assert.deepEqual(reportUrls.sort(), [
    "/api/sessions/observed-demo-999/report",
    "/api/sessions/proxy-demo-999/report",
    "/api/sessions/session-demo-999/report",
  ]);
  assert.deepEqual(loadedProvenance["/sessions/session-demo-999"], {
    adapterId: "opencode",
    trackingMode: "native_usage",
    retryable: false,
  });
  const cachedProvenance = await loadBoardRunProvenance(
    data.tasks_by_status,
    async () => { throw new Error("cached Session Reports must not refetch"); },
    loadedProvenance,
  );
  assert.deepEqual(cachedProvenance, loadedProvenance);

  let retryAttempts = 0;
  const failedProvenance = await loadBoardRunProvenance(data.tasks_by_status, async () => {
    retryAttempts += 1;
    throw new Error("temporary report failure");
  });
  assert.equal(failedProvenance["/sessions/session-demo-999"].retryable, true);
  const recoveredProvenance = await loadBoardRunProvenance(data.tasks_by_status, async () => {
    retryAttempts += 1;
    return completedReportData();
  }, failedProvenance);
  assert.equal(retryAttempts, 6);
  assert.deepEqual(recoveredProvenance["/sessions/session-demo-999"], {
    adapterId: "opencode",
    trackingMode: "native_usage",
    retryable: false,
  });

  let activeReportLoads = 0;
  let peakReportLoads = 0;
  const boundedTasks = {
    Estimated: [],
    Running: [],
    Review: Array.from({ length: 7 }, (_, index) => ({
      ...data.tasks_by_status.Review[0],
      id: `bounded-task-${index}`,
      session_href: `/sessions/bounded-session-${index}`,
    })),
    Done: [],
  };
  await loadBoardRunProvenance(boundedTasks, async () => {
    activeReportLoads += 1;
    peakReportLoads = Math.max(peakReportLoads, activeReportLoads);
    await new Promise((resolve) => setTimeout(resolve, 0));
    activeReportLoads -= 1;
    return completedReportData();
  });
  assert.equal(peakReportLoads, 3);

  const activeTasks = {
    Estimated: [],
    Running: [],
    Review: [data.tasks_by_status.Review[0]],
    Done: [],
  };
  const activeProvenance = await loadBoardRunProvenance(activeTasks, async () => reportData());
  assert.deepEqual(activeProvenance["/sessions/session-demo-999"], {
    adapterId: "opencode",
    trackingMode: "native_usage",
    retryable: true,
  });
  let activeRetry = 0;
  const settledProvenance = await loadBoardRunProvenance(activeTasks, async () => {
    activeRetry += 1;
    return completedReportData();
  }, activeProvenance);
  assert.equal(activeRetry, 1);
  assert.equal(settledProvenance["/sessions/session-demo-999"].retryable, false);

  const missingReport = completedReportData();
  missingReport.summary.adapter_id = "missing Worker Adapter evidence";
  missingReport.summary.tracking_mode = "missing tracking-mode evidence";
  missingReport.summary.missing_labels = ["missing Worker Run evidence"];
  const missingProvenance = await loadBoardRunProvenance(activeTasks, async () => missingReport);
  assert.deepEqual(missingProvenance["/sessions/session-demo-999"], {
    adapterId: null,
    trackingMode: null,
    retryable: true,
  });

  const cancellation = new AbortController();
  const releases = [];
  let canceledReportLoads = 0;
  const canceledLoad = loadBoardRunProvenance(boundedTasks, async () => {
    canceledReportLoads += 1;
    await new Promise((resolve) => { releases.push(resolve); });
    return completedReportData();
  }, {}, cancellation.signal);
  while (canceledReportLoads < 3) await new Promise((resolve) => setImmediate(resolve));
  cancellation.abort();
  releases.forEach((release) => release());
  await canceledLoad;
  assert.equal(canceledReportLoads, 3);

  const retryableData = boardData();
  retryableData.tasks_by_status.Estimated[0].session_href = "/sessions/failed-demo-999";
  retryableData.tasks_by_status.Estimated[0].launch_failure = data.tasks_by_status.Estimated[0].launch_failure;
  const retryable = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999",
    surface: "pipeline",
    data: retryableData,
    error: null,
    loading: false,
    runProvenance: {
      "/sessions/failed-demo-999": { adapterId: "adapter-a", trackingMode: "native_usage", retryable: false },
    },
  }));
  assert.match(retryable, /adapter-a · native_usage · Budget-authoritative after run · Session Report/);
  assert.doesNotMatch(retryable, /Current launch · CLI: Track native usage after run/);

  const advisoryData = boardData();
  advisoryData.needs_you = { project_id: "demo-999", count: 1, items: [lowConfidenceItem()] };
  const advisory = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999", surface: "pipeline", data: advisoryData, error: null, loading: false,
  }));
  assert.match(advisory, /Running work/);
  assert.doesNotMatch(advisory, /Low confidence estimate/);

  const mixedAttentionData = boardData();
  mixedAttentionData.needs_you.items = [lowConfidenceItem(), mixedAttentionData.needs_you.items[0]];
  const mixedAttention = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999", surface: "pipeline", data: mixedAttentionData, error: null, loading: false,
  }));
  assert.match(mixedAttention, /Review proposed Task Breakdown/);
  assert.doesNotMatch(mixedAttention, /Low confidence estimate/);

  const fragmentData = boardData();
  fragmentData.needs_you.items = [fragmentData.needs_you.items[1]];
  let fragmentRenderer;
  await act(async () => {
    fragmentRenderer = create(React.createElement(BoardState, {
      projectId: "demo-999", surface: "pipeline", data: fragmentData, error: null, loading: false,
    }));
  });
  const fragmentLink = fragmentRenderer.root.findAllByType("a")
    .find((link) => link.props.href === "/projects/demo-999#task-task-estimated-999");
  assert.equal(fragmentLink.props.onClick, undefined);
  await act(async () => { fragmentRenderer.unmount(); });

  assert.deepEqual(launchPopoverPlacement({ top: 700, bottom: 730, left: 900 }, 1100, 900), {
    placement: "above",
    width: 320,
    left: 764,
    top: "auto",
    bottom: "208px",
    maxHeight: 676,
  });
  assert.deepEqual(launchPopoverPlacement({ top: 40, bottom: 70, left: 4 }, 300, 900), {
    placement: "below",
    width: 268,
    left: 16,
    top: "78px",
    bottom: "auto",
    maxHeight: 806,
  });

  const emptyData = boardData();
  emptyData.tasks_by_status = Object.fromEntries(["Estimated", "Running", "Review", "Done"].map((status) => [status, []]));
  const empty = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999", data: emptyData, error: null, loading: false, action: () => {},
  }));
  assert.match(empty, /Add or attach Markdown work|No matching tasks/);

  const textFiltered = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999", data: boardData(), error: null, loading: false,
    query: "no-such-task", action: () => {},
  }));
  assert.match(textFiltered, /0 of 4 visible/);
  assert.match(textFiltered, /No matching tasks/);
});

test("Needs You is a projection-backed route with inline manual estimates", async () => {
  const data = boardData();
  data.needs_you = {
    project_id: "demo-999",
    count: 1,
    items: [{
      id: "task:task-estimated-999:low_confidence_estimate",
      kind: "low_confidence_estimate",
      title: "Low confidence estimate",
      reason: "Enter a manual estimate to clear this advisory decision.",
      actions: [{
        kind: "manual_estimate",
        label: "Enter manual estimate",
        method: "POST",
        href: "/api/projects/demo-999/tasks/task-estimated-999/estimate-decision/manual?estimate_revision=1",
      }],
    }],
  };
  const actions = [];
  let tree;
  await act(async () => {
    tree = create(React.createElement(BoardState, {
      projectId: "demo-999",
      surface: "needsYou",
      data,
      error: null,
      loading: false,
      notice: { message: "Estimate revision changed.", setupHref: null },
      action: (url, body) => actions.push([url, body]),
    }));
  });
  const markup = JSON.stringify(tree.toJSON());
  assert.match(markup, /Needs You/);
  assert.match(markup, /Enter manual estimate/);
  assert.match(markup, /Estimate revision changed/);
  assert.match(markup, /"role":"alert"/);
  assert.doesNotMatch(markup, /Planning Inbox|Filter loaded tasks|Estimated DEMO task/);

  const input = tree.root.findByProps({ placeholder: "tokens" });
  await act(async () => { input.props.onChange({ target: { value: "900" } }); });
  const form = tree.root.findByType("form");
  await act(async () => { form.props.onSubmit({ preventDefault: () => {} }); });
  assert.deepEqual(actions, [[
    "/api/projects/demo-999/tasks/task-estimated-999/estimate-decision/manual?estimate_revision=1",
    JSON.stringify({ estimate_tokens: 900 }),
  ]]);
  await act(async () => { tree.unmount(); });
});

test("Pipeline profile renders typed unavailable and empty states", () => {
  const data = boardData();
  data.workspace.project.root_path = "";
  data.workspace.project.profile = {
    git_branch: null,
    language_hints: [],
    framework_hints: [],
    package_manager_hints: [],
    test_command: null,
    run_command: null,
    relevant_docs: [],
  };
  const markup = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999", surface: "pipeline", data, error: null, loading: false, action: () => {},
  }));
  for (const text of [
    "Repo path unavailable",
    "Branch</dt><dd>unavailable",
    "No language, framework, or package hints detected",
    "Test</dt><dd>unavailable",
    "Run</dt><dd>unavailable",
    "No relevant docs detected",
  ]) assert.match(markup, new RegExp(text));
  assert.doesNotMatch(markup, /undefined|\[object Object\]/);
});

test("Planning pane disclosure survives a board refresh", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (url) => {
    if (url.includes("/planning/start")) {
      return new Response(JSON.stringify({ planning_session_id: "sess-plan-999" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify({ events: [], next_since_id: 0, has_more: false }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };
  const data = boardData();
  let renderer;
  await act(async () => {
    renderer = create(React.createElement(BoardState, {
      projectId: "demo-999", surface: "pipeline", data, error: null, loading: false,
    }));
  });
  const disclosure = () => renderer.root.findByProps({ "aria-controls": "planning-pane-demo-999-pipeline" });
  assert.equal(disclosure().props["aria-expanded"], false);
  await act(async () => { disclosure().props.onClick(); });
  assert.equal(disclosure().props["aria-expanded"], true);

  await act(async () => {
    renderer.update(React.createElement(BoardState, {
      projectId: "demo-999", surface: "pipeline", data, error: null, loading: true,
    }));
  });
  assert.equal(renderer.root.findByProps({ className: "spinner" }).children.join(""), "Loading Pipeline…");
  await act(async () => {
    renderer.update(React.createElement(BoardState, {
      projectId: "demo-999", surface: "pipeline", data, error: null, loading: false,
    }));
  });
  assert.equal(disclosure().props["aria-expanded"], true);
  await act(async () => { renderer.unmount(); });
});

test("Narrow viewport collapses Planning on Pipeline and Floor", async (t) => {
  const originalFetch = globalThis.fetch;
  const originalWindow = globalThis.window;
  t.after(() => {
    globalThis.fetch = originalFetch;
    globalThis.window = originalWindow;
  });
  let mediaListener;
  globalThis.window = {
    matchMedia: () => ({
      matches: false,
      addEventListener: (_type, listener) => { mediaListener = listener; },
      removeEventListener: () => {},
    }),
  };
  globalThis.fetch = async (url) => {
    if (url.includes("/planning/start")) {
      return new Response(JSON.stringify({ planning_session_id: "sess-plan-999" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify({ events: [], next_since_id: 0, has_more: false }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };
  const data = boardData();
  let renderer;
  await act(async () => {
    renderer = create(React.createElement(BoardState, {
      projectId: "demo-999", surface: "floor", data, error: null, loading: false,
    }));
  });
  const floorDisclosure = () => renderer.root.findByProps({ "aria-controls": "planning-pane-demo-999-floor" });
  await act(async () => { floorDisclosure().props.onClick(); });
  assert.equal(floorDisclosure().props["aria-expanded"], true);

  await act(async () => { mediaListener({ matches: true }); });
  assert.equal(floorDisclosure().props["aria-expanded"], false);
  await act(async () => {
    renderer.update(React.createElement(BoardState, {
      projectId: "demo-999", surface: "pipeline", data, error: null, loading: false,
    }));
  });
  const pipelineDisclosure = renderer.root.findByProps({ "aria-controls": "planning-pane-demo-999-pipeline" });
  assert.equal(pipelineDisclosure.props["aria-expanded"], false);
  await act(async () => { renderer.unmount(); });
});

test("Execution Floor renders active runs, Review queue, and recently-finished trail", () => {
  const floor = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999",
    surface: "floor",
    data: boardData(),
    error: null,
    loading: false,
    action: () => {},
  }));
  for (const text of [
    "Execution Floor",
    "Run next",
    "Start queue",
    "Active Worker Runs",
    "Running DEMO task",
    "Refresh",
    "Review queue",
    "Review DEMO task",
    "Needs operator disposition",
    "View evidence",
    "Recently finished",
    "Done DEMO task",
    "Archive",
  ]) assert.match(floor, new RegExp(text));
  assert.match(floor, /class="status-pill status-pill-warning"[\s\S]*?class="status-pill-label">Blocked<\/span>/);
  assert.match(floor, /class="token-comparison finished-token-comparison" aria-label="Estimate versus actual tokens"[\s\S]*?token-stat-estimate[\s\S]*?<small>Estimate<\/small><strong>100<\/strong>[\s\S]*?token-stat-actual[\s\S]*?<small>Actual · −11%<\/small><strong>89<\/strong>/);
  assert.match(floor, /status-pill-glyph[^>]*aria-hidden="true">▮<\/span><span class="status-pill-label">Queue idle<\/span>/);
  assert.match(floor, /aria-expanded="false"/);
  assert.match(floor, />Expand</);
  assert.ok(floor.indexOf("finished-token-comparison") < floor.indexOf("Done DEMO task"));
  assert.doesNotMatch(floor, /Planning Chat|Planning Inbox|Estimated DEMO task|Task details/);
});

test("Planning Chat investigation links prefill bounded Task context", () => {
  const tasks = Object.values(boardData().tasks_by_status).flat();
  assert.equal(
    investigationMessage(tasks, "task-estimated-999"),
    "Investigate Task task-estimated-999 before re-estimation:\nEstimated DEMO task",
  );
  const markup = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999",
    surface: "pipeline",
    data: boardData(),
    error: null,
    loading: false,
    investigateTaskId: "task-estimated-999",
  }));
  assert.match(markup, /aria-expanded="false"/);
  assert.doesNotMatch(markup, /Investigate Task task-estimated-999 before re-estimation|<textarea/);
});

test("Evidence Drawer fetches its Session Report handoff and reuses bounded evidence components", async () => {
  const task = boardData().tasks_by_status.Review[0];
  let requestedUrl = null;
  const loaded = await loadEvidenceDrawer(task, async (url) => {
    requestedUrl = url;
    return reportData();
  });
  assert.equal(requestedUrl, "/api/sessions/session-demo-999/report");
  assert.equal(loaded.session.id, "sess-demo-999");
  assert.equal(await loadEvidenceDrawer({ session_href: "https://example.invalid/session" }), null);

  const drawer = renderToStaticMarkup(React.createElement(EvidenceDrawerState, {
    task,
    projectId: "demo-999",
    data: reportData(),
    error: null,
    loading: false,
    action: () => {},
  }));
  for (const text of [
    "Task evidence",
    "Token log",
    "provider raw usage",
    "Budget-zone timeline",
    "Worker Run timeline",
    "Live Worker Run feed",
    "timeline detail",
    "Repo Context Brief",
    "Alarms",
    "BUDGET_YELLOW",
    "Checkpoint results",
    "checkpoint detail",
    "Agent Review",
    "Agent Review summary",
    "Agent Review findings",
    "Agent Review finding",
    "Full Session Report",
    "Save review prompt",
    "Mark Done",
    "Block",
  ]) assert.match(drawer, new RegExp(text));
  assert.match(drawer, /role="dialog"/);
  assert.match(drawer, /class="status-pill status-pill-warning"[\s\S]*?class="status-pill-label">Blocked<\/span>/);
  assert.match(drawer, /class="live-event live-event-launch event-row"/);
  assert.match(drawer, /Preview truncated/);
});

test("legacy form errors survive the canonical Pipeline redirect", () => {
  assert.deepEqual(boardNoticeFromSearch("?error=DEMO%20launch%20blocked"), {
    message: "DEMO launch blocked",
    setupHref: null,
  });
  assert.equal(boardNoticeFromSearch(""), null);
});

test("board cards derive short names from long task descriptions", () => {
  assert.equal(taskDisplayName({ summary: { text: "# Dashboard card cleanup\nMake every card easier to scan." } }), "Dashboard card cleanup");
  assert.equal(taskDisplayName({ summary: { text: "Please update the dashboard so that card titles read like short names and preserve the full task body." } }), "Update the dashboard");
  assert.equal(taskDisplayName({ summary: { text: "Build and deploy the operator portal" } }), "Build and deploy the operator portal");
  assert.equal(taskDisplayName({ id: "task-demo-999", summary: { text: "" } }), "Task-demo-999");
});

test("React task history sanitizes errors and links back to the canonical Pipeline", () => {
  const loading = renderToStaticMarkup(React.createElement(TaskHistoryState, {
    projectId: "demo-999", data: null, error: null, loading: true, filter: "all",
    onSelectFilter: () => {}, onUnarchive: () => {}, notice: null,
  }));
  assert.match(loading, /Loading task history/);

  const failed = renderToStaticMarkup(React.createElement(TaskHistoryState, {
    projectId: "demo-999", data: null, error: { message: "secret detail", status: 500 }, loading: false,
    filter: "all", onSelectFilter: () => {}, onUnarchive: () => {}, notice: null,
  }));
  assert.match(failed, /Could not load task history/);
  assert.doesNotMatch(failed, /secret detail/);
  assert.doesNotMatch(failed, /server-rendered/);

  const populated = renderToStaticMarkup(React.createElement(TaskHistoryState, {
    projectId: "demo-999",
    data: { filters: [], tasks: [] },
    error: null,
    loading: false,
    filter: "all",
    onSelectFilter: () => {},
    onUnarchive: () => {},
    notice: null,
  }));
  assert.match(populated, /href="\/projects\/demo-999"/);
  assert.match(populated, /Back to Pipeline/);
  assert.doesNotMatch(populated, /href="\/app\/projects\/demo-999\/board"/);
});

test("React task history does not render a Scout label", () => {
  const markup = renderToStaticMarkup(React.createElement(TaskHistoryState, {
    projectId: "demo-999",
    data: { filters: [], tasks: [
      { id: "scout-history-1", description: "Inspect routing", status: "Done", task_kind: "scout", archived: false },
      { id: "blocked-history-1", description: "Await operator input", status: "Blocked", task_kind: "implementation", archived: false },
      { id: "archived-blocked-history-1", description: "Preserve blocked evidence", status: "Estimated", task_kind: "implementation", archived: true, blocked_reason: "Needs operator input", requires_manual_estimate: true },
    ] },
    error: null,
    loading: false,
    filter: "all",
    onSelectFilter: () => {},
    onUnarchive: () => {},
    notice: null,
  }));
  assert.doesNotMatch(markup, /<span[^>]*class="[^"]*pill scout[^"]*"[^>]*>scout<\/span>/);
  assertStatusPillsHaveGlyphs(markup);
  assert.match(markup, /class="status-pill-label">Done<\/span>/);
  assert.match(markup, /class="status-pill status-pill-warning"[\s\S]*?class="status-pill-label">Blocked<\/span>/);
  assert.match(markup, /class="status-pill-label">Estimated<\/span>/);
  assert.match(markup, /class="status-pill-label">Archived<\/span>/);
  assert.match(markup, /Needs operator input/);
  assert.match(markup, /class="status-pill status-pill-warning"><span class="status-pill-glyph" aria-hidden="true">▲<\/span><span class="status-pill-label">Manual estimate required<\/span><\/span>/);
});

test("board action controller negotiates JSON, reloads, reports failures, and navigates", async () => {
  const body = { demo: 999 };
  let reloads = 0;
  let request;
  const notices = [];
  const success = await submitBoardAction({
    url: "/projects/demo-999/run-next",
    body,
    fetchImpl: async (url, options) => {
      request = { url, options };
      return { ok: true, json: async () => ({ ok: true, next_href: null }) };
    },
    navigate: () => assert.fail("successful non-navigation action must not navigate"),
    reload: async () => { reloads += 1; },
    onNotice: (notice) => notices.push(notice),
  });
  assert.equal(success, "reloaded");
  assert.equal(reloads, 1);
  assert.equal(request.url, "/projects/demo-999/run-next");
  assert.equal(request.options.method, "POST");
  assert.equal(request.options.body, body);
  assert.equal(request.options.headers.Accept, "application/json");
  assert.equal(request.options.credentials, "same-origin");
  assert.deepEqual(notices, [null]);

  let destination = null;
  const navigated = await submitBoardAction({
    url: "/api/projects/demo-999/planning/intake",
    body,
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({ ok: true, next_href: "/task-breakdowns/demo-999/review" }),
    }),
    navigate: (href) => { destination = href; },
    reload: async () => assert.fail("navigation outcome must not reload"),
    onNotice: () => {},
  });
  assert.equal(navigated, "navigated");
  assert.equal(destination, "/task-breakdowns/demo-999/review");

  let failureNotice;
  const failed = await submitBoardAction({
    url: "/projects/demo-999/queue/start",
    body,
    fetchImpl: async () => ({
      ok: false,
      json: async () => ({ ok: false, error: "Worker setup required", setup_href: "/settings/workers" }),
    }),
    navigate: () => assert.fail("failure outcome must not navigate"),
    reload: async () => { reloads += 1; },
    onNotice: (notice) => { failureNotice = notice; },
  });
  assert.equal(failed, "failed");
  assert.equal(reloads, 2);
  assert.deepEqual(failureNotice, {
    message: "Worker setup required",
    setupHref: "/settings/workers",
  });
});

test("board status controller merges counts, reloads cards, and retains state on errors", async () => {
  const current = {
    data: {
      project: { id: "demo-999" },
      automation: { counts: { Estimated: 1 }, queue: { status: "idle" }, live_refresh_enabled: true },
    },
    error: null,
    loading: false,
  };
  let updater;
  const mergedResult = await pollBoardStatus({
    getStatus: async () => ({
      counts: { Estimated: 0, Running: 1 },
      queue: { status: "running" },
      has_active_runs: true,
      queue_active: false,
      reload_required: false,
    }),
    reload: async () => assert.fail("summary-only status must not reload cards"),
    update: (callback) => { updater = callback; },
  });
  assert.equal(mergedResult, "merged");
  const merged = updater(current);
  assert.equal(merged.data.project.id, "demo-999");
  assert.deepEqual(merged.data.automation.counts, { Estimated: 0, Running: 1 });
  assert.deepEqual(merged.data.automation.queue, { status: "running" });
  assert.equal(merged.data.automation.live_refresh_enabled, true);
  assert.deepEqual(mergeBoardStatus({ data: null }, { counts: {} }), { data: null });

  let reloads = 0;
  const reloadedResult = await pollBoardStatus({
    getStatus: async () => ({ reload_required: true }),
    reload: async () => { reloads += 1; },
    update: () => assert.fail("reload-required status must not merge stale cards"),
  });
  assert.equal(reloadedResult, "reloaded");
  assert.equal(reloads, 1);

  const retainedResult = await pollBoardStatus({
    getStatus: async () => { throw new Error("offline"); },
    reload: async () => assert.fail("failed polling must retain current state"),
    update: () => assert.fail("failed polling must retain current state"),
  });
  assert.equal(retainedResult, "retained");
});

test("loading and errors do not masquerade as an empty project list", () => {
  const loading = renderSidebar({ data: null, loading: true });
  assert.match(loading, /Loading projects…/);
  assert.doesNotMatch(loading, /No projects/);

  const failed = renderSidebar({ data: null, error: new Error("offline") });
  assert.match(failed, /Could not load projects/);
  assert.match(failed, /href="\/login"/);
  assert.doesNotMatch(failed, /No projects/);
});

test("loaded empty navigation keeps the Project group and a project entry point", () => {
  const markup = renderSidebar();
  assert.match(markup, /No projects/);
  assert.match(markup, /aria-label="Project"/);
  assert.match(markup, /href="\/projects"/);
  assert.doesNotMatch(markup, /href="\/board"/);
});

test("project Pipeline, Needs You, Floor, and Planning active states follow canonical routes", () => {
  const data = {
    portal_auth_required: false,
    sidebar_projects: [{ id: "demo-999", name: "DEMO 999", task_count: 1, needs_you_count: 3 }],
  };
  const pipeline = renderSidebar({
    activeProjectId: "demo-999",
    activeView: "pipeline",
    data,
  });
  assert.match(pipeline, /href="\/projects\/demo-999"[^>]*aria-current="page"/);
  assert.match(pipeline, /href="\/projects\/demo-999\/needs-you"[^>]*aria-label="Needs You, 3 Needs You"/);
  assert.match(pipeline, /href="\/projects\/demo-999\/floor"/);
  assert.doesNotMatch(pipeline, /href="\/app\/projects\/demo-999"/);

  const needsYou = renderSidebar({
    activeProjectId: "demo-999",
    activeView: "needsYou",
    data,
  });
  assert.match(needsYou, /href="\/projects\/demo-999\/needs-you"[^>]*aria-current="page"/);

  const floor = renderSidebar({
    activeProjectId: "demo-999",
    activeView: "floor",
    data,
  });
  assert.match(floor, /href="\/projects\/demo-999\/floor"[^>]*aria-current="page"/);

  const plan = renderSidebar({
    activeProjectId: "demo-999",
    activeView: "planningChat",
    data,
  });
  assert.match(plan, /href="\/projects\/demo-999\/plan"[^>]*aria-current="page"/);
});

test("canonical project routes highlight the project while aliases remain server-owned", () => {
  const route = parseRoute("/projects/demo-999");
  assert.equal(route.view, "pipeline");
  assert.equal(route.projectId, "demo-999");
  for (const path of [
    "/projects/demo-999/board",
    "/app/projects/demo-999",
    "/app/projects/demo-999/board",
    "/app/projects/demo-999/floor",
    "/app/projects/demo-999/plan",
    "/app/projects/demo-999/needs-you",
  ]) {
    assert.equal(parseRoute(path).view, "notFound");
  }
});

test("task-board and logout controls are conditional", () => {
  const withoutTasks = renderSidebar({
    data: {
      portal_auth_required: false,
      sidebar_projects: [{ id: "demo-999", name: "DEMO 999", task_count: 0 }],
    },
  });
  assert.doesNotMatch(withoutTasks, /class="project-board/);
  assert.doesNotMatch(withoutTasks, /action="\/logout"/);

  const authenticated = renderSidebar({
    data: { portal_auth_required: true, sidebar_projects: [] },
  });
  assert.match(authenticated, /action="\/logout"/);
});

function bounded(preview, overrides = {}) {
  return { preview, truncated: false, full_href: null, ...overrides };
}

function page(items = []) {
  return {
    items,
    pagination: { offset: 0, limit: 50, total: items.length, has_more: false, next_href: null },
  };
}

function breakdownReviewData(status = "proposed") {
  const candidate = {
    index: 0,
    accepted_by_default: status === "proposed",
    kind: "implementation",
    execution_mode: "AFK",
    title: bounded("DEMO title 999"),
    objective: bounded("DEMO objective 999"),
    prompt: bounded("DEMO prompt preview 999", { truncated: true, full_href: "/api/task-breakdowns/demo/text/candidate-0-prompt" }),
    acceptance_criteria: bounded("DEMO acceptance 999"),
    proof: bounded("DEMO proof 999"),
    hitl_reason: bounded(""),
    constraints: bounded("DEMO constraint 999"),
    why_this_task_exists: bounded("Exists 999"),
    why_not_smaller: bounded("Not smaller 999"),
    why_not_larger: bounded("Not larger 999"),
    dependencies: bounded("Dependency 999"),
    likely_entry_points: bounded("src/demo.py"),
  };
  return {
    review: {
      id: "breakdown-demo-999", status, decision: "proposed_task_breakdown",
      model: bounded("DEMO-model-999"), session_id: "session-demo-999",
      intake_decision: "needs_breakdown",
      intake_decision_reason: bounded("DEMO intake reason 999"),
      session_href: "/sessions/session-demo-999", rationale: bounded("DEMO rationale 999"),
      source_text: bounded("DEMO source 2099", { truncated: true, full_href: "/api/task-breakdowns/demo/text/source" }),
      failure_type: status === "failed" ? bounded("provider_error") : null,
      failure_message: status === "failed" ? bounded("Safe DEMO failure 999") : null,
      created_task_ids: page(status === "accepted" ? [bounded("task-demo-999")] : []),
    },
    candidates: page(status === "failed" ? [] : [candidate]),
    context: {
      global_contract_summary: bounded("DEMO global contract 999"),
      global_constraints: page([bounded("DEMO global constraint 999")]),
      verification: page([bounded("Run DEMO verification 999")]),
      rejected_items: page([{ text: bounded("Rejected DEMO 999"), reason: bounded("Not a task") }]),
      non_goals: page([bounded("No real data")]),
      recommended_sequence: page([bounded("DEMO title 999")]),
    },
    repo_context: {
      available: true, source: bounded("repo_context_brief"), text_chars: 999,
      documents: page([bounded("AGENTS.md")]), manifests: page([bounded("pyproject.toml")]),
      entrypoints: page([bounded("src/demo.py")]), test_commands: page([bounded("uv run pytest")]),
      tracked_files_sample: page([bounded("tests/demo.py")]),
    },
    controls: {
      can_accept: status === "proposed", can_retry: status === "failed",
      can_create_manual_candidate: status === "failed",
    },
    links: {
      self_href: "/task-breakdowns/breakdown-demo-999/review",
      api_href: "/api/task-breakdowns/breakdown-demo-999/review",
      board_href: "/projects/project-demo-999/board",
      accept_href: status === "proposed" ? "/task-breakdowns/breakdown-demo-999/accept" : null,
      retry_href: status === "failed" ? "/task-breakdowns/breakdown-demo-999/retry" : null,
      manual_href: status === "failed" ? "/task-breakdowns/breakdown-demo-999/manual" : null,
    },
  };
}

function breakdownDraft(data, { overflow = false, total = data.candidates.pagination.total } = {}) {
  const fields = Object.fromEntries(Object.entries(data.candidates.items[0] || {})
    .filter(([, value]) => value && typeof value === "object" && "preview" in value)
    .map(([field, value]) => [field, {
      value: value.preview, loaded: !value.truncated, fullHref: value.full_href,
      touched: false, error: null,
    }]));
  return {
    candidates: data.candidates.items.length ? [{
      index: 0, selected: true, kind: "implementation", executionMode: "AFK",
      kindTouched: false, executionModeTouched: false, fields,
    }] : [],
    candidatePagination: { ...data.candidates.pagination, total, has_more: overflow, next_href: overflow ? "/api/task-breakdowns/demo/evidence/candidates?offset=1&limit=50" : null },
    globalContract: { value: "DEMO global contract 999", loaded: true, touched: false, error: null },
    globalConstraints: { value: "DEMO global constraint 999", loaded: true, touched: false, error: null },
    verification: { value: "Run DEMO verification 999", loaded: true, touched: false, error: null },
  };
}

function renderBreakdown(status, options = {}) {
  const data = breakdownReviewData(status);
  if (options.repoContextAvailable === false) data.repo_context.available = false;
  if (options.acceptanceClaim) {
    data.controls = {
      can_accept: false,
      can_retry: false,
      can_create_manual_candidate: false,
    };
    data.links.accept_href = null;
  }
  return renderToStaticMarkup(React.createElement(TaskBreakdownReviewState, {
    breakdownId: data.review.id,
    data,
    draft: breakdownDraft(data, options),
    loading: false,
    error: null,
    dirty: Boolean(options.dirty),
  }));
}

test("Task Breakdown Review renders proposed parity and bounded edit gates", () => {
  const markup = renderBreakdown("proposed", { dirty: true });
  for (const text of [
    "Task Breakdown Review", "DEMO title 999", "Candidate kind", "Execution mode",
    "Acceptance criteria", "Candidate proof / verification path", "Slicing rationale",
    "Global contract summary", "Rejected as Tasks", "Repo Context Brief",
    "4 context groups",
    "Intake decision", "needs_breakdown", "Intake reason", "DEMO intake reason 999",
    "Accept selected and estimate", "Unsaved browser-local edits",
  ]) assert.match(markup, new RegExp(text));
  assert.match(markup, /Load full text before editing/);
  assert.match(markup, /disabled=""/);
  assert.match(markup, /aria-describedby="[^"]+-disabled-reason"/);
  assert.match(markup, /Complete text must load before this field can be edited\./);
  assert.match(renderBreakdown("proposed", { repoContextAvailable: false }), /3 context groups/);
  assertDisabledControlsHaveReasons(markup);
  assertStatusPillsHaveGlyphs(markup);
  assert.match(markup, /class="status-pill-label">proposed<\/span>/);
});

test("Task Breakdown Review workbench keeps focus, selection, disclosure, and confirmation distinct", async (t) => {
  const originalFetch = globalThis.fetch;
  const originalWindow = globalThis.window;
  const originalActFlag = globalThis.IS_REACT_ACT_ENVIRONMENT;
  t.after(() => {
    globalThis.fetch = originalFetch;
    globalThis.window = originalWindow;
    globalThis.IS_REACT_ACT_ENVIRONMENT = originalActFlag;
  });
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;

  const data = breakdownReviewData("proposed");
  data.review.source_text = bounded("Complete DEMO source 2099");
  data.candidates.items.push({
    ...data.candidates.items[0],
    index: 1,
    accepted_by_default: false,
    title: bounded("DEMO title 2"),
  });
  data.candidates.pagination = { offset: 0, limit: 50, total: 2, has_more: false, next_href: null };
  const posted = [];
  globalThis.window = {
    location: { pathname: data.links.self_href, assign: () => {} },
    confirm: () => true,
    addEventListener: () => {},
    removeEventListener: () => {},
  };
  globalThis.fetch = async (url, options = {}) => {
    if (url === data.links.api_href) return { ok: true, json: async () => data };
    if (options.method === "POST") {
      posted.push({ url, body: Object.fromEntries(options.body.entries()) });
      return { ok: true, json: async () => ({ ok: true, next_href: data.links.board_href }) };
    }
    throw new Error(`Unexpected fetch: ${url}`);
  };

  let renderer;
  await act(async () => { renderer = create(mountedReview(data.review.id)); });
  const navigator = renderer.root.findByProps({ "aria-label": "Candidate navigator" });
  let rows = renderer.root.findAll((node) => node.props["data-candidate-index"] !== undefined);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].props["aria-current"], "true");
  assert.equal(rows[0].props.tabIndex, 0);
  assert.equal(rows[1].props.tabIndex, -1);
  assert.match(rows[0].parent.props.className, /is-disabled/, "unloaded text is visibly disabled");
  assert.match(JSON.stringify(renderer.toJSON()), /Identity|Contract|Proof of done|Slicing rationale/);
  assert.match(JSON.stringify(renderer.toJSON()), /5 rationale fields/);
  assert.match(navigator.props.className, /review-navigator/);

  const keyDown = (key) => ({ key, preventDefault: () => {} });
  await act(async () => { rows[0].props.onKeyDown(keyDown("ArrowDown")); });
  rows = renderer.root.findAll((node) => node.props["data-candidate-index"] !== undefined);
  assert.equal(rows[1].props.tabIndex, 0);
  assert.equal(rows[1].props["aria-current"], "true");
  assert.equal(rows[0].props.tabIndex, -1);

  await act(async () => { rows[1].props.onKeyDown(keyDown("ArrowUp")); });
  rows = renderer.root.findAll((node) => node.props["data-candidate-index"] !== undefined);
  assert.equal(rows[0].props.tabIndex, 0, "ArrowUp moves focus backward");
  await act(async () => { rows[0].props.onKeyDown(keyDown("j")); });
  rows = renderer.root.findAll((node) => node.props["data-candidate-index"] !== undefined);
  assert.equal(rows[1].props.tabIndex, 0, "j moves focus forward");
  await act(async () => { rows[1].props.onKeyDown(keyDown("k")); });
  rows = renderer.root.findAll((node) => node.props["data-candidate-index"] !== undefined);
  assert.equal(rows[0].props.tabIndex, 0, "k moves focus backward");
  await act(async () => { rows[0].props.onKeyDown(keyDown("j")); });
  rows = renderer.root.findAll((node) => node.props["data-candidate-index"] !== undefined);

  await act(async () => { rows[0].props.onKeyDown(keyDown(" ")); });
  let candidates = renderer.root.findAllByType("input").filter((input) => input.props.type === "checkbox");
  assert.deepEqual(candidates.map((input) => input.props.checked), [true, false], "Space ignores an unfocused row");
  await act(async () => { rows[1].props.onKeyDown(keyDown(" ")); });
  candidates = renderer.root.findAllByType("input").filter((input) => input.props.type === "checkbox");
  assert.deepEqual(candidates.map((input) => input.props.checked), [true, true]);
  const editableTitle = renderer.root.findAllByType("input").find((input) => input.props.value === "DEMO title 2");
  assert.equal(editableTitle.props.onKeyDown, undefined, "text editing keeps native arrow-key behavior");

  await act(async () => { rows[1].props.onKeyDown(keyDown("Enter")); });
  assert.equal(renderer.root.findByProps({ "data-slicing-rationale": "1" }).props.open, true);

  await act(async () => { editableTitle.props.onChange({ target: { value: "" } }); });
  rows = renderer.root.findAll((node) => node.props["data-candidate-index"] !== undefined);
  assert.match(rows[1].parent.props.className, /is-edited/, "edited state is distinct from selection");
  assert.match(rows[1].parent.props.className, /is-incomplete/, "blank required fields are visibly incomplete");
  assert.equal(reviewButton(renderer.root, "Accept selected").props.disabled, true);
  assert.match(JSON.stringify(renderer.toJSON()), /Complete required text for 1 selected candidate before acceptance\./);

  await act(async () => { editableTitle.props.onChange({ target: { value: "DEMO title 2" } }); });
  const globalContract = renderer.root.findAllByType("textarea").find((field) => field.props.value === "DEMO global contract 999");
  await act(async () => { globalContract.props.onChange({ target: { value: "" } }); });
  assert.equal(reviewButton(renderer.root, "Accept selected").props.disabled, true);
  assert.match(JSON.stringify(renderer.toJSON()), /Complete the required global contract summary before acceptance\./);
  await act(async () => { globalContract.props.onChange({ target: { value: "DEMO global contract 999" } }); });
  assert.equal(reviewButton(renderer.root, "Accept selected").props.disabled, undefined);

  await act(async () => { reviewButton(renderer.root, "Accept selected").props.onClick(); });
  assert.equal(posted.length, 0, "opening confirmation never mutates");
  let confirmation = renderer.root.findByProps({ role: "dialog" });
  assert.ok(confirmation, "confirmation opens before the acceptance mutation");
  let escapePrevented = false;
  let escapeStopped = false;
  await act(async () => {
    confirmation.props.onKeyDown({
      key: "Escape",
      preventDefault: () => { escapePrevented = true; },
      stopPropagation: () => { escapeStopped = true; },
    });
  });
  assert.equal(escapePrevented, true);
  assert.equal(escapeStopped, true);
  assert.throws(() => renderer.root.findByProps({ role: "dialog" }), "Escape closes the confirmation overlay");

  await act(async () => { reviewButton(renderer.root, "Accept selected").props.onClick(); });
  confirmation = renderer.root.findByProps({ role: "dialog" });
  assert.match(JSON.stringify(renderer.toJSON()), /DEMO title 999|DEMO title 2/);
  await act(async () => { reviewButton(renderer.root, "Accept and estimate").props.onClick(); });
  assert.deepEqual(posted, [{
    url: data.links.accept_href,
    body: {
      accept_0: "1",
      accept_1: "1",
      title_1: "DEMO title 2",
      global_contract_summary: "DEMO global contract 999",
    },
  }]);
  await act(async () => { renderer.unmount(); });
});

test("Task Breakdown Review renders failed recovery, accepted evidence, and overflow gate", () => {
  const failed = renderBreakdown("failed");
  assert.match(failed, /Breakdown failed/);
  assert.match(failed, /Retry breakdown/);
  assert.match(failed, /Create manual candidate/);
  assert.match(failed, /Safe DEMO failure 999/);
  assert.match(failed, /Preserved context/);
  assert.match(failed, /Repo Context Brief/);

  const accepted = renderBreakdown("accepted");
  assert.match(accepted, /Accepted review/);
  assert.match(accepted, /task-demo-999/);
  assert.match(accepted, /Accepted candidates/);
  assert.match(accepted, /DEMO title 999/);
  assert.match(accepted, /Global contract summary/);
  assert.match(accepted, /Repo Context Brief/);
  assert.doesNotMatch(accepted, /Accept selected and estimate/);
  assertNoNestedPanels(accepted);

  const overflow = renderBreakdown("proposed", { overflow: true, total: 21 });
  assert.match(overflow, /Load remaining candidates/);
  assert.match(overflow, /Load every candidate before acceptance/);
  assert.match(overflow, /1 of 21 candidates selected\./);
  assert.match(overflow, /Accept selected and estimate<\/button>/);
  assert.match(overflow, /class="disabled-reason"[^>]*>Load every candidate before acceptance\.<\/span>/);
  assertDisabledControlsHaveReasons(overflow);
});

test("Task Breakdown Review renders a proposed acceptance claim read-only", () => {
  const markup = renderBreakdown("proposed", { acceptanceClaim: true });
  assert.match(markup, /Acceptance in progress/);
  assert.match(markup, /controlled operator repair/);
  assert.match(markup, /DEMO title 999/);
  assert.doesNotMatch(markup, /Accept selected and estimate|Candidate kind|Execution mode/);
});

test("rendered Portal surfaces preserve focus, motion, select, and panel contracts", () => {
  const board = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999",
    data: boardData(),
    error: null,
    loading: false,
    action: () => {},
    estimating: true,
  }));
  const review = renderBreakdown("proposed");
  const accepted = renderBreakdown("accepted");
  const floor = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999",
    surface: "floor",
    data: boardData(),
    error: null,
    loading: false,
    action: () => {},
  }));
  const budget = renderToStaticMarkup(React.createElement(BudgetSettingsState, {
    data: {
      daily_cap_tokens: 1000,
      session_cap_tokens: 250,
      current_window_used_tokens: 125,
      current_window_remaining_tokens: 875,
      daily_usage_reset_at: "2099-01-01T00:00:00Z",
      budget_since: "2099-01-01T00:00:00Z",
    },
    error: null,
    loading: false,
    onRefresh: () => {},
  }));

  assert.doesNotMatch(board, /<select[^>]*name="task_kind"/);
  assert.match(board, /Next required action/);
  assert.match(board, /class="data-table pipeline-ledger-table"/);
  assert.match(board, /aria-expanded="false"/);
  assert.doesNotMatch(board, /Describe the task or goal…/);
  assert.match(review, /<select[^>]*>.*?<option value="implementation"[^>]*>/s);
  assert.doesNotMatch(board, /class="board-intake-progress-bar"/);
  assert.match(floor, /class="live-pulse-dot"/);
  assertDisabledControlsHaveReasons(board);
  for (const markup of [board, floor, review, accepted, budget]) assertNoNestedPanels(markup);
});

test("Vite browser computes focus, motion, select, panel, and collapsed rail contracts", { timeout: 30000 }, async () => {
  const browser = browserExecutable();
  assert.ok(browser, "Chromium or Chrome is required for the rendered Ledger contract");
  const profile = mkdtempSync(join(tmpdir(), "foreman-ledger-browser-"));
  try {
    const { stdout } = await execFileAsync(browser, [
      "--headless",
      "--no-sandbox",
      "--disable-gpu",
      "--disable-dev-shm-usage",
      `--user-data-dir=${profile}`,
      "--force-prefers-reduced-motion=reduce",
      "--window-size=1100,900",
      "--virtual-time-budget=5000",
      "--dump-dom",
      `${browserBaseUrl}/static/react/tests/ledger-browser-contract.html`,
    ], { encoding: "utf8", maxBuffer: 2 * 1024 * 1024, timeout: 20000, killSignal: "SIGKILL" });
    assert.match(stdout, /data-ledger-contract="passed"/);
    assert.doesNotMatch(stdout, /data-ledger-contract="failed"|data-contract-error=/);
  } finally {
    rmSync(profile, { recursive: true, force: true });
  }
});

function reviewButton(root, label) {
  return root.findAllByType("button").find((button) => button.children.join("").includes(label));
}

function mountedReview(breakdownId, setGuard = () => {}, navigate = () => true) {
  return React.createElement(
    NavContext.Provider,
    { value: navigate },
    React.createElement(
      NavigationGuardContext.Provider,
      { value: setGuard },
      React.createElement(TaskBreakdownReview, { breakdownId }),
    ),
  );
}

test("Task Breakdown controller pages, loads full text, and installs dirty guards", async (t) => {
  const originalFetch = globalThis.fetch;
  const originalWindow = globalThis.window;
  const originalActFlag = globalThis.IS_REACT_ACT_ENVIRONMENT;
  t.after(() => {
    globalThis.fetch = originalFetch;
    globalThis.window = originalWindow;
    globalThis.IS_REACT_ACT_ENVIRONMENT = originalActFlag;
  });
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  let guard = null;
  let beforeUnload = null;
  const data = breakdownReviewData("proposed");
  data.review.source_text = bounded("DEMO source 2099");
  data.candidates.pagination = {
    offset: 0, limit: 1, total: 2, has_more: true,
    next_href: "/api/task-breakdowns/demo/evidence/candidates?offset=1&limit=1",
  };
  const second = { ...data.candidates.items[0], index: 1, title: bounded("DEMO title 2") };
  globalThis.window = {
    location: { pathname: "/task-breakdowns/breakdown-demo-999/review", assign: () => {} },
    confirm: () => false,
    addEventListener: (name, listener) => { if (name === "beforeunload") beforeUnload = listener; },
    removeEventListener: () => {},
  };
  globalThis.fetch = async (url) => {
    if (url === data.links.api_href) return { ok: true, json: async () => data };
    if (String(url).includes("evidence/candidates")) {
      return { ok: true, json: async () => page([second]) };
    }
    if (String(url).includes("candidate-0-prompt")) {
      return { ok: true, text: async () => "Complete DEMO prompt 999" };
    }
    throw new Error(`Unexpected fetch: ${url}`);
  };

  let renderer;
  await act(async () => { renderer = create(mountedReview(data.review.id, (value) => { guard = value; })); });
  assert.equal(reviewButton(renderer.root, "Accept selected").props.disabled, true);
  await act(async () => { await reviewButton(renderer.root, "Load remaining candidates").props.onClick(); });
  assert.notEqual(reviewButton(renderer.root, "Accept selected").props.disabled, true);
  assert.equal(reviewButton(renderer.root, "Load remaining candidates"), undefined);
  await act(async () => { await reviewButton(renderer.root, "Load full text before editing").props.onClick(); });
  assert(renderer.root.findAllByType("textarea").some((field) => field.props.value === "Complete DEMO prompt 999"));

  const title = renderer.root.findAllByType("input").find((field) => field.props.value === "DEMO title 999");
  await act(async () => { title.props.onChange({ target: { value: "Edited DEMO title 999" } }); });
  assert.equal(typeof guard, "function");
  assert.equal(guard(), false);
  const event = { prevented: false, returnValue: null, preventDefault() { this.prevented = true; } };
  beforeUnload(event);
  assert.equal(event.prevented, true);
  assert.equal(event.returnValue, "");
  await act(async () => { renderer.unmount(); });
});

test("Task Breakdown Retry and Manual refetch authoritative same-state evidence", async (t) => {
  const originalFetch = globalThis.fetch;
  const originalWindow = globalThis.window;
  const originalActFlag = globalThis.IS_REACT_ACT_ENVIRONMENT;
  t.after(() => {
    globalThis.fetch = originalFetch;
    globalThis.window = originalWindow;
    globalThis.IS_REACT_ACT_ENVIRONMENT = originalActFlag;
  });
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  const first = breakdownReviewData("failed");
  const second = breakdownReviewData("failed");
  const recovered = breakdownReviewData("proposed");
  first.review.source_text = bounded("DEMO source 2099");
  second.review.source_text = bounded("DEMO source 2099");
  first.review.failure_message = bounded("Old failure preview", { truncated: true, full_href: "/api/task-breakdowns/demo/text/failure-message" });
  second.review.failure_message = bounded("New failure preview", { truncated: true, full_href: "/api/task-breakdowns/demo/text/failure-message" });
  first.context.non_goals = page([bounded("Old non-goal")]);
  second.context.non_goals = page([bounded("New non-goal")]);
  const reviewPayloads = [first, second, recovered];
  const posted = [];
  const postedBodies = [];
  globalThis.window = {
    location: { pathname: "/task-breakdowns/breakdown-demo-999/review", assign: () => {} },
    confirm: () => true,
    addEventListener: () => {},
    removeEventListener: () => {},
  };
  globalThis.fetch = async (url, options = {}) => {
    if (options.method === "POST") {
      posted.push(url);
      postedBodies.push(Object.fromEntries(options.body.entries()));
      return { ok: true, json: async () => ({ ok: true, next_href: first.links.self_href }) };
    }
    if (url === first.links.api_href) {
      return { ok: true, json: async () => reviewPayloads.shift() };
    }
    if (url === "/api/task-breakdowns/demo/text/failure-message") {
      return { ok: true, text: async () => "Old full failure" };
    }
    throw new Error(`Unexpected fetch: ${url}`);
  };

  let renderer;
  await act(async () => { renderer = create(mountedReview(first.review.id)); });
  const fullTextButtons = renderer.root.findAllByType("button").filter((button) => button.children.join("").includes("Load full text"));
  await act(async () => { await fullTextButtons.at(-1).props.onClick(); });
  assert.match(JSON.stringify(renderer.toJSON()), /Old full failure/);

  await act(async () => { await reviewButton(renderer.root, "Retry breakdown").props.onClick(); });
  const retried = JSON.stringify(renderer.toJSON());
  assert.match(retried, /New failure preview/);
  assert.match(retried, /New non-goal/);
  assert.doesNotMatch(retried, /Old full failure|Old non-goal/);

  await act(async () => { await reviewButton(renderer.root, "Create manual candidate").props.onClick(); });
  assert.match(JSON.stringify(renderer.toJSON()), /Accept selected and estimate/);
  assert.deepEqual(posted, [first.links.retry_href, first.links.manual_href]);
  assert.deepEqual(postedBodies, [{}, {}]);
  await act(async () => { renderer.unmount(); });
});

test("dirty Retry confirms, single-flights, and follows accepted replay navigation", async (t) => {
  const originalFetch = globalThis.fetch;
  const originalWindow = globalThis.window;
  const originalActFlag = globalThis.IS_REACT_ACT_ENVIRONMENT;
  t.after(() => {
    globalThis.fetch = originalFetch;
    globalThis.window = originalWindow;
    globalThis.IS_REACT_ACT_ENVIRONMENT = originalActFlag;
  });
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  const failed = breakdownReviewData("failed");
  failed.review.source_text = bounded("Complete DEMO source 2099");
  let allowRetry = false;
  let confirmations = 0;
  let postCount = 0;
  let resolvePost;
  const postResponse = new Promise((resolve) => { resolvePost = resolve; });
  const navigated = [];
  globalThis.window = {
    location: { pathname: failed.links.self_href, assign: (path) => navigated.push(path) },
    confirm: () => { confirmations += 1; return allowRetry; },
    addEventListener: () => {},
    removeEventListener: () => {},
  };
  globalThis.fetch = async (url, options = {}) => {
    if (options.method === "POST") {
      postCount += 1;
      return postResponse;
    }
    if (url === failed.links.api_href) return { ok: true, json: async () => failed };
    throw new Error(`Unexpected fetch: ${url}`);
  };

  let renderer;
  await act(async () => {
    renderer = create(mountedReview(failed.review.id, () => {}, (path) => navigated.push(path)));
  });
  const manualTitle = renderer.root.findAllByType("input").find((field) => field.props.value === "Manual task from source");
  await act(async () => { manualTitle.props.onChange({ target: { value: "Edited DEMO manual 999" } }); });
  await act(async () => { await reviewButton(renderer.root, "Retry breakdown").props.onClick(); });
  assert.equal(postCount, 0);

  allowRetry = true;
  let first;
  await act(async () => {
    first = reviewButton(renderer.root, "Retry breakdown").props.onClick();
    reviewButton(renderer.root, "Retry breakdown").props.onClick();
    resolvePost({
      ok: true,
      json: async () => ({ ok: true, status: "accepted", next_href: failed.links.board_href }),
    });
    await first;
  });
  assert.equal(postCount, 1);
  assert.equal(confirmations, 2);
  assert.deepEqual(navigated, [failed.links.board_href]);
  await act(async () => { renderer.unmount(); });
});

test("Task Breakdown action controller negotiates exact JSON and preserves safe failures", async () => {
  let request;
  const success = await submitBreakdownAction({
    url: "/task-breakdowns/demo/accept",
    body: new URLSearchParams({ accept_0: "1" }),
    fetchImpl: async (url, options) => {
      request = { url, options };
      return { ok: true, json: async () => ({ ok: true, next_href: "/projects/demo/board" }) };
    },
  });
  assert.equal(success.ok, true);
  assert.equal(request.options.method, "POST");
  assert.equal(request.options.headers.Accept, "application/json");
  assert.equal(request.options.credentials, "same-origin");

  const failure = await submitBreakdownAction({
    url: "/task-breakdowns/demo/retry",
    body: new URLSearchParams(),
    fetchImpl: async () => ({ ok: false, json: async () => ({
      ok: false, error: "Safe validation failure", retry_href: "/task-breakdowns/demo/review",
    }) }),
  });
  assert.deepEqual(failure, {
    ok: false, error: "Safe validation failure", retryHref: "/task-breakdowns/demo/review",
  });
});

test("Task Breakdown Accept omits loaded-only redacted values and submits actual edits", () => {
  const data = breakdownReviewData("proposed");
  const draft = breakdownDraft(data);
  draft.candidates[0].fields.prompt = {
    value: "complete [REDACTED] prompt 999", loaded: true, touched: false, fullHref: null, error: null,
  };
  const loadOnly = buildAcceptForm(draft);
  assert.equal(loadOnly.get("accept_0"), "1");
  assert.equal(loadOnly.has("prompt_0"), false);

  draft.candidates[0].fields.prompt.touched = true;
  draft.candidates[0].fields.prompt.value = "operator-edited [REDACTED] prompt 999";
  const edited = buildAcceptForm(draft);
  assert.equal(edited.get("prompt_0"), "operator-edited [REDACTED] prompt 999");
});

test("Task Breakdown Review distinguishes loading, safe error, and empty states", () => {
  const loading = renderToStaticMarkup(React.createElement(TaskBreakdownReviewState, {
    breakdownId: "breakdown-demo-999", data: null, draft: null, loading: true, error: null,
  }));
  assert.match(loading, /Loading Task Breakdown Review/);

  const failedLoad = renderToStaticMarkup(React.createElement(TaskBreakdownReviewState, {
    breakdownId: "breakdown-demo-999", data: null, draft: null, loading: false, error: new Error("secret detail"),
  }));
  assert.match(failedLoad, /Could not load Task Breakdown Review/);
  assert.match(failedLoad, /Retry review/);
  assert.doesNotMatch(failedLoad, /secret detail|server-rendered/);

  const empty = renderToStaticMarkup(React.createElement(TaskBreakdownReviewState, {
    breakdownId: "breakdown-demo-999", data: null, draft: null, loading: false, error: null,
  }));
  assert.match(empty, /No Task Breakdown Review state available/);
});

test("Task Breakdown Review is exact-route owned without swallowing suffixes", () => {
  assert.deepEqual(parseRoute("/task-breakdowns/breakdown-demo-999/review"), {
    view: "taskBreakdownReview", breakdownId: "breakdown-demo-999",
  });
  assert.equal(parseRoute("/task-breakdowns/breakdown-demo-999/review/extra").view, "notFound");
  assert.equal(parseRoute("/app/task-breakdowns/breakdown-demo-999/review").view, "notFound");
});

test("Task Breakdown Review preserves project context for canonical and legacy Pipeline links", () => {
  assert.equal(projectIdFromBoardHref("/projects/demo-999"), "demo-999");
  assert.equal(projectIdFromBoardHref("/projects/demo-999/board"), "demo-999");
  assert.equal(projectIdFromBoardHref("/projects/demo-999/floor"), null);
  assert.equal(projectIdFromBoardHref("/projects/demo-999/board/extra"), null);
});

// A failed JSON handoff carries text nobody wrote for an operator: an exception
// detail, a proxy's HTML error page, or `Internal Server Error`. It must never be
// rendered. A negotiated action outcome is the opposite -- the backend authors and
// sanitizes that text for the operator -- so this only exercises the load-error
// branch, and the action paths that surface `outcome.error` stay legal.
test("no view renders backend text when its handoff fails", () => {
  const sentinel = "SENTINEL_BACKEND_DETAIL_2099";
  const views = () => [
    ["Dashboard", DashboardState],
    ["Projects", ProjectsState],
    ["Board", BoardState],
    ["Workspace", WorkspaceState],
    ["Sessions", SessionsState],
    ["SessionReport", SessionReportState],
    ["Setup", SetupState],
    ["Alarms", AlarmsState],
    ["TaskHistory", TaskHistoryState],
    ["BudgetSettings", BudgetSettingsState],
    ["WorkerSettings", WorkerSettingsState],
    ["ControlPlaneSettings", ControlPlaneSettingsState],
    ["ProjectSettings", ProjectSettingsState],
  ];

  for (const status of [500, 401]) {
    const error = new Error(`${sentinel} raised at /srv/internal/path`);
    error.status = status;
    for (const [name, Component] of views()) {
      const markup = renderToStaticMarkup(
        React.createElement(Component, {
          data: null,
          error,
          loading: false,
          projectId: "demo-999",
          sessionId: "sess-demo-999",
          breakdownId: "breakdown-demo-999",
          onRefresh: () => {},
        }),
      );
      assert.ok(
        !markup.includes(sentinel),
        `${name} rendered backend error text on a ${status} load failure`,
      );
    }
  }
});

test("Settings views show a fixed message when their handoff fails", () => {
  const cases = [
    ["BudgetSettings", () => BudgetSettingsState, /Could not load budget settings\. Retry\./, /Budget settings require sign-in\./],
    ["WorkerSettings", () => WorkerSettingsState, /Could not load worker adapters\. Retry\./, /Worker adapters require sign-in\./],
    ["ControlPlaneSettings", () => ControlPlaneSettingsState, /Could not load orchestrator settings\. Retry\./, /Orchestrator settings require sign-in\./],
    ["ProjectSettings", () => ProjectSettingsState, /Could not load project settings\. Retry\./, /Project settings require sign-in\./],
    ["Alarms", () => AlarmsState, /Could not load Alarms\. Retry\./, /Alarms require sign-in\./],
  ];

  for (const [name, get, failMessage, authMessage] of cases) {
    const render = (status) =>
      renderToStaticMarkup(
        React.createElement(get(), {
          data: null,
          error: Object.assign(new Error("psycopg2.OperationalError at /srv/app"), { status }),
          loading: false,
          filter: "open",
          onFilter: () => {},
          onRefresh: () => {},
          retry: () => {},
        }),
      );

    assert.match(render(500), failMessage, `${name} 500`);
    assert.match(render(401), authMessage, `${name} 401`);
  }
});

// Mirrors the /api/settings/control-plane handoff in routes/react_shell.py: the
// dropdown is pi's discovered inventory, never a harness-authored list.
function controlPlaneData(overrides = {}) {
  return {
    model: "anthropic/claude-sonnet-5",
    configured: true,
    inventory: {
      models: ["anthropic/claude-sonnet-5", "openai-codex/gpt-5.4"],
      discovered_at: "2099-01-01T00:00:00+00:00",
      state: "ready",
      needs_authentication: false,
      reasons: [],
    },
    verification: {
      passed: true,
      verified_at: "2099-01-01T00:00:00+00:00",
      model: "anthropic/claude-sonnet-5",
      stale: false,
      reasons: [],
    },
    diverging_jobs: {},
    shadowed_settings: {},
    connection_status: { state: "online", checked_at: null, details: null },
    ...overrides,
  };
}

test("ControlPlaneSettings renders untested connections as attention statuses", async () => {
  let renderer;
  await act(async () => {
    renderer = create(React.createElement(ControlPlaneSettingsState, {
      data: controlPlaneData({
        connection_status: { state: "needs_test", checked_at: null, details: null },
      }),
      error: null,
      loading: false,
      onRefresh: () => {},
    }));
  });
  const markup = JSON.stringify(renderer.toJSON());
  const label = renderer.root.findByProps({ className: "status-pill-label" });
  assert.equal(label.children.join(""), "needs test");
  assert.equal(label.parent.props.className, "status-pill status-pill-warning");
  assert.ok(label.parent.findByProps({ className: "status-pill-glyph" }).children.join(""));
  assert.match(markup, /needs test/);
  await act(async () => { renderer.unmount(); });
});

test("ControlPlaneSettings offers only inventory models and saves the qualified id", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  let posted = null;
  globalThis.fetch = async (url, options) => {
    posted = { url, body: JSON.parse(options.body) };
    return { ok: true, json: async () => ({ ok: true }) };
  };

  let renderer;
  await act(async () => {
    renderer = create(
      React.createElement(ControlPlaneSettingsState, {
        data: controlPlaneData(), error: null, loading: false, onRefresh: () => {},
      }),
    );
  });

  const select = renderer.root.findByProps({ id: "orchestrator-model" });
  const offered = select.props.children[1].map((option) => option.props.value);
  assert.deepEqual(offered, ["anthropic/claude-sonnet-5", "openai-codex/gpt-5.4"]);
  // No provider, base URL, or API key field survives on this surface.
  assert.throws(() => renderer.root.findByProps({ id: "control-plane-provider" }));
  assert.throws(() => renderer.root.findByProps({ id: "control-plane-base-url" }));
  assert.throws(() => renderer.root.findByProps({ id: "control-plane-api-key-env" }));

  const form = renderer.root.findByProps({ className: "control-plane-form" });
  await act(async () => { await form.props.onSubmit({ preventDefault: () => {} }); });
  assert.equal(posted.url, "/settings/control-plane");
  assert.equal(posted.body.control_plane_model, "anthropic/claude-sonnet-5");
  assert.deepEqual(Object.keys(posted.body), ["control_plane_model"]);
  await act(async () => { renderer.unmount(); });
});

test("ControlPlaneSettings shows the authenticate-with-pi state instead of an empty dropdown", async () => {
  let renderer;
  await act(async () => {
    renderer = create(
      React.createElement(ControlPlaneSettingsState, {
        data: controlPlaneData({
          model: null,
          configured: false,
          inventory: { models: [], discovered_at: null, state: "needs_authentication", needs_authentication: true, reasons: [] },
        }),
        error: null, loading: false, onRefresh: () => {},
      }),
    );
  });
  const markup = JSON.stringify(renderer.toJSON());
  assert.match(markup, /pi \/login/);
  assert.throws(() => renderer.root.findByProps({ id: "orchestrator-model" }));
  await act(async () => { renderer.unmount(); });
});

test("ControlPlaneSettings surfaces stale verification and diverging per-job models", async () => {
  let renderer;
  await act(async () => {
    renderer = create(
      React.createElement(ControlPlaneSettingsState, {
        data: controlPlaneData({
          verification: {
            passed: true,
            verified_at: "2099-01-01T00:00:00+00:00",
            model: "openai-codex/gpt-5.4",
            stale: true,
            reasons: [],
          },
          diverging_jobs: { estimator_model: "openai-codex/gpt-5.4" },
        }),
        error: null, loading: false, onRefresh: () => {},
      }),
    );
  });
  const markup = JSON.stringify(renderer.toJSON());
  assert.match(markup, /Verify again/);
  assert.match(markup, /estimator_model = openai-codex\/gpt-5\.4/);
  assert.match(markup, /ignored legacy settings do not select runtime models/);
  assert.match(markup, /Saving the Orchestrator Model removes them/);
  assert.doesNotMatch(markup, /pinned to a different model/);
  await act(async () => { renderer.unmount(); });
});

test("ControlPlaneSettings blocks Verify until a model is configured", async () => {
  let renderer;
  await act(async () => {
    renderer = create(
      React.createElement(ControlPlaneSettingsState, {
        data: controlPlaneData({ model: null, configured: false }),
        error: null, loading: false, onRefresh: () => {},
      }),
    );
  });
  const verify = renderer.root
    .findAllByType("button")
    .find((b) => b.props.children === "Verify");
  assert.equal(verify.props.disabled, true);
  const markup = JSON.stringify(renderer.toJSON());
  assert.match(markup, /Orchestrator is not configured/);
  await act(async () => { renderer.unmount(); });
});

test("the not-found branch routes to a canonical URL", async () => {
  const { default: App } = await server.ssrLoadModule("/src/App.jsx");
  assert.equal(parseRoute("/nonsense-route-2099").view, "notFound");
  const source = readFileSync(new URL("../src/App.jsx", import.meta.url), "utf8");
  // The /app alias becomes a redirect at Jinja retirement, so nothing in-shell
  // may target it.
  assert.match(source, /This React Portal route does not exist\./);
  assert.doesNotMatch(source, /href="\/app"/);
  assert.ok(App);
});

// The mirror of the load-error rule. A negotiated outcome's `error` is text the
// backend wrote for the operator and sanitized server-side; replacing it with a
// fixed string would delete the guidance, not protect anyone.
test("a negotiated action outcome still surfaces the backend's authored message", async () => {
  const authored = "Local Runner backend is disabled. Run foremanctl init, then foremanctl serve.";
  const blocked = await submitProjectRestore({
    url: "/projects/demo-999/restore",
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({
        ok: false,
        error: authored,
        next_href: null,
        retry_href: null,
        project: null,
      }),
    }),
    onSuccess: async () => { throw new Error("must not refetch after a failed outcome"); },
  });

  assert.equal(blocked.ok, false);
  assert.equal(blocked.error, authored);
});

function scoutBoardData(overrides = {}) {
  const data = boardData();
  return {
    ...data,
    needs_you: {
      project_id: "demo-999",
      count: 1,
      items: [],
    },
    tasks_by_status: {
      ...data.tasks_by_status,
      Estimated: data.tasks_by_status.Estimated.map((task) =>
        task.id === "task-estimated-999" ? { ...task, task_kind: "scout" } : task
      ),
    },
    ...overrides,
  };
}

function lowConfidenceItem(overrides = {}) {
  return {
    id: "task:task-estimated-999:low_confidence_estimate",
    kind: "low_confidence_estimate",
    title: "Low confidence estimate",
    reason: "Automatic estimate confidence is low.",
    task_id: "task-estimated-999",
    task_kind: "implementation",
    advisory: true,
    confidence: 0.5,
    href: "/projects/demo-999/plan?question=low%20confidence%20estimate&task_id=task-estimated-999",
    action_label: "Investigate in chat",
    ...overrides,
  };
}

test("TaskCard does not render a Scout kind label", () => {
  const data = boardData();
  data.tasks_by_status.Estimated[0].task_kind = "scout";
  const markup = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999",
    surface: "pipeline",
    data,
    error: null,
    loading: false,
    action: () => {},
  }));
  assert.doesNotMatch(markup, /<span[^>]*class="[^"]*pill scout[^"]*"[^>]*>scout<\/span>/);
});

test("TaskCard renders an acceptance_verification kind label", () => {
  const data = boardData();
  data.tasks_by_status.Estimated[0].task_kind = "acceptance_verification";
  const markup = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999",
    surface: "pipeline",
    data,
    error: null,
    loading: false,
    action: () => {},
  }));
  assert.match(markup, /<span[^>]*class="[^"]*pill[^"]*"[^>]*>acceptance_verification<\/span>/);
});

test("Needs You renders the investigate-in-chat low-confidence choice", () => {
  const data = boardData();
  data.needs_you = { project_id: "demo-999", count: 1, items: [lowConfidenceItem()] };
  const markup = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999",
    surface: "needsYou",
    data,
    error: null,
    loading: false,
    action: () => {},
  }));
  assert.match(markup, /Investigate in chat/);
  assert.match(markup, /href="\/projects\/demo-999\/plan\?question/);
});
