function normalize(value) {
  return String(value || "").trim().toLowerCase();
}

export function statusTone(status) {
  const value = normalize(status);
  if (["running", "active"].includes(value)) return "running";
  if (["failed", "fail", "error", "aborted", "canceled", "cancelled"].includes(value)) return "danger";
  if (["blocked", "proposed", "pending", "review", "warning", "warn"].includes(value)) return "warning";
  if (["accepted", "complete", "completed", "done", "pass", "passed", "ready", "success", "succeeded", "verified"].includes(value)) return "success";
  if (["info", "low"].includes(value)) return "info";
  return "neutral";
}

export function sessionStatusTone(status, active = false) {
  return active ? "running" : statusTone(status);
}

export function severityStatusTone(severity) {
  const value = normalize(severity);
  if (["critical", "high"].includes(value)) return "danger";
  if (["warning", "medium"].includes(value)) return "warning";
  if (["info", "low"].includes(value)) return "info";
  return "neutral";
}

export function checkpointStatusTone(passed) {
  return passed ? "success" : "danger";
}

export function capabilityStatusTone(state, archived = false) {
  if (archived) return "neutral";
  const value = normalize(state);
  if (value === "launch_ready") return "success";
  if (value === "analysis_ready") return "info";
  return statusTone(value);
}

export function budgetZoneStatusTone(zone) {
  const value = normalize(zone);
  if (value === "green") return "success";
  if (value === "yellow") return "warning";
  if (value === "red") return "danger";
  return "neutral";
}

export function trackingStatusTone(mode, launchReady = false) {
  const value = normalize(mode);
  if (["proxy_governed", "native_usage"].includes(value)) return launchReady ? "success" : "info";
  if (["", "observed_only", "unverified"].includes(value)) return "warning";
  return "neutral";
}
