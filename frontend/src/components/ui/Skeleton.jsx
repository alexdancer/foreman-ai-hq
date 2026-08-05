import React from "react";

import { cx } from "./cx.js";

export function Skeleton({ label = "Loading", lines = 1, className, ...rest }) {
  const lineCount = Math.max(1, Number(lines) || 1);
  return (
    <div className={cx("skeleton", className)} role="status" aria-label={label} {...rest}>
      {Array.from({ length: lineCount }, (_, index) => (
        <span className="skeleton-bar" aria-hidden="true" key={index} />
      ))}
    </div>
  );
}
