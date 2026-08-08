import React from "react";

import { cx } from "./cx.js";

export function DataTable({ label, columns, minWidth, className, children, style, ...rest }) {
  const tableStyle = columns || minWidth
    ? {
        ...style,
        ...(columns ? { "--data-table-columns": columns } : {}),
        ...(minWidth ? { "--data-table-min-width": minWidth } : {}),
      }
    : style;
  return (
    <div className="data-table-scroll">
      <div
        className={cx("data-table", className)}
        role="table"
        aria-label={label}
        style={tableStyle}
        {...rest}
      >
        {children}
      </div>
    </div>
  );
}

export function Row({ header = false, className, children, ...rest }) {
  return (
    <div className={cx("data-table-row", header && "data-table-head", className)} role="row" {...rest}>
      {children}
    </div>
  );
}

export function ColumnHead({ className, children, ...rest }) {
  return (
    <div className={cx("data-table-column-head", className)} role="columnheader" {...rest}>
      {children}
    </div>
  );
}

export function DataCell({ className, children, ...rest }) {
  return (
    <div className={cx("data-table-cell", className)} role="cell" {...rest}>
      {children}
    </div>
  );
}
