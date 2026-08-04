import { budgetZoneStatusTone, checkpointStatusTone, severityStatusTone } from "./ui/statusTone.js";

export function budgetZoneEvidenceProps(item = {}) {
  return {
    statusTone: budgetZoneStatusTone(item.zone),
    statusLabel: `${item.zone || "unknown"} zone`,
    title: "Budget zone",
    meta: `${item.created_at || "time unavailable"} · max tokens ${item.max_tokens ?? "unavailable"}`,
  };
}

export function alarmEvidenceProps(item = {}, { fallbackId, fallbackBody } = {}) {
  const id = item.id || fallbackId;
  return {
    statusTone: severityStatusTone(item.severity),
    statusLabel: item.severity || "unknown",
    title: item.type || "Alarm",
    meta: `${id} · ${item.created_at || "time unavailable"}`,
    body: item.recommended_action || fallbackBody,
  };
}

export function checkpointEvidenceProps(item = {}) {
  return {
    statusTone: checkpointStatusTone(item.passed),
    statusLabel: item.passed ? "PASS" : "FAIL",
    title: item.name || "Checkpoint",
    detail: item.details,
  };
}
