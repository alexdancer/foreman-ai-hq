import React from "react";

import { cx } from "./cx.js";

const TONE_GLYPHS = {
  accepted: "✓",
  complete: "✓",
  green: "✓",
  mint: "✓",
  success: "✓",
  blocked: "▲",
  proposed: "▲",
  warn: "▲",
  warning: "▲",
  yellow: "▲",
  danger: "✕",
  error: "✕",
  failed: "✕",
  red: "✕",
  blue: "◐",
  info: "◐",
  running: "◐",
  orchestration: "▮",
  purple: "▮",
  violet: "▮",
};

export function StatusPill({ tone = "neutral", glyph, label, className, ...rest }) {
  if (label == null || (typeof label === "string" && !label.trim())) {
    throw new Error("StatusPill requires a visible text label.");
  }
  const visibleGlyph = glyph || TONE_GLYPHS[tone] || "▮";
  return (
    <span className={cx("status-pill", `status-pill-${tone}`, className)} {...rest}>
      <span className="status-pill-glyph" aria-hidden="true">{visibleGlyph}</span>
      <span className="status-pill-label">{label}</span>
    </span>
  );
}
