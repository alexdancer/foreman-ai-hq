import React from "react";

import { cx } from "./cx.js";

export function EventRow({
  as: Component = "li",
  time = "--:--:--",
  kind = "event",
  note,
  className,
  children,
  ...rest
}) {
  return (
    <Component className={cx("live-event", `live-event-${kind}`, "event-row", className)} {...rest}>
      <span className="live-event-time">{time}</span>
      <span className="live-event-kind">{kind}</span>
      <span className="live-event-body">
        {children}
        {note && <em className="live-event-note">{note}</em>}
      </span>
    </Component>
  );
}
