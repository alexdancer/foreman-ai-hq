import React from "react";

import { StatusPill, statusTone } from "./ui/index.js";

export function TaskCondition({ label, reason, tone = "warning", announce = false, className }) {
  if (!label) return null;
  const classes = ["task-condition", className].filter(Boolean).join(" ");
  return (
    <div className={classes} role={announce ? "status" : undefined}>
      <StatusPill tone={tone} label={label} />
      {reason && <span className="wrap-anywhere">{reason}</span>}
    </div>
  );
}

export function BlockedCondition({ reason, announce = false }) {
  if (!reason) return null;
  return (
    <TaskCondition
      label="Blocked"
      reason={reason}
      tone={statusTone("blocked")}
      announce={announce}
      className="blocked-condition"
    />
  );
}
