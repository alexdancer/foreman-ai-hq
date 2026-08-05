import React, { useCallback, useEffect, useState } from "react";

import { postJSON } from "../api.js";
import { StatusPill, statusTone } from "../components/ui/index.js";
import { useResource } from "../useResource.js";

const safeError = (error) =>
  error?.status === 401
    ? "Orchestrator settings require sign-in."
    : "Could not load orchestrator settings. Retry.";

export default function ControlPlaneSettings() {
  const [refreshKey, setRefreshKey] = useState(0);
  const { data, error, loading } = useResource("/api/settings/control-plane", refreshKey);
  const refresh = useCallback(() => { setRefreshKey((k) => k + 1); }, []);

  return (
    <ControlPlaneSettingsState
      data={data}
      error={error}
      loading={loading}
      onRefresh={refresh}
    />
  );
}

export function ControlPlaneSettingsState({ data, error, loading, onRefresh }) {
  const [selected, setSelected] = useState("");
  const [status, setStatus] = useState(null);
  const [inlineError, setInlineError] = useState(null);
  const [busy, setBusy] = useState(false);
  const busyReasonId = busy ? "control-plane-busy-reason" : undefined;

  useEffect(() => {
    if (data) setSelected(data.model || "");
  }, [data]);

  const submitSave = async (event) => {
    event.preventDefault();
    setInlineError(null);
    setStatus(null);
    if (!selected) {
      setInlineError("Choose a model from pi's inventory.");
      return;
    }
    setBusy(true);
    try {
      const outcome = await postJSON("/settings/control-plane", { control_plane_model: selected });
      if (!outcome?.ok) {
        setInlineError(boundedError(outcome?.error, "Could not save the Orchestrator Model."));
      } else {
        setStatus("Saved. Verify to prove the model runs and is metered.");
        onRefresh();
      }
    } catch (err) {
      setInlineError(boundedError(err.message, "Could not save the Orchestrator Model."));
    } finally {
      setBusy(false);
    }
  };

  const submitDiscover = async () => {
    setInlineError(null);
    setStatus(null);
    setBusy(true);
    try {
      const outcome = await postJSON("/settings/control-plane/discover", {});
      if (outcome?.needs_authentication) {
        setInlineError("pi reports no models. Run `pi /login` to authenticate a provider.");
      } else if (!outcome?.models?.length) {
        setInlineError(boundedError(outcome?.reasons?.join("; "), "Model discovery failed."));
      } else {
        setStatus(`Discovered ${outcome.models.length} models from pi.`);
      }
      onRefresh();
    } catch (err) {
      setInlineError(boundedError(err.message, "Model discovery failed."));
    } finally {
      setBusy(false);
    }
  };

  const submitVerify = async () => {
    setInlineError(null);
    setStatus(null);
    setBusy(true);
    try {
      const outcome = await postJSON("/settings/control-plane/verify", {});
      if (outcome?.passed) {
        setStatus("Verified: the sentinel matched and a token turn was recorded.");
      } else {
        setInlineError(boundedError(outcome?.error, "Verification failed."));
      }
      onRefresh();
    } catch (err) {
      setInlineError(boundedError(err.message, "Verification failed."));
    } finally {
      setBusy(false);
    }
  };

  if (loading && !data) {
    return <p className="spinner">Loading orchestrator settings…</p>;
  }
  if (error) {
    return (
      <>
        <div className="notice danger">{safeError(error)}</div>
        <p><a href="/settings/control-plane">Retry</a></p>
      </>
    );
  }
  if (!data) {
    return <p className="spinner">Loading orchestrator settings…</p>;
  }

  const inventory = data.inventory || {};
  const models = inventory.models || [];
  const verification = data.verification || {};
  const diverging = data.diverging_jobs || {};
  const divergingKeys = Object.keys(diverging);
  const state = data.connection_status?.state || "offline";
  const details = data.connection_status?.details || null;

  return (
    <>
      <h1 className="page-title">Orchestrator model</h1>
      <p className="page-sub">
        Chosen from pi&rsquo;s own inventory · drives planning, estimation, breakdown, and agent review
      </p>

      <div className="live-notice" aria-live="polite">
        {inlineError || status || ""}
      </div>
      {busy && <p className="disabled-reason" id={busyReasonId} role="status">A control-plane settings action is already in progress.</p>}

      {!data.configured && (
        <div className="notice danger">
          Orchestrator is not configured. Orchestration and the board are blocked until a
          model from pi&rsquo;s inventory is saved.
        </div>
      )}

      {divergingKeys.length > 0 && (
        <div className="notice warning">
          These ignored legacy settings do not select runtime models:{" "}
          {divergingKeys.map((key) => `${key} = ${diverging[key]}`).join(", ")}. Saving the
          Orchestrator Model removes them.
        </div>
      )}

      <section className="control-plane-layout">
        <article className="panel">
          <div className="panel-header"><h3>Choose orchestrator model</h3></div>
          <div className="panel-body">
            {inventory.needs_authentication ? (
              <div className="notice warning">
                <p>
                  pi reports no runnable models, which means no provider is authenticated yet.
                </p>
                <p>
                  Run <code>pi /login</code> to sign in to a provider with OAuth or an API key,
                  then refresh the inventory.
                </p>
              </div>
            ) : models.length === 0 ? (
              <p className="muted">
                No inventory has been discovered yet. Refresh to ask pi which models it can run.
              </p>
            ) : (
              <form className="control-plane-form" onSubmit={submitSave}>
                <div className="control-plane-fields">
                  <div className="control-plane-field control-plane-field-wide">
                    <label htmlFor="orchestrator-model">Model</label>
                    <select
                      id="orchestrator-model"
                      value={selected}
                      onChange={(e) => setSelected(e.target.value)}
                      disabled={busy}
                      aria-describedby={busyReasonId}
                    >
                      <option value="">Choose a model…</option>
                      {models.map((model) => (
                        <option key={model} value={model}>{model}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="control-plane-actions">
                  <button type="submit" className="btn" disabled={busy || !selected} aria-describedby={busyReasonId}>
                    Save
                  </button>
                </div>
              </form>
            )}

            <div className="control-plane-actions" style={{ marginTop: 12 }}>
              <button type="button" className="btn" onClick={submitDiscover} disabled={busy} aria-describedby={busyReasonId}>
                Refresh inventory
              </button>
              <button
                type="button"
                className="btn"
                onClick={submitVerify}
                disabled={busy || !data.configured}
                aria-describedby={busyReasonId}
              >
                Verify
              </button>
            </div>
            <p className="muted">
              {inventory.discovered_at
                ? `Inventory discovered ${inventory.discovered_at}`
                : "Inventory has never been discovered."}
            </p>
            {data.shadowed_settings?.orchestrator_model && (
              <p className="muted">
                Overridden by environment variable {data.shadowed_settings.orchestrator_model}.
              </p>
            )}
          </div>
        </article>

        <article className="panel">
          <div className="panel-header"><h3>Verification</h3></div>
          <div className="panel-body">
            <p>
              Status: <StatusPill tone={statusTone(state)} label={state === "needs_test" ? "needs test" : state} />
            </p>
            {verification.verified_at ? (
              <div className="kv">
                <div className="k">Result</div>
                <div className="v">{verification.passed ? "passed" : "failed"}</div>
                <div className="k">Model</div>
                <div className="v">{verification.model}</div>
                <div className="k">Verified at</div>
                <div className="v">{verification.verified_at}</div>
                {verification.stale && (
                  <>
                    <div className="k">Stale</div>
                    <div className="v">
                      Proves a different model than the one configured now. Verify again.
                    </div>
                  </>
                )}
                {verification.reasons?.length > 0 && (
                  <>
                    <div className="k">Reasons</div>
                    <div className="v">{verification.reasons.join("; ")}</div>
                  </>
                )}
              </div>
            ) : (
              <p className="muted">
                Not verified. Presence in the inventory is not verification — only a real
                metered turn is.
              </p>
            )}
            {details && (
              <details style={{ marginTop: 10 }}>
                <summary>Raw sanitized details</summary>
                <pre className="raw-evidence">{JSON.stringify(details, null, 2)}</pre>
              </details>
            )}
          </div>
        </article>
      </section>
    </>
  );
}

function boundedError(value, fallback) {
  return typeof value === "string" && value ? value.slice(0, 1000) : fallback;
}
