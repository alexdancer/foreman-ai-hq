function normalize(value) {
  return String(value || "").trim().toLowerCase();
}

export function statusTone(status) {
  const value = normalize(status);
  if (["running", "active"].includes(value)) return "running";
  if (["failed", "fail", "error", "blocked", "aborted", "canceled", "cancelled"].includes(value)) return "danger";
  if (["proposed", "pending", "warning", "warn"].includes(value)) return "warning";
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
