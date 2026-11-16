"use client";
// OverlapCircles (APSI, "two circles, one overlap") and SunburstProgress (évolvé mark as progress).
import { useId } from "react";
import type { LoopState } from "../contracts";
import { LOOP_STATES } from "../contracts";
import { cn } from "../lib/cn";
import { fmt, useUI } from "../provider";

export type VennPhase = "idle" | "running" | "compatible" | "shared";

/** Only a consented, non-empty APSI intersection is ever drawn. CSS motion; static under reduced motion. */
export function OverlapCircles({
  phase,
  label,
  overlapText,
  size = 320,
  onDark = false,
  decorative = false,
}: {
  phase: VennPhase;
  label: string;
  overlapText?: string;
  size?: number;
  onDark?: boolean;
  decorative?: boolean;
}) {
  const clip = useId().replace(/:/g, "");
  const stroke = onDark ? "var(--evolve-cream)" : "var(--evolve-navy)";
  const fill = onDark ? "rgb(255 254 240 / 0.08)" : "rgb(0 53 125 / 0.06)";
  const shift = phase === "compatible" ? 46 : 0;
  return (
    <figure className={cn(`venn-${phase}`, "m-0")} data-testid={decorative ? undefined : "overlap-circles"} data-phase={phase}>
      <svg
        {...(decorative ? { "aria-hidden": true } : { role: "img", "aria-label": label })}
        width="100%"
        style={{ maxWidth: size }}
        viewBox="-14 0 348 200"
      >
        <defs>
          <clipPath id={`venn-${clip}`}>
            <circle cx="120" cy="100" r="80" />
          </clipPath>
        </defs>
        <g className="venn-a" style={phase === "compatible" ? { transform: `translateX(-${shift}px)` } : undefined}>
          <circle cx="120" cy="100" r="80" fill={fill} stroke={stroke} strokeWidth="2.5" />
        </g>
        <g className="venn-b" style={phase === "compatible" ? { transform: `translateX(${shift}px)` } : undefined}>
          <circle cx="200" cy="100" r="80" fill={fill} stroke={stroke} strokeWidth="2.5" />
        </g>
        {phase === "shared" ? (
          <g className="reveal">
            <circle cx="200" cy="100" r="80" clipPath={`url(#venn-${clip})`} fill="var(--signal-escalated)" opacity="0.85" />
            {overlapText ? (
              <text x="160" y="106" textAnchor="middle" fontSize="15" fontWeight="700" fill="var(--neutral-950)" fontFamily="var(--type-ui)">
                {overlapText}
              </text>
            ) : null}
          </g>
        ) : null}
        {phase === "compatible" ? (
          <g className="reveal">
            <circle cx="160" cy="100" r="18" fill="var(--signal-compatible)" />
            <path d="M151 100l6 6 12-13" fill="none" stroke="#fff" strokeWidth="3.5" strokeLinecap="round" />
          </g>
        ) : null}
        {phase === "idle" ? <circle cx="160" cy="34" r="4" fill="var(--evolve-lime)" stroke={stroke} strokeWidth="1" /> : null}
      </svg>
    </figure>
  );
}

/** SunburstProgress: one dash per closed-loop state; lime = "you are here". Compact ring for headers/cards. */
export function SunburstProgress({ current, size = 96, showLabel = true }: { current: LoopState; size?: number; showLabel?: boolean }) {
  const { labels } = useUI();
  const idx = LOOP_STATES.indexOf(current);
  const total = LOOP_STATES.length;
  const text = fmt(labels.stepOf, { n: idx + 1, total });
  return (
    <div className="flex items-center gap-4" data-testid="sunburst">
      <svg role="img" aria-label={`${text}: ${labels.loopStates[current]}`} width={size} height={size} viewBox="-66 -66 132 132" className="shrink-0 rounded-full bg-navy">
        {LOOP_STATES.map((s, i) => {
          const a = (i / total) * 2 * Math.PI - Math.PI / 2;
          const here = i === idx;
          return (
            <line
              key={s}
              x1={Math.cos(a) * 26}
              y1={Math.sin(a) * 26}
              x2={Math.cos(a) * 52}
              y2={Math.sin(a) * 52}
              stroke={here ? "var(--evolve-lime)" : i < idx ? "var(--evolve-cream)" : "var(--evolve-mist)"}
              strokeOpacity={here || i < idx ? 1 : 0.5}
              strokeWidth={here ? 9 : 6}
              strokeLinecap="round"
            />
          );
        })}
      </svg>
      {showLabel ? (
        <div>
          <p className="text-sm text-ink-2">{text}</p>
          <p className="font-semibold text-ink">{labels.loopStates[current]}</p>
        </div>
      ) : null}
    </div>
  );
}
