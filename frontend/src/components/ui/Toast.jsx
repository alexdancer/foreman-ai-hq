import React from "react";

import { cx } from "./cx.js";

export function Toast({ tone = "info", title, className, children, ...rest }) {
  const urgent = tone === "danger" || tone === "error";
  return (
    <div
      className={cx("toast", tone !== "info" && `toast-${tone}`, className)}
      role={urgent ? "alert" : "status"}
      aria-live={urgent ? "assertive" : "polite"}
      {...rest}
    >
      {title && <strong>{title}</strong>}
      <div>{children}</div>
    </div>
  );
}
