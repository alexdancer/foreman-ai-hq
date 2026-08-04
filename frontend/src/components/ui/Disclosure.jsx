import React from "react";

import { cx } from "./cx.js";

export function Disclosure({ label, count, countLabel, className, children, ...rest }) {
  if (label == null || (typeof label === "string" && !label.trim())) {
    throw new Error("Disclosure requires a visible label.");
  }
  if (count == null) {
    throw new Error("Disclosure requires a visible count.");
  }
  const quantityLabel = countLabel || `${count} ${count === 1 ? "item" : "items"}`;
  return (
    <details className={cx("disclosure", className)} {...rest}>
      <summary>
        <span className="disclosure-label">{label}</span>
        <span className="disclosure-count" aria-label={quantityLabel}>{count}</span>
        <span className="disclosure-chevron" aria-hidden="true">›</span>
      </summary>
      <div className="disclosure-body">{children}</div>
    </details>
  );
}

export function EvidenceDisclosure({ className, ...rest }) {
  return <Disclosure className={cx("evidence-disclosure", className)} {...rest} />;
}
