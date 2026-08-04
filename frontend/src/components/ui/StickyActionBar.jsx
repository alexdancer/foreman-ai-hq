import React from "react";

import { cx } from "./cx.js";

export function StickyActionBar({ consequence, reason, actions, className, children, ...rest }) {
  return (
    <div className={cx("sticky-action-bar", className)} {...rest}>
      <div className="sticky-action-copy">
        <strong>{consequence}</strong>
        {reason && <span className="sticky-action-reason" role="status">{reason}</span>}
        {children}
      </div>
      {actions && <div className="sticky-action-actions">{actions}</div>}
    </div>
  );
}
