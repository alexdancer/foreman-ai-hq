import React, { useCallback, useEffect, useRef, useState } from "react";

import { getJSON, postJSON } from "../api.js";
import { Button, Fieldset } from "../components/ui/index.js";
import { useResource } from "../useResource.js";

const safeError = (error) =>
  error?.status === 401
    ? "Budget settings require sign-in."
    : "Could not load budget settings. Retry.";

export default function BudgetSettings() {
  const [refreshKey, setRefreshKey] = useState(0);
  const { data, error, loading } = useResource("/api/settings/budget", refreshKey);
  const refresh = useCallback(() => { setRefreshKey((k) => k + 1); }, []);

  return (
    <BudgetSettingsState
      data={data}
      error={error}
      loading={loading}
      onRefresh={refresh}
    />
  );
}

export function BudgetSettingsState({ data, error, loading, onRefresh }) {
  const [daily, setDaily] = useState("");
  const [session, setSession] = useState("");
  const [status, setStatus] = useState(null);
  const [inlineError, setInlineError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    if (data) {
      setDaily(data.daily_cap_tokens ?? "");
      setSession(data.session_cap_tokens ?? "");
    }
  }, [data]);

  const submitSave = async (event) => {
    event.preventDefault();
    setInlineError(null);
    setStatus(null);
    const dailyCap = Number(daily);
    const sessionCap = Number(session);
    if (!Number.isInteger(dailyCap) || dailyCap <= 0 || !Number.isInteger(sessionCap) || sessionCap <= 0) {
      setInlineError("Daily and session caps must be positive integers.");
      return;
    }
    setBusy(true);
    try {
      const outcome = await postJSON("/settings/budget", {
        daily_cap_tokens: dailyCap,
        session_cap_tokens: sessionCap,
      });
      if (!outcome?.ok) {
        setInlineError(boundedError(outcome?.error, "Could not save budget."));
      } else {
        setStatus("Budget saved.");
        onRefresh();
      }
    } catch (err) {
      setInlineError(boundedError(err.message, "Could not save budget."));
    } finally {
      setBusy(false);
    }
  };

  const submitReset = async () => {
    setConfirming(false);
    setInlineError(null);
    setStatus(null);
    setBusy(true);
    try {
      const outcome = await postJSON("/settings/budget/reset", {});
      if (!outcome?.ok) {
        setInlineError(boundedError(outcome?.error, "Could not reset budget counter."));
      } else {
        setStatus("Daily budget counter reset.");
        onRefresh();
      }
    } catch (err) {
      setInlineError(boundedError(err.message, "Could not reset budget counter."));
    } finally {
      setBusy(false);
    }
  };

  if (loading && !data) {
    return <p className="spinner">Loading budget settings…</p>;
  }
  if (error) {
    return (
      <>
        <div className="notice danger">{safeError(error)}</div>
        <p><a href="/settings/budget">Retry</a></p>
      </>
    );
  }

  const budget = data || {};
  const used = budget.current_window_used_tokens ?? 0;
  const remaining = budget.current_window_remaining_tokens;
  const dailyCap = budget.daily_cap_tokens;
  const resetAt = budget.daily_usage_reset_at;

  return (
    <>
      <h1 className="page-title">Token budget</h1>
      <p className="page-sub">Daily governed model spend is enforced from the token ledger; Worker execution actuals stay separate.</p>

      <div className="live-notice" aria-live="polite">
        {inlineError || status || ""}
      </div>

      <section className="panel">
        <div className="panel-header"><h3>Configure launch guardrails</h3></div>
        <div className="panel-body">
          <form onSubmit={submitSave} className="dashboard-grid">
            <div>
              <label htmlFor="daily-cap">Daily governed model-spend cap</label>
              <input
                id="daily-cap"
                type="number"
                min={1}
                step={1}
                value={daily}
                onChange={(e) => setDaily(e.target.value)}
                className="board-input"
                required
                aria-describedby="daily-cap-help"
              />
              <p id="daily-cap-help" className="muted">
                Applied to total governed model spend: Worker execution, control-plane estimation, task breakdown, adapter verification, Agent Review/reporting, and other tracked token rows.
              </p>
            </div>
            <div>
              <label htmlFor="session-cap">Per-session Worker execution cap</label>
              <input
                id="session-cap"
                type="number"
                min={1}
                step={1}
                value={session}
                onChange={(e) => setSession(e.target.value)}
                className="board-input"
                required
                aria-describedby="session-cap-help"
              />
              <p id="session-cap-help" className="muted">
                Stored as launch/session budget context for proxy-governed and native-usage Workers.
              </p>
            </div>
            <div className="toolbar" style={{ gridColumn: "1 / -1" }}>
              <Button type="submit" disabled={busy} disabledReason="A budget update is already in progress.">
                Save budget
              </Button>
              <a href="/setup" className="btn secondary">Back to setup</a>
            </div>
          </form>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header"><h3>Today’s budget counter</h3></div>
        <div className="panel-body">
          <div className="dashboard-grid">
            <article className="kpi">
              <div className="label">Used in current daily window</div>
              <div className="value mono">{formatTokens(used)}</div>
              <div className="sub">since {budget.budget_since || "—"}</div>
            </article>
            <article className="kpi">
              <div className="label">Remaining daily budget</div>
              <div className="value mono">{remaining !== null ? formatTokens(remaining) : "—"}</div>
              <div className="sub">based on the saved daily cap</div>
            </article>
            <Fieldset className="budget-action-group" legend="Reset daily guardrail usage">
                <p className="muted">Start a new daily budget window from now. Token ledger evidence, session reports, and task actuals are preserved.</p>
                {resetAt && <p className="mono muted">last reset: {resetAt}</p>}
                <Button
                  type="button"
                  variant="danger"
                  onClick={() => setConfirming(true)}
                  disabled={busy}
                  disabledReason="A budget update is already in progress."
                >
                  Reset today’s budget counter
                </Button>
            </Fieldset>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header"><h3>Spend authority</h3></div>
        <div className="panel-body">
          <div className="dashboard-grid">
            <Fieldset className="budget-authority-group" legend="Daily budgeted spend">
                <p>
                  <span className="pill green">worker_execution</span>{" "}
                  <span className="pill green">control_plane</span>{" "}
                  <span className="pill green">reporting_summary</span>{" "}
                  <span className="pill green">task_breakdown</span>{" "}
                  <span className="pill green">adapter_verification</span>{" "}
                  <span className="pill green">other</span>
                </p>
                <p className="muted">Daily guardrails and alarms count all governed token-ledger rows, including Agent Review and setup/orchestration spend.</p>
            </Fieldset>
            <Fieldset className="budget-authority-group" legend="Worker-only evidence">
                <p>
                  <span className="pill blue">per-session Worker cap</span>{" "}
                  <span className="pill blue">task actual_tokens</span>
                </p>
                <p className="muted">Per-session Worker execution caps and task actuals remain based on Worker execution evidence, not Agent Review/reporting tokens.</p>
            </Fieldset>
          </div>
        </div>
      </section>

      {confirming && (
        <ResetConfirmationDialog
          onConfirm={submitReset}
          onCancel={() => setConfirming(false)}
        />
      )}
    </>
  );
}

function ResetConfirmationDialog({ onConfirm, onCancel }) {
  const ref = useRef(null);
  useEffect(() => {
    const cancelButton = ref.current?.querySelector("button.secondary");
    (cancelButton || ref.current?.querySelector("button"))?.focus();
  }, []);

  return (
    <div
      className="panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reset-dialog-title"
      ref={ref}
      style={{
        position: "fixed",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        zIndex: 100,
        minWidth: 320,
        background: "var(--bg-1)",
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="panel-body">
        <h3 id="reset-dialog-title" style={{ margin: "0 0 10px", fontSize: 13 }}>
          Reset today’s budget counter?
        </h3>
        <p className="muted">This starts a new daily budget window from now. Ledger evidence, session reports, and task actuals are preserved.</p>
        <div className="toolbar" style={{ marginBottom: 0 }}>
          <button type="button" className="btn danger" onClick={onConfirm}>
            Confirm reset
          </button>
          <button type="button" className="btn secondary" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

function boundedError(value, fallback) {
  return typeof value === "string" && value ? value.slice(0, 1000) : fallback;
}

function formatTokens(value) {
  return Number(value || 0).toLocaleString();
}
