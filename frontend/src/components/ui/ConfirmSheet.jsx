import React, { forwardRef, useEffect, useId, useImperativeHandle, useRef } from "react";

import { cx } from "./cx.js";

const focusableSelector = [
  "a[href]",
  "button:not([disabled])",
  "textarea:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(", ");

export const ConfirmSheet = forwardRef(function ConfirmSheet({
  open,
  onClose,
  title,
  description,
  actions,
  className,
  children,
  ...rest
}, forwardedRef) {
  const generatedId = useId();
  const dialogRef = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useImperativeHandle(forwardedRef, () => dialogRef.current);

  useEffect(() => {
    if (!open || typeof document === "undefined") return undefined;
    const dialog = dialogRef.current;
    const opener = document.activeElement;
    if (!dialog) return undefined;

    const focusable = () => Array.from(dialog.querySelectorAll(focusableSelector));
    const initialTarget = focusable()[0] || dialog;
    initialTarget.focus();

    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const targets = focusable();
      if (targets.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      const first = targets[0];
      const last = targets[targets.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && (active === first || !dialog.contains(active))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (active === last || !dialog.contains(active))) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      if (opener?.isConnected && typeof opener.focus === "function") opener.focus();
    };
  }, [open]);

  if (open && typeof onClose !== "function") {
    throw new Error("ConfirmSheet requires onClose while open.");
  }
  if (!open) return null;
  const titleId = `${generatedId}-title`;
  const descriptionId = description ? `${generatedId}-description` : undefined;

  return (
    <div className="confirm-sheet-backdrop" role="presentation">
      <section
        ref={dialogRef}
        className={cx("confirm-sheet", className)}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        tabIndex={-1}
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
});
