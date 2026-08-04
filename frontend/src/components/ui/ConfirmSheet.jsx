import React, { useId } from "react";

import { cx } from "./cx.js";

export function ConfirmSheet({
  open,
  title,
  description,
  actions,
  className,
  children,
  ...rest
}) {
  const generatedId = useId();
  if (!open) return null;
  const titleId = `${generatedId}-title`;
  const descriptionId = description ? `${generatedId}-description` : undefined;

  return (
    <div className="confirm-sheet-backdrop" role="presentation">
      <section
        className={cx("confirm-sheet", className)}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        {...rest}
      >
        <header className="confirm-sheet-header">
          <h2 id={titleId}>{title}</h2>
          {description && <p id={descriptionId}>{description}</p>}
        </header>
        <div className="confirm-sheet-body">{children}</div>
        {actions && <footer className="confirm-sheet-actions">{actions}</footer>}
      </section>
    </div>
  );
}
