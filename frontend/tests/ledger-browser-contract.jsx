import React from "react";
import { createRoot } from "react-dom/client";

import { Panel, PanelBody, PanelHeader, Skeleton, StatusPill } from "../src/components/ui/index.js";
import "../src/tokens.css";

function ContractSurface() {
  return (
    <main>
      <Panel>
        <PanelHeader title="Ledger contract" />
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

async function inspect() {
  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
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

  const live = document.querySelector(".live-pulse-dot");
  const liveStyle = getComputedStyle(live);
  requireContract(matchMedia("(prefers-reduced-motion: reduce)").matches, "reduced motion is not active");
  requireContract(liveStyle.animationName === "none" && liveStyle.opacity === "1", "live status loses reduced-motion meaning");
  requireContract(document.querySelector(".status-pill-glyph")?.textContent.trim(), "status glyph is missing");
  requireContract(document.querySelector(".status-pill-label")?.textContent.trim() === "running", "status label is missing");

  const progressStyle = getComputedStyle(document.querySelector(".board-intake-progress-bar"));
  requireContract(progressStyle.animationName === "none" && progressStyle.transform === "none", "progress fallback still moves");
  const skeletonStyle = getComputedStyle(document.querySelector(".skeleton-bar"), "::after");
  requireContract(skeletonStyle.animationName === "none" && skeletonStyle.transform === "none", "skeleton fallback still moves");
  requireContract(document.querySelectorAll(".panel .panel").length === 0, "panels are nested");
  document.documentElement.dataset.ledgerContract = "passed";
}

createRoot(document.querySelector("#root")).render(<ContractSurface />);
inspect().catch((error) => {
  document.documentElement.dataset.ledgerContract = "failed";
  document.body.dataset.contractError = error.message;
});
