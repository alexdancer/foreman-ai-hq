import React from "react";

import { cx } from "./cx.js";

export function TokenComparison({
  estimate,
  actual,
  provenance,
  estimateLabel = "Estimate",
  actualLabel,
  className,
  "aria-label": ariaLabel = "Estimate versus actual tokens",
  ...rest
}) {
  const savings =
    Number.isFinite(estimate) && Number.isFinite(actual) && estimate > 0 && actual <= estimate
      ? Math.round((1 - actual / estimate) * 100)
      : null;
  const displayedActualLabel = actualLabel ?? (savings != null && savings > 0 ? `Actual · −${savings}%` : "Actual");

  return (
    <div className={cx("token-comparison", className)} role="group" aria-label={ariaLabel} {...rest}>
      <div className="token-stat token-stat-estimate">
        <small>{estimateLabel}</small>
        <strong>{estimate?.toLocaleString() ?? "Unavailable"}</strong>
      </div>
      <div className="token-stat-divider" aria-hidden="true" />
      <div className="token-stat token-stat-actual">
        <small>{displayedActualLabel}</small>
        <strong>{actual?.toLocaleString() ?? "Unavailable"}</strong>
      </div>
      {provenance && <p className="token-comparison-provenance">Spend tracking · {provenance}</p>}
    </div>
  );
}
