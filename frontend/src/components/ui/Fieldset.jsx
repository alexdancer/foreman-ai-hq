import React, { useId } from "react";

import { cx } from "./cx.js";

export function Fieldset({
  legend,
  description,
  disabled = false,
  disabledReason,
  className,
  children,
  ...rest
}) {
  const generatedReasonId = useId();
  if (disabled && !disabledReason) {
    throw new Error("Fieldset requires disabledReason when disabled.");
  }
  const reasonId = disabled && disabledReason ? `${generatedReasonId}-reason` : undefined;
  const describedBy = [rest["aria-describedby"], reasonId].filter(Boolean).join(" ") || undefined;

  return (
    <fieldset
      className={cx("workbench-fieldset", className)}
      disabled={disabled || undefined}
      {...rest}
      aria-describedby={describedBy}
    >
      <legend>{legend}</legend>
      {description && <p className="fieldset-description">{description}</p>}
      {children}
      {reasonId && <p className="disabled-reason" id={reasonId}>{disabledReason}</p>}
    </fieldset>
  );
}
