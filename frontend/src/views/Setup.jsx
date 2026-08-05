import React, { useState } from "react";

import { StatusPill, trackingStatusTone } from "../components/ui/index.js";
import { useResource } from "../useResource.js";

const safeError = (error) => error?.status === 401
  ? "Setup state requires sign-in."
  : "Could not load setup state. Retry.";

function setupAdapterQuery() {
  const search = typeof window !== "undefined" ? window.location.search : "";
  const adapterId = new URLSearchParams(search).get("adapter_id");
  return adapterId ? `?adapter_id=${encodeURIComponent(adapterId)}` : "";
}

export default function Setup() {
  const [query] = useState(() => setupAdapterQuery());
  const { data, error, loading } = useResource("/api/setup" + query, 0);

  return <SetupState data={data} error={error} loading={loading} />;
}

export function SetupState({ data, error, loading }) {
  if (loading && !data) {
    return <p className="spinner">Loading setup state…</p>;
  }
  if (error) {
    return (
      <>
        <div className="notice danger">{safeError(error)}</div>
        <p><a href="/setup">Retry</a></p>
      </>
    );
  }

  const setup = data || {};
  const steps = setup.steps || [];
  const nextStep = setup.next_step || { label: "", href: "", detail: "" };
  const activeAdapter = setup.active_adapter;
  const readyToLaunch = setup.ready_to_launch || false;

  const trackingLabel = trackingModeLabel(activeAdapter?.tracking_mode);

  return (
    <>
      <h1 className="page-title">First-run setup</h1>
      <p className="page-sub">
        connect control plane · confirm token budget · verify Worker token tracking · launch from board
      </p>

      <div className="live-notice" aria-live="polite">
        {readyToLaunch ? "Ready to launch" : "Complete the required setup steps before governed Worker launch."}
      </div>

      <section className="status-toolbar" aria-label="Next setup action">
        <div className="status-group">
          <StatusPill tone={readyToLaunch ? "success" : "warning"} label={readyToLaunch ? "ready" : "next missing action"} />
          <span className="status-item">{nextStep.detail}</span>
        </div>
        <a className="btn primary" href={nextStep.href}>
          {nextStep.label}
        </a>
      </section>

      <section className="kpi-row" aria-label="Setup readiness">
        {steps.map((step) => (
          <article className="kpi" key={step.name}>
            <div className="label">{step.name}</div>
            <div className="value" style={{ fontSize: 18 }}>
              <StatusPill tone={setupTone(step.state)} label={step.state || "unknown"} />
            </div>
            <div className="sub">{step.detail}</div>
            <p style={{ margin: "12px 0 0" }}>
              <a className="btn" href={step.href}>
                Open
              </a>
            </p>
          </article>
        ))}
      </section>

      <section className="panel" aria-label="Launch readiness">
        <div className="panel-header">
          <h3>Launch readiness</h3>
        </div>
        <div className="panel-body">
          {readyToLaunch ? (
            <>
              <p>
                <StatusPill tone="success" label="ready" /> Worker execution has a confirmed budget, budget-authoritative adapter, and launch-ready Connected Project.
              </p>
              <p>
                <a className="btn primary" href={nextStep.href}>
                  Open task board
                </a>
              </p>
            </>
          ) : (
            <>
              <p>
                <StatusPill tone="warning" label="setup needed" /> Complete the required setup steps before governed Worker launch.
              </p>
              <ol>
                {steps.map((step) => (
                  <li key={step.name}>
                    <a href={step.href}>{step.name}</a>: <StatusPill tone={setupTone(step.state)} label={step.state || "unknown"} />
                  </li>
                ))}
              </ol>
            </>
          )}
        </div>
      </section>

      {activeAdapter && (
        <section className="panel" aria-label="Active Worker adapter">
          <div className="panel-header">
            <h3>Active Worker adapter</h3>
          </div>
          <div className="panel-body">
            <dl className="workspace-kv">
              <dt>adapter</dt>
              <dd>{activeAdapter.name}</dd>
              <dt>status</dt>
              <dd><StatusPill tone={setupTone(activeAdapter.verification_status)} label={activeAdapter.verification_status || "unknown"} /></dd>
              <dt>launchable</dt>
              <dd><StatusPill tone={activeAdapter.launchable ? "success" : "warning"} label={activeAdapter.launchable ? "true" : "false"} /></dd>
              <dt>tracking</dt>
              <dd><StatusPill tone={trackingStatusTone(activeAdapter.tracking_mode, activeAdapter.launchable)} label={trackingLabel} /></dd>
            </dl>
          </div>
        </section>
      )}
    </>
  );
}

function setupTone(value) {
  const state = String(value || "").toLowerCase();
  if (["ready", "verified", "online", "launchable"].includes(state)) return "success";
  if (["failed", "offline"].includes(state)) return "danger";
  if (state === "blocked") return "warning";
  if (state.includes("need") || state.includes("setup") || state.includes("unverified")) return "warning";
  return "neutral";
}

function trackingModeLabel(mode) {
  if (mode === null || mode === undefined) {
    return "unverified";
  }
  if (mode === "unverified") {
    return "unverified";
  }
  return String(mode);
}
