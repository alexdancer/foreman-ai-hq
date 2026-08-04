import React from "react";

import { StatusPill, statusTone } from "./ui/index.js";

export function BlockedCondition({ reason, announce = false }) {
  if (!reason) return null;
  return (
    <div className="blocked-condition" role={announce ? "status" : undefined}>
      <StatusPill tone={statusTone("blocked")} label="Blocked" />
      <span className="wrap-anywhere">{reason}</span>
    </div>
  );
}
