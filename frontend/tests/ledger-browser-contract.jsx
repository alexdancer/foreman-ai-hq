import React from "react";
import { createRoot } from "react-dom/client";

import { ConfirmSheet, Panel, PanelBody, PanelHeader, Skeleton, StatusPill } from "../src/components/ui/index.js";
import { BoardState, EvidenceDrawerState } from "../src/views/Board.jsx";
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
      <button id="pipeline-outside-target" type="button">Outside target</button>
      <PipelineContract />
      <FloorContract />
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
  requireContract(activePanel.querySelector(".event-row"), "active Worker Run does not preserve shared live-event treatment");
  requireContract(getComputedStyle(activeGrid).gridTemplateColumns.split(" ").length === 1, "active Worker Runs are not full-width panels");
  requireContract(
    Math.abs(activePanel.getBoundingClientRect().width - activeGrid.getBoundingClientRect().width) < 1,
    "active Worker Run panel does not fill its Execution Floor section",
  );

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
  document.body.dataset.contractError = error.message;
});
