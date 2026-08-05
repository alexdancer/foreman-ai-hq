import React from "react";

import { cx } from "./cx.js";

function containsNestedPanel(children) {
  let found = false;
  React.Children.forEach(children, (child) => {
    if (found || !React.isValidElement(child)) return;
    const classNames = typeof child.props?.className === "string"
      ? child.props.className.split(/\s+/)
      : [];
    if (child.type === Panel || classNames.includes("panel")) {
      found = true;
      return;
    }
    found = containsNestedPanel(child.props?.children);
  });
  return found;
}

// The workhorse container trio, wrapping the shared `.panel` / `.panel-header`
// / `.panel-body` classes.
//
// `Panel` is polymorphic (`as`, default <section>) so it also covers the
// `.pipeline-header.panel` <header> shape; extra classes and `id` pass through.
//
// `PanelHeader` renders the `<h3>` title plus an optional trailing marker.
// Most headers show a `.column-count`, so passing `count` renders that; for
// the few headers that need a different marker (a `.nav-badge`, a bare
// `<span>`), pass a ready-made node as `badge` and it wins.
export function Panel({ as: Component = "section", className, children, ...rest }) {
  if (containsNestedPanel(children)) {
    throw new Error("Panel cannot contain another Panel; use Fieldset or Disclosure.");
  }
  return (
    <Component className={cx("panel", className)} {...rest}>
      {children}
    </Component>
  );
}

export function PanelHeader({ title, count, badge }) {
  return (
    <div className="panel-header">
      <h3>{title}</h3>
      {badge != null
        ? badge
        : count != null
          ? <span className="column-count">{count}</span>
          : null}
    </div>
  );
}

export function PanelBody({ className, children, ...rest }) {
  return (
    <div className={cx("panel-body", className)} {...rest}>
      {children}
    </div>
  );
}
