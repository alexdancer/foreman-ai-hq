import React from "react";
import { createRoot } from "react-dom/client";

import { ConfirmSheet, Panel, PanelBody, PanelHeader, Skeleton, StatusPill } from "../src/components/ui/index.js";
import "../src/tokens.css";

const confirmSheetRef = React.createRef();

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
              <a id="rail-contract-link" data-rail-link="true" aria-label="Pipeline, 3 Needs You" href="/projects/demo-999">
                <span className="nav-glyph" aria-hidden="true">P</span><span className="rail-label">Pipeline</span>
                <span className="nav-badge nav-badge-needs-you" aria-label="3 Needs You"><span aria-hidden="true">3</span></span>
              </a>
            </nav>
          </section>
        </aside>
        <div className="shell-workbench"><div className="context-bar" aria-label="Page context">Project / Pipeline</div><div className="main">Workbench content</div></div>
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
  requireContract(railLink.getAttribute("aria-label") === "Pipeline, 3 Needs You", "collapsed rail link loses its badge state");
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
