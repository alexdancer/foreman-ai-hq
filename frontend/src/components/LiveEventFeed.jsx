import React, { useEffect, useRef } from "react";

import { EventRow } from "./ui/index.js";

const ISO_TIME = /T(\d{2}:\d{2}:\d{2})/;

export function liveEventText(summary) {
  if (summary == null) return "";
  if (typeof summary === "string") return summary;
  return summary.text || "";
}

export function liveEventTime(createdAt) {
  // Slice the wire string rather than constructing a Date: the rest of the
  // portal renders server timestamps verbatim, and a local-timezone shift here
  // would silently disagree with the Session Report next to it.
  const match = ISO_TIME.exec(createdAt || "");
  return match ? match[1] : "";
}

export function LiveEventRow({ event }) {
  const text = liveEventText(event.detail_summary);
  return (
    <EventRow
      time={liveEventTime(event.created_at) || "--:--:--"}
      kind={event.kind}
      note={event.kind === "token" ? " · provisional; final total recorded on completion." : undefined}
    >
      {text || event.title || event.kind}
    </EventRow>
  );
}

export function LiveEventFeed({ events, active, emptyText = "Waiting for live Worker events…" }) {
  const listRef = useRef(null);
  const pinnedRef = useRef(true);

  useEffect(() => {
    const el = listRef.current;
    // Only follow the tail when the operator is already reading it. Yanking the
    // viewport back on every append makes older events impossible to read.
    if (el && pinnedRef.current) el.scrollTop = el.scrollHeight;
  }, [events.length]);

  const onScroll = (scrollEvent) => {
    const el = scrollEvent.currentTarget;
    pinnedRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 24;
  };

  if (events.length === 0) {
    return <p className="muted live-feed-empty">{active ? emptyText : "No live events."}</p>;
  }

  return (
    <ul className="live-feed-list" ref={listRef} onScroll={onScroll}>
      {events.map((event, index) => (
        <LiveEventRow key={event.id ?? `${event.created_at}-${event.kind}-${index}`} event={event} />
      ))}
    </ul>
  );
}
