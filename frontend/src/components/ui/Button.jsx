import React, { useId } from "react";

import { cx } from "./cx.js";

export function Button({
  as: Component = "button",
  variant = "primary",
  size,
  disabled = false,
  disabledReason,
  className,
  children,
  ...rest
}) {
  const generatedReasonId = useId();
  if (disabled && !disabledReason) {
    throw new Error("Button requires disabledReason when disabled.");
  }
  const reasonId = disabled && disabledReason ? `${generatedReasonId}-reason` : undefined;
  const describedBy = [rest["aria-describedby"], reasonId].filter(Boolean).join(" ") || undefined;
  const classes = cx(
    "btn",
    size === "small" && "small",
    variant && variant !== "primary" && variant,
    className,
  );
  const control = (
    <Component
      className={classes}
      disabled={disabled || undefined}
      {...rest}
      aria-describedby={describedBy}
    >
      {children}
    </Component>
  );

  if (!reasonId) return control;
  return (
    <span className="disabled-control">
      {control}
      <span className="disabled-reason" id={reasonId}>{disabledReason}</span>
    </span>
  );
}
