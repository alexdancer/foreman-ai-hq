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
const tokensCss = readFileSync(new URL("../src/tokens.css", import.meta.url), "utf8");
const execFileAsync = promisify(execFile);
let server;
let browserBaseUrl;
let Sidebar;
let DashboardState;
let BoardState;
let EvidenceDrawerState;
let loadEvidenceDrawer;
let boardNoticeFromSearch;
let mergeBoardStatus;
let taskDisplayName;
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
let ProofOutcome;

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
  ({ Sidebar } = await server.ssrLoadModule("/src/components/Shell.jsx"));
  ({ DashboardState } = await server.ssrLoadModule("/src/views/Dashboard.jsx"));
  ({ ProjectsState } = await server.ssrLoadModule("/src/views/Projects.jsx"));
  ({
    BoardState,
    boardNoticeFromSearch,
    EvidenceDrawerState,
    loadEvidenceDrawer,
    mergeBoardStatus,
    pollBoardStatus,
    submitBoardAction,
    taskDisplayName,
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
  ({ ProjectSettingsState, ProofOutcome } = await server.ssrLoadModule("/src/views/ProjectSettings.jsx"));
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
      tracking: { mode: "native_usage", label: "CLI: Track native usage after run" },
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
  assert.equal(parseRoute("/projects/demo-999/task-history").view, "taskHistory");
  assert.equal(parseRoute("/app/projects/demo-999/task-history").view, "notFound");
  for (const path of [
    "/app/settings",
    "/app/not-a-migrated-route",
    "/projects/demo-999/board",
    "/app/projects/demo-999",
    "/app/projects/demo-999/board",
    "/app/projects/demo-999/floor",
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

test("sidebar Settings and Open local repo use in-shell links; board and login stay full-page", () => {
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
  assert.equal(byHref["/board"].props.onClick, undefined);
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
  assert.match(populated, /Archived Repo/);
  assert.match(populated, /Archived 2099-01-01T00:00:00Z/);
  assert.match(populated, /href="\/projects\/active-999"/);
  assert.match(populated, /href="\/projects\/archived-999"/);
});

test("Dashboard is the sole active home navigation item", () => {
  const markup = renderSidebar();
  assert.match(markup, /class="active" href="\/app">Dashboard/);
  assert.doesNotMatch(markup, /sidebar-action active/);
});

test("Sessions sidebar and list preserve compact scan, states, and pagination", () => {
  const sidebar = renderSidebar({ activeView: "sessions" });
  assert.match(sidebar, /class="active" href="\/sessions">Sessions/);
  assert.doesNotMatch(sidebar, /class="active" href="\/app">Dashboard/);

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
  assert.match(sidebar, /class="active" href="\/setup">First-run setup/);
  assert.doesNotMatch(sidebar, /class="active" href="\/app">Dashboard/);
  assert.doesNotMatch(sidebar, /class="active" href="\/sessions">Sessions/);
  assert.doesNotMatch(sidebar, /class="active" href="\/settings\//);

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

test("Project proof outcomes use one semantic hue boundary", () => {
  const passed = renderToStaticMarkup(React.createElement(ProofOutcome, {
    passed: true,
    outcome: { launch_guardrails: { reasons: [] } },
  }));
  const blocked = renderToStaticMarkup(React.createElement(ProofOutcome, {
    passed: false,
    outcome: { launch_guardrails: { reasons: ["Complete project setup."] } },
  }));

  assert.match(passed, /class="status-pill status-pill-success"[^>]*>.*Read-only proof launched/s);
  assert.match(blocked, /class="status-pill status-pill-warning"[^>]*>.*Read-only proof blocked/s);
  assert.match(blocked, /Complete project setup\./);
  assert.doesNotMatch(passed + blocked, /class="notice/);
  assertStatusPillsHaveGlyphs(passed);
  assertStatusPillsHaveGlyphs(blocked);
});

test("Alarms sidebar and list render from available_actions and bookmarkable filters", () => {
  const sidebar = renderSidebar({ activeView: "alarms" });
  assert.match(sidebar, /class="active" href="\/alarms">Alarms/);
  assert.doesNotMatch(sidebar, /class="active" href="\/app">Dashboard/);

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
  assert.doesNotMatch(markup, /Short task intake|Active Worker Runs|Execution Floor<\/a>/);
});

test("Pipeline renders project readiness, Needs You, planning, intake, and Estimated work only", () => {
  const loading = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999", data: null, error: null, loading: true,
  }));
  assert.match(loading, /Loading Pipeline…/);

  const failed = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999", data: null, error: { message: "offline", status: 500 }, loading: false,
  }));
  assert.match(failed, /Could not load board/);
  assert.doesNotMatch(failed, /offline/);
  assert.doesNotMatch(failed, /server-rendered/);
  assert.doesNotMatch(failed, /href="\/projects\/demo-999\/board"/);

  const pipeline = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999",
    surface: "pipeline",
    data: boardData(),
    error: null,
    loading: false,
    query: "",
    notice: null,
    action: () => {},
  }));
  for (const text of [
    "Pipeline",
    "Connected repo",
    "/DEMO/2099/repo",
    "Repo profile",
    "Branch</dt><dd>implementation/demo-999",
    "Stack</dt><dd>Python · JavaScript · FastAPI · React · uv · npm",
    "Test</dt><dd>uv run pytest",
    "Run</dt><dd>uv run foremanctl serve",
    "Docs</dt><dd>README.md, CONTEXT.md",
    "Sessions",
    "Worker Setup",
    "Project Settings",
    "launch ready",
    "Needs You",
    "Review proposed Task Breakdown",
    "DEMO_INTAKE_2099_999.md · 1 candidate",
    "Planning Inbox",
    "Short task intake",
    "Filter loaded tasks",
    "Codex",
    "gpt-5.4",
    "Approve budget override",
    "Acknowledge native usage overrun risk",
    "Dismiss",
    "Estimate 100",
    "Manual estimate required",
    "Manual token estimate",
  ]) {
    assert.match(pipeline, new RegExp(text));
  }
  assert.match(pipeline, /status-pill-glyph[^>]*aria-hidden="true">✓<\/span><span class="status-pill-label">launch ready<\/span>/);
  assert.match(pipeline, /status-pill-glyph[^>]*aria-hidden="true">▲<\/span><span class="status-pill-label">proposed<\/span>/);
  assert.match(pipeline, /type="file"/);
  assert.match(pipeline, /type="number"/);
  assert.match(pipeline, /type="checkbox"/);
  assert.doesNotMatch(pipeline, /Active Worker Runs|Review queue|Recently finished|Server board/);

  const emptyData = boardData();
  emptyData.tasks_by_status.Estimated = [];
  const empty = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999", data: emptyData, error: null, loading: false, action: () => {},
  }));
  assert.match(empty, /No Estimated tasks/);

  const filtered = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999", data: boardData(), error: null, loading: false,
    query: "no-such-task", action: () => {},
  }));
  assert.match(filtered, /0 of 4 visible/);
  assert.match(filtered, /No matching tasks/);
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
  assert.match(floor, /class="token-comparison finished-token-comparison" aria-label="Estimate versus actual tokens"[\s\S]*?token-stat-estimate[\s\S]*?<small>Estimate<\/small><strong>100<\/strong>[\s\S]*?token-stat-actual[\s\S]*?<small>Actual · −11%<\/small><strong>89<\/strong>/);
  assert.match(floor, /status-pill-glyph[^>]*aria-hidden="true">▮<\/span><span class="status-pill-label">Queue idle<\/span>/);
  assert.ok(floor.indexOf("finished-token-comparison") < floor.indexOf("Done DEMO task"));
  assert.doesNotMatch(floor, /Short task intake|Planning Inbox|Estimated DEMO task|Task details/);
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

test("board intake shows progress while task estimation is running", () => {
  const idle = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999", data: boardData(), error: null, loading: false, action: () => {},
  }));
  assert.match(idle, /Estimate task/);
  assert.doesNotMatch(idle, /Estimating…/);
  assert.doesNotMatch(idle, /role="progressbar"/);

  const busy = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999", data: boardData(), error: null, loading: false, action: () => {}, estimating: true,
  }));
  assert.match(busy, /Estimating…/);
  assert.match(busy, /Preparing Task Breakdown Review/);
  assert.match(busy, /Estimating and breaking down the task/);
  assert.match(busy, /role="progressbar"/);
  assert.match(busy, /aria-valuetext="Estimating task and preparing review"/);
  assert.match(busy, /aria-busy="true"/);
  assert.equal((busy.match(/aria-describedby="board-estimating-reason"/g) || []).length, 3);
  assert.match(busy, /Task estimation is already in progress\./);
  assert.match(busy, /disabled=""/);
  assertDisabledControlsHaveReasons(busy);
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

test("React task history renders a visible Scout label", () => {
  const markup = renderToStaticMarkup(React.createElement(TaskHistoryState, {
    projectId: "demo-999",
    data: { filters: [], tasks: [{ id: "scout-history-1", description: "Inspect routing", status: "Done", task_kind: "scout", archived: false }] },
    error: null,
    loading: false,
    filter: "all",
    onSelectFilter: () => {},
    onUnarchive: () => {},
    notice: null,
  }));
  assert.match(markup, /<span[^>]*class="[^"]*pill scout[^"]*"[^>]*>scout<\/span>/);
  assertStatusPillsHaveGlyphs(markup);
  assert.match(markup, /class="status-pill-label">Done<\/span>/);
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
    url: "/projects/demo-999/tasks/estimate-form",
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
  assert.match(loading, /Loading…/);
  assert.doesNotMatch(loading, /No projects/);
  assert.doesNotMatch(loading, />Planning</);

  const failed = renderSidebar({ data: null, error: new Error("offline") });
  assert.match(failed, /Could not load projects/);
  assert.match(failed, /href="\/login"/);
  assert.doesNotMatch(failed, /No projects/);
  assert.doesNotMatch(failed, />Planning</);
});

test("loaded empty navigation shows the empty state and Planning", () => {
  const markup = renderSidebar();
  assert.match(markup, /No projects/);
  assert.match(markup, />Planning</);
  assert.match(markup, /href="\/board"/);
});

test("project Pipeline and Floor active states follow the selected route", () => {
  const data = {
    portal_auth_required: false,
    sidebar_projects: [{ id: "demo-999", name: "DEMO 999", task_count: 1, needs_you_count: 3 }],
  };
  const workspace = renderSidebar({
    activeProjectId: "demo-999",
    activeView: "pipeline",
    data,
  });
  assert.match(workspace, /class="project-item active"/);
  assert.match(workspace, /class="project-board active" href="\/projects\/demo-999#needs-you"/);
  assert.match(workspace, /class="nav-badge">3<\/span>/);
  assert.match(workspace, /href="\/projects\/demo-999"/);
  assert.match(workspace, /href="\/projects\/demo-999\/floor"/);
  assert.doesNotMatch(workspace, /href="\/app\/projects\/demo-999"/);

  const floor = renderSidebar({
    activeProjectId: "demo-999",
    activeView: "floor",
    data,
  });
  assert.match(floor, /class="project-item active"/);
  assert.match(floor, /class="project-board active" href="\/projects\/demo-999\/floor"/);
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

function breakdownDraft(data, { overflow = false } = {}) {
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
    candidatePagination: { ...data.candidates.pagination, has_more: overflow, next_href: overflow ? "/api/task-breakdowns/demo/evidence/candidates?offset=1&limit=50" : null },
    globalContract: { value: "DEMO global contract 999", loaded: true, touched: false, error: null },
    globalConstraints: { value: "DEMO global constraint 999", loaded: true, touched: false, error: null },
    verification: { value: "Run DEMO verification 999", loaded: true, touched: false, error: null },
  };
}

function renderBreakdown(status, options = {}) {
  const data = breakdownReviewData(status);
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
    "Acceptance criteria", "Candidate proof / verification path", "Task slicing evidence",
    "Global contract summary", "Rejected as Tasks", "Repo Context Brief",
    "Accept selected and estimate", "Unsaved browser-local edits",
  ]) assert.match(markup, new RegExp(text));
  assert.match(markup, /Load full text before editing/);
  assert.match(markup, /disabled=""/);
  assert.match(markup, /aria-describedby="[^"]+-disabled-reason"/);
  assert.match(markup, /Complete text must load before this field can be edited\./);
  assertDisabledControlsHaveReasons(markup);
  assertStatusPillsHaveGlyphs(markup);
  assert.match(markup, /class="status-pill-label">proposed<\/span>/);
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

  const overflow = renderBreakdown("proposed", { overflow: true });
  assert.match(overflow, /Load remaining candidates/);
  assert.match(overflow, /Load every candidate before acceptance/);
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

  assert.match(board, /<select[^>]*name="task_kind"/);
  assert.match(review, /<select[^>]*>.*?<option value="implementation"[^>]*>/s);
  assert.match(board, /class="board-intake-progress-bar"/);
  assert.match(floor, /class="live-pulse-dot"/);
  assert.match(tokensCss, /:where\(a, area\[href\], button, input, select, textarea, summary, \[contenteditable="true"\], \[tabindex\]:not\(\[tabindex="-1"\]\)\):focus-visible\s*\{[^}]*outline: 2px solid var\(--mint\)/s);
  assert.doesNotMatch(tokensCss, /:focus(?:-visible)?[^\{]*\{[^}]*outline:\s*(?:none|0(?:\D|$))/s);
  assert.match(tokensCss, /select\s*\{[^}]*width: 100%;[^}]*max-width: 100%;[^}]*min-width: 0;/s);
  assert.match(tokensCss, /@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.live-pulse-dot\s*\{[^}]*animation: none;[^}]*opacity: 1;/);
  assert.match(tokensCss, /@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.board-intake-progress-bar\s*\{[^}]*transform: none;[^}]*animation: none;/);
  for (const markup of [board, floor, review, accepted, budget]) assertNoNestedPanels(markup);
});

test("Vite browser computes focus, motion, select, and panel contracts", { timeout: 30000 }, async () => {
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
    ["ControlPlaneSettings", () => ControlPlaneSettingsState, /Could not load control-plane settings\. Retry\./, /Control-plane settings require sign-in\./],
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

// Curated models mirror CURATED_CONTROL_PLANE_MODELS in routes/portal.py so the
// dropdown cannot drift between the two surfaces.
function controlPlaneData(overrides = {}) {
  return {
    provider: "anthropic",
    model: "claude-sonnet-4-6",
    base_url: null,
    api_key_env: "TEST_CONTROL_PLANE_KEY",
    api_key_present: true,
    estimator_model: "claude-sonnet-4-6",
    task_breakdown_model: "claude-sonnet-4-6",
    legacy_api_key_configured: false,
    shadowed_settings: {},
    curated_models: [
      { provider: "openai", model: "gpt-5.6-sol", label: "OpenAI · gpt-5.6-sol" },
      { provider: "openai", model: "gpt-5.6-terra", label: "OpenAI · gpt-5.6-terra" },
      { provider: "openai", model: "gpt-5.6-luna", label: "OpenAI · gpt-5.6-luna" },
      { provider: "anthropic", model: "claude-fable-5", label: "Anthropic · Claude Fable 5" },
      { provider: "anthropic", model: "claude-sonnet-5", label: "Anthropic · Claude Sonnet 5" },
      { provider: "anthropic", model: "claude-opus-4-8", label: "Anthropic · Claude Opus 4.8" },
      { provider: "anthropic", model: "claude-haiku-4-5", label: "Anthropic · Claude Haiku 4.5" },
      { provider: "openrouter", model: "anthropic/claude-sonnet-5", label: "OpenRouter · Claude Sonnet 5 (recommended)" },
      { provider: "openrouter", model: "openai/gpt-5.6-terra", label: "OpenRouter · GPT-5.6 Terra (recommended)" },
      { provider: "openrouter", model: "google/gemini-3.5-flash", label: "OpenRouter · Gemini 3.5 Flash (recommended)" },
    ],
    connection_status: { state: "needs_test", checked_at: null, details: null },
    ...overrides,
  };
}

// This is the client-side replacement for the retired Jinja
// <option selected>/hidden/disabled markup: dataToForm() in
// ControlPlaneSettings.jsx now decides "is this model custom" itself, by
// checking whether the stored (provider, model) pair is in curated_models.
// Table-driven over curated cases plus stored model/provider pairs that must
// remain reachable through Custom model.
test("ControlPlaneSettings dataToForm resolves curated vs. custom models by provider+model pair", async () => {
  const cases = [
    {
      name: "a curated model for its own provider renders selected, not custom",
      provider: "anthropic",
      model: "claude-sonnet-5",
      expectCustom: false,
    },
    {
      name: "an openai-compatible model is never curated for any provider",
      provider: "openai-compatible",
      model: "openai-compatible/custom-control-plane-999",
      expectCustom: true,
    },
    {
      name: "a curated model name reused under the wrong provider is custom",
      provider: "openai",
      model: "claude-sonnet-5",
      expectCustom: true,
    },
    {
      name: "a stale provider-prefixed model id is custom",
      provider: "anthropic",
      model: "anthropic/claude-sonnet-4-20250514",
      expectCustom: true,
    },
    {
      name: "a curated OpenRouter model renders selected, not custom",
      provider: "openrouter",
      model: "anthropic/claude-sonnet-5",
      expectCustom: false,
    },
    {
      name: "an uncurated OpenRouter model remains available through Custom model",
      provider: "openrouter",
      model: "meta-llama/custom-demo-999",
      expectCustom: true,
    },
  ];

  for (const testCase of cases) {
    const data = controlPlaneData({ provider: testCase.provider, model: testCase.model });
    let renderer;
    await act(async () => {
      renderer = create(
        React.createElement(ControlPlaneSettingsState, {
          data, error: null, loading: false, onRefresh: () => {},
        }),
      );
    });

    const modelSelect = renderer.root.findByProps({ id: "control-plane-model" });
    if (testCase.expectCustom) {
      assert.equal(modelSelect.props.value, "__custom__", testCase.name);
      const customInput = renderer.root.findByProps({ id: "control-plane-custom-model" });
      assert.equal(customInput.props.value, testCase.model, testCase.name);
    } else {
      assert.equal(modelSelect.props.value, testCase.model, testCase.name);
      assert.throws(
        () => renderer.root.findByProps({ id: "control-plane-custom-model" }),
        testCase.name,
      );
    }

    await act(async () => { renderer.unmount(); });
  }
});

test("ControlPlaneSettings saves an uncurated OpenRouter model ID unchanged", async (t) => {
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
        data: controlPlaneData({
          provider: "openrouter",
          model: "meta-llama/custom-demo-999",
          base_url: "https://openrouter.ai/api/v1",
          api_key_env: "OPENROUTER_API_KEY",
        }),
        error: null,
        loading: false,
        onRefresh: () => {},
      }),
    );
  });

  const form = renderer.root.findByProps({ className: "control-plane-form" });
  await act(async () => { await form.props.onSubmit({ preventDefault: () => {} }); });

  assert.equal(posted.url, "/settings/control-plane");
  assert.equal(posted.body.control_plane_provider, "openrouter");
  assert.equal(posted.body.control_plane_model, "meta-llama/custom-demo-999");
  assert.equal(posted.body.control_plane_base_url, "https://openrouter.ai/api/v1");
  assert.equal(posted.body.control_plane_api_key_env, "OPENROUTER_API_KEY");
  await act(async () => { renderer.unmount(); });
});

test("ControlPlaneSettings renders reported cost and unavailable cost distinctly", async () => {
  for (const [cost, expected] of [[0.0042, "$0.004200"], [null, "unavailable"]]) {
    let renderer;
    await act(async () => {
      renderer = create(
        React.createElement(ControlPlaneSettingsState, {
          data: controlPlaneData({
            connection_status: {
              state: "online",
              checked_at: "2099-01-01T00:00:00Z",
              details: {
                provider: "openrouter",
                model: "anthropic/claude-sonnet-5",
                usage: { total_tokens: 10 },
                cost,
              },
            },
          }),
          error: null,
          loading: false,
          onRefresh: () => {},
        }),
      );
    });
    assert.match(JSON.stringify(renderer.toJSON()), new RegExp(expected.replace("$", "\\$")));
    await act(async () => { renderer.unmount(); });
  }
});

test("ControlPlaneSettings clears OpenRouter connection defaults when switching providers", async () => {
  let renderer;
  await act(async () => {
    renderer = create(
      React.createElement(ControlPlaneSettingsState, {
        data: controlPlaneData({ provider: "openrouter", model: "anthropic/claude-sonnet-5" }),
        error: null,
        loading: false,
        onRefresh: () => {},
      }),
    );
  });

  await act(async () => {
    renderer.root.findByProps({ id: "control-plane-provider" }).props.onChange({ target: { value: "openai" } });
  });

  assert.equal(renderer.root.findByProps({ id: "control-plane-base-url" }).props.value, "");
  assert.equal(
    renderer.root.findByProps({ id: "control-plane-api-key-env" }).props.value,
    "FOREMAN_AI_HQ_CONTROL_API_KEY",
  );
  assert.equal(renderer.root.findByProps({ id: "control-plane-model" }).props.value, "gpt-5.6-sol");
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

function lowConfidenceItem(decisionState, overrides = {}) {
  const base = "/api/projects/demo-999/tasks/task-estimated-999/estimate-decision";
  const rev = "?estimate_revision=1";
  const actionsByState = {
    decision_required: [
      { kind: "acknowledge_estimate", label: "Acknowledge estimate", method: "POST", href: `${base}/acknowledge${rev}` },
      { kind: "manual_estimate", label: "Enter manual estimate", method: "POST", href: `${base}/manual${rev}` },
      { kind: "create_scout", label: "Create linked Scout", method: "POST", href: `${base}/scout${rev}` },
    ],
    scout_pending: [
      { kind: "view_scout", label: "View linked Scout", method: "GET", href: "/projects/demo-999#task-scout-1" },
    ],
    findings_ready: [
      { kind: "view_scout_report", label: "View Scout report", method: "GET", href: "/sessions/sess-scout" },
      { kind: "request_reestimate", label: "Request re-estimate", method: "POST", href: `${base}/scout/reestimate${rev}` },
    ],
    reestimate_ready: [
      { kind: "view_scout_report", label: "View Scout report", method: "GET", href: "/sessions/sess-scout" },
      { kind: "apply_reestimate", label: "Apply re-estimate", method: "POST", href: `${base}/scout/reestimate/apply?estimate_revision=1&attempt_id=att-1` },
      { kind: "dismiss_reestimate", label: "Dismiss re-estimate", method: "POST", href: `${base}/scout/reestimate/dismiss?estimate_revision=1&attempt_id=att-1` },
    ],
    reestimate_failed: [
      { kind: "view_scout_report", label: "View Scout report", method: "GET", href: "/sessions/sess-scout" },
      { kind: "retry_reestimate", label: "Retry re-estimate", method: "POST", href: `${base}/scout/reestimate/retry?estimate_revision=1&attempt_id=att-1` },
      { kind: "dismiss_reestimate", label: "Dismiss re-estimate", method: "POST", href: `${base}/scout/reestimate/dismiss?estimate_revision=1&attempt_id=att-1` },
    ],
  };
  return {
    id: "task:task-estimated-999:low_confidence_estimate",
    kind: "low_confidence_estimate",
    title: "Low confidence estimate",
    reason: "Automatic estimate confidence is low.",
    task_id: "task-estimated-999",
    task_kind: "implementation",
    advisory: true,
    confidence: 0.5,
    decision_state: decisionState,
    scout_task_id: decisionState === "decision_required" ? null : "scout-1",
    session_href: decisionState.startsWith("reestimate") || decisionState === "findings_ready" ? "/sessions/sess-scout" : null,
    actions: actionsByState[decisionState] || [],
    ...overrides,
  };
}

test("Pipeline intake selector defaults to implementation", () => {
  const markup = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999",
    surface: "pipeline",
    data: boardData(),
    error: null,
    loading: false,
    action: () => {},
  }));
  assert.match(markup, /<select[^>]*name="task_kind"[^>]*>\s*<option value="implementation">/);
  assert.match(markup, /<option value="scout">/);
  assert.doesNotMatch(markup, /<option value="acceptance_verification">/);
});

test("TaskCard renders bounded Scout kind label and launch controls", () => {
  const data = scoutBoardData();
  const markup = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999",
    surface: "pipeline",
    data,
    error: null,
    loading: false,
    action: () => {},
  }));
  assert.match(markup, /<span[^>]*class="[^"]*pill scout[^"]*"[^>]*>scout<\/span>/);
  assert.match(markup, /Launch/);
});

test("Needs You renders three initial low-confidence choices", () => {
  const data = scoutBoardData({
    needs_you: { project_id: "demo-999", count: 1, items: [lowConfidenceItem("decision_required")] },
  });
  const markup = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999",
    surface: "pipeline",
    data,
    error: null,
    loading: false,
    action: () => {},
  }));
  assert.match(markup, /Acknowledge estimate/);
  assert.match(markup, /<form[^>]*class="needs-you-inline"[^>]*>.*?<input[^>]*type="number"/s);
  assert.match(markup, /Create linked Scout/);
  const needsYouSection = markup.match(/<section class="panel needs-you"[^>]*>.*?<\/section>/s)?.[0] ?? "";
  const buttons = [...needsYouSection.matchAll(/<button[^>]*class="[^"]*btn[^"]*"/g)];
  assert.equal(buttons.length, 3);
});

test("Needs You renders a visible Scout label for Scout decisions", () => {
  const data = scoutBoardData({
    needs_you: { project_id: "demo-999", count: 1, items: [lowConfidenceItem("decision_required", { task_kind: "scout" })] },
  });
  const markup = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999",
    surface: "pipeline",
    data,
    error: null,
    loading: false,
    action: () => {},
  }));
  const needsYouSection = markup.match(/<section class="panel needs-you"[^>]*>.*?<\/section>/s)?.[0] ?? "";
  assert.match(needsYouSection, /<span[^>]*class="[^"]*pill scout[^"]*"[^>]*>scout<\/span>/);
});

test("Needs You GET action renders a safe anchor", () => {
  const data = scoutBoardData({
    needs_you: { project_id: "demo-999", count: 1, items: [lowConfidenceItem("scout_pending")] },
  });
  const markup = renderToStaticMarkup(React.createElement(BoardState, {
    projectId: "demo-999",
    surface: "pipeline",
    data,
    error: null,
    loading: false,
    action: () => {},
  }));
  assert.match(markup, /<a[^>]*class="[^"]*btn[^"]*secondary[^"]*"[^>]*href="\/projects\/demo-999#task-scout-1"[^>]*>View linked Scout<\/a>/);
});

test("Needs You linked Scout re-estimation states render Apply, Dismiss, and duplicate-spend Retry", () => {
  for (const [state, expected] of [
    ["findings_ready", ["View Scout report", "Request re-estimate"]],
    ["reestimate_ready", ["View Scout report", "Apply re-estimate", "Dismiss re-estimate"]],
    ["reestimate_failed", ["View Scout report", "Retry re-estimate", "Dismiss re-estimate"]],
  ]) {
    const data = scoutBoardData({
      needs_you: { project_id: "demo-999", count: 1, items: [lowConfidenceItem(state)] },
    });
    const markup = renderToStaticMarkup(React.createElement(BoardState, {
      projectId: "demo-999",
      surface: "pipeline",
      data,
      error: null,
      loading: false,
      action: () => {},
    }));
    for (const text of expected) {
      assert.match(markup, new RegExp(text));
    }
  }
});

test("submitBoardAction sends re-estimate retry with duplicate-spend acknowledgement", async () => {
  let request;
  const result = await submitBoardAction({
    url: "/api/projects/demo-999/tasks/task-estimated-999/estimate-decision/scout/reestimate/retry?estimate_revision=1&attempt_id=att-1",
    body: JSON.stringify({ acknowledge_possible_duplicate_spend: true }),
    fetchImpl: async (url, options) => {
      request = { url, options };
      return { ok: true, json: async () => ({ ok: true, next_href: null }) };
    },
    navigate: () => assert.fail("successful action must not navigate"),
    reload: async () => {},
    onNotice: () => {},
  });
  assert.equal(result, "reloaded");
  assert.equal(request.url, "/api/projects/demo-999/tasks/task-estimated-999/estimate-decision/scout/reestimate/retry?estimate_revision=1&attempt_id=att-1");
  assert.equal(request.options.body, JSON.stringify({ acknowledge_possible_duplicate_spend: true }));
});

test("submitBoardAction failure preserves backend error and setup href", async () => {
  let notice;
  const result = await submitBoardAction({
    url: "/api/projects/demo-999/tasks/task-estimated-999/estimate-decision/scout/reestimate/apply?estimate_revision=1&attempt_id=att-1",
    body: JSON.stringify({}),
    fetchImpl: async () => ({
      ok: false,
      json: async () => ({ ok: false, error: "Stale re-estimate.", setup_href: "/settings/workers" }),
    }),
    navigate: () => assert.fail("failure must not navigate"),
    reload: async () => {},
    onNotice: (n) => { notice = n; },
  });
  assert.equal(result, "failed");
  assert.deepEqual(notice, { message: "Stale re-estimate.", setupHref: "/settings/workers" });
});
