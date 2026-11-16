"use client";
// PedigreeGraph (docs/09 §4.2, §5): SVG render of the GA4GH-style pedigree returned by
// GET /api/counselor/cases/{id} -> pedigree {nodes, edges, F, relationship}. R-UX-2.
// - Standard symbols: square = male, circle = female, diamond = sex not recorded; filled = affected.
// - Consanguineous union = double line; the consanguinity loop (paths from each partner to their shared
//   ancestors) is drawn dashed in the info ink and listed in the legend.
// - F is NOT rendered here: it arrives through the `context` slot as a LockedNumber (P-01/P-03, genome-wide context only).
// - Layout is graph structure only (generations + ordering). No arithmetic on any risk value happens here (P-02).
// - Accessible: role="img" with title/description, plus a text list of every individual.
import { useId, useMemo, type ReactNode } from "react";
import { cn } from "../lib/cn";

export interface PedigreeNode {
  id: string;
  sex: "MALE" | "FEMALE" | "UNKNOWN_SEX" | string;
  affected: boolean;
  role: "partner_A" | "partner_B" | "relative" | string;
}

export interface PedigreeEdge {
  from: string;
  to: string;
  kind: "parent_of" | "couple" | string;
  consanguineous?: boolean;
}

export interface PedigreeLabels {
  partnerA: string;
  partnerB: string;
  relative: string;
  male: string;
  female: string;
  unknownSex: string;
  affected: string;
  unaffected: string;
  union: string;
  consanguineousUnion: string;
  loop: string;
  legend: string;
  listHeading: string;
  parents: string;
  noParents: string;
  unplaced: string;
  /** "{count} people" */
  people: string;
}

export const DEFAULT_PEDIGREE_LABELS: PedigreeLabels = {
  partnerA: "Partner A",
  partnerB: "Partner B",
  relative: "Relative",
  male: "Male",
  female: "Female",
  unknownSex: "Sex not recorded",
  affected: "Affected",
  unaffected: "Unaffected",
  union: "Union",
  consanguineousUnion: "Consanguineous union (double line)",
  loop: "Consanguinity loop: paths to shared ancestors",
  legend: "Legend",
  listHeading: "Individuals in this pedigree",
  parents: "Parents",
  noParents: "Not recorded",
  unplaced: "Position in the family not recorded",
  people: "{count} people",
};

const SP = 96; // horizontal spacing between symbols
const GAP = 112; // vertical spacing between generations
const R = 18; // symbol half-size
const PAD = 48;

interface Placed {
  node: PedigreeNode;
  x: number;
  y: number;
  gen: number;
  unplaced: boolean;
}

interface Layout {
  placed: Map<string, Placed>;
  sibships: { parents: string[]; children: string[] }[];
  couples: { a: string; b: string; consanguineous: boolean }[];
  loopNodes: Set<string>;
  width: number;
  height: number;
}

function computeLayout(nodes: PedigreeNode[], edges: PedigreeEdge[]): Layout {
  const ids = new Set(nodes.map((n) => n.id));
  const parentsOf = new Map<string, string[]>();
  const childrenOf = new Map<string, string[]>();
  const couples: Layout["couples"] = [];
  for (const e of edges) {
    if (!ids.has(e.from) || !ids.has(e.to)) continue;
    if (e.kind === "parent_of") {
      parentsOf.set(e.to, [...(parentsOf.get(e.to) ?? []), e.from]);
      childrenOf.set(e.from, [...(childrenOf.get(e.from) ?? []), e.to]);
    } else if (e.kind === "couple") {
      couples.push({ a: e.from, b: e.to, consanguineous: !!e.consanguineous });
    }
  }
  const coupled = new Set(couples.flatMap((c) => [c.a, c.b]));
  const connected = (id: string) => parentsOf.has(id) || childrenOf.has(id) || coupled.has(id);

  // Generations: top-down from founders, then pull parentless spouses down next to their partner's generation.
  const gen = new Map<string, number>();
  const genOf = (id: string, seen = new Set<string>()): number => {
    if (gen.has(id)) return gen.get(id)!;
    if (seen.has(id)) return 0;
    seen.add(id);
    const ps = parentsOf.get(id) ?? [];
    const g = ps.length ? Math.max(...ps.map((p) => genOf(p, seen))) + 1 : 0;
    gen.set(id, g);
    return g;
  };
  nodes.forEach((n) => genOf(n.id));
  for (let pass = 0; pass < nodes.length; pass++) {
    let changed = false;
    for (const n of nodes) {
      if (parentsOf.has(n.id)) continue;
      const kids = childrenOf.get(n.id);
      if (kids?.length) {
        const g = Math.min(...kids.map((k) => gen.get(k)!)) - 1;
        if (g !== gen.get(n.id)) {
          gen.set(n.id, g);
          changed = true;
        }
      }
    }
    for (const c of couples) {
      const ga = gen.get(c.a)!;
      const gb = gen.get(c.b)!;
      if (ga !== gb) {
        const target = Math.max(ga, gb);
        for (const [who, g] of [[c.a, ga], [c.b, gb]] as const) {
          if (!parentsOf.has(who) && g !== target) {
            gen.set(who, target);
            changed = true;
          }
        }
      }
    }
    if (!changed) break;
  }
  const minGen = Math.min(...nodes.filter((n) => connected(n.id)).map((n) => gen.get(n.id)!), 0);
  const maxGen = Math.max(...nodes.filter((n) => connected(n.id)).map((n) => gen.get(n.id)! - minGen), 0);

  const x = new Map<string, number>();
  const byGen = (g: number) => nodes.filter((n) => connected(n.id) && gen.get(n.id)! - minGen === g);
  const roleRank = (n: PedigreeNode) => (n.role === "partner_A" ? 0 : n.role === "partner_B" ? 1 : 2);

  // Bottom generation: partner A, partner B, then others in input order.
  const bottom = byGen(maxGen).sort((a, b) => roleRank(a) - roleRank(b));
  bottom.forEach((n, i) => x.set(n.id, i * SP));

  // Upper generations: co-parent pairs centered over their children; pairs never overlap.
  for (let g = maxGen - 1; g >= 0; g--) {
    const members = byGen(g);
    const used = new Set<string>();
    const units: { ids: string[]; want: number }[] = [];
    for (const n of members) {
      if (used.has(n.id)) continue;
      const kids = (childrenOf.get(n.id) ?? []).filter((k) => x.has(k));
      const partner = members.find(
        (m) => m.id !== n.id && !used.has(m.id) && (childrenOf.get(m.id) ?? []).some((k) => kids.includes(k)),
      );
      const ids = partner ? [n.id, partner.id] : [n.id];
      ids.forEach((i) => used.add(i));
      const allKids = [...new Set(ids.flatMap((i) => (childrenOf.get(i) ?? []).filter((k) => x.has(k))))];
      const want = allKids.length ? allKids.reduce((s, k) => s + x.get(k)!, 0) / allKids.length : Number.POSITIVE_INFINITY;
      units.push({ ids, want });
    }
    const finite = units.filter((u) => Number.isFinite(u.want));
    const mid = finite.length ? finite.reduce((s, u) => s + u.want, 0) / finite.length : 0;
    units.sort((a, b) => a.want - b.want);
    let cursor = Number.NEGATIVE_INFINITY;
    for (const u of units) {
      // The member who has parents of their own sits toward the middle (shorter loop lines).
      if (u.ids.length === 2) {
        const [p, q] = u.ids;
        const pInner = parentsOf.has(p) && !parentsOf.has(q);
        const qInner = parentsOf.has(q) && !parentsOf.has(p);
        const leftSide = u.want < mid;
        if ((leftSide && pInner) || (!leftSide && qInner)) u.ids = [q, p];
      }
      const width = (u.ids.length - 1) * SP;
      const want = Number.isFinite(u.want) ? u.want : cursor + SP;
      const start = Math.max(want - width / 2, Number.isFinite(cursor) ? cursor + SP : want - width / 2);
      u.ids.forEach((id, i) => x.set(id, start + i * SP));
      cursor = start + width;
    }
  }

  // Unplaced individuals (no edges): a separate lane after the bottom generation.
  const unplacedNodes = nodes.filter((n) => !connected(n.id));
  const minX = Math.min(...[...x.values()], 0);
  const maxX = Math.max(...[...x.values()], 0);
  unplacedNodes.forEach((n, i) => x.set(n.id, maxX + SP * (i + 1.5)));

  const placed = new Map<string, Placed>();
  for (const n of nodes) {
    const unplaced = !connected(n.id);
    const g = unplaced ? maxGen : gen.get(n.id)! - minGen;
    placed.set(n.id, { node: n, x: x.get(n.id)! - minX + PAD + R, y: PAD + R + g * GAP, gen: g, unplaced });
  }

  // Sibships: children grouped by their exact parent set.
  const sibMap = new Map<string, { parents: string[]; children: string[] }>();
  for (const [child, ps] of parentsOf) {
    const key = [...ps].sort().join("|");
    const s = sibMap.get(key) ?? { parents: [...ps].sort(), children: [] };
    s.children.push(child);
    sibMap.set(key, s);
  }

  // Consanguinity loop: ancestors shared by both partners, and every path down from them to a partner.
  const ancestors = (id: string): Set<string> => {
    const out = new Set<string>();
    const stack = [...(parentsOf.get(id) ?? [])];
    while (stack.length) {
      const p = stack.pop()!;
      if (out.has(p)) continue;
      out.add(p);
      stack.push(...(parentsOf.get(p) ?? []));
    }
    return out;
  };
  const loopNodes = new Set<string>();
  for (const c of couples) {
    const aa = ancestors(c.a);
    const ab = ancestors(c.b);
    const shared = [...aa].filter((i) => ab.has(i));
    if (!shared.length) continue;
    const sharedSet = new Set(shared);
    for (const id of [...aa, ...ab, c.a, c.b]) {
      const anc = ancestors(id);
      if (sharedSet.has(id) || [...anc].some((i) => sharedSet.has(i))) loopNodes.add(id);
    }
  }

  const xs = [...placed.values()].map((p) => p.x);
  const ys = [...placed.values()].map((p) => p.y);
  return {
    placed,
    sibships: [...sibMap.values()],
    couples,
    loopNodes,
    width: Math.max(...xs, 0) + R + PAD,
    height: Math.max(...ys, 0) + R + PAD + 28,
  };
}

function Symbol({ p, loop }: { p: Placed; loop: boolean }) {
  const { node, x, y } = p;
  const partner = node.role === "partner_A" || node.role === "partner_B";
  const common = {
    fill: node.affected ? "currentColor" : "var(--surface-1)",
    stroke: "currentColor",
    strokeWidth: partner ? 3.5 : 2,
    strokeDasharray: p.unplaced ? "4 3" : undefined,
  };
  const shape =
    node.sex === "MALE" ? (
      <rect x={x - R} y={y - R} width={R * 2} height={R * 2} {...common} />
    ) : node.sex === "FEMALE" ? (
      <circle cx={x} cy={y} r={R} {...common} />
    ) : (
      <polygon points={`${x},${y - R - 3} ${x + R + 3},${y} ${x},${y + R + 3} ${x - R - 3},${y}`} {...common} />
    );
  return (
    <g className="text-ink" data-pedigree-node={node.id} data-role={node.role} data-affected={node.affected || undefined} data-loop={loop || undefined}>
      {loop ? <circle cx={x} cy={y} r={R + 8} fill="none" stroke="var(--signal-info-ink)" strokeWidth={2} strokeDasharray="5 4" className="pedigree-loop" /> : null}
      {shape}
    </g>
  );
}

export function PedigreeGraph({
  nodes,
  edges,
  title,
  context,
  labels: labelOverrides,
  className,
  testId = "pedigree-graph",
}: {
  nodes: PedigreeNode[];
  edges: PedigreeEdge[];
  /** Accessible title of the drawing (e.g. "Family tree, first cousins"). */
  title: string;
  /** Optional caption area, e.g. relationship + F rendered through LockedNumber (genome-wide context only). */
  context?: ReactNode;
  labels?: Partial<PedigreeLabels>;
  className?: string;
  testId?: string;
}) {
  const labels = { ...DEFAULT_PEDIGREE_LABELS, ...labelOverrides };
  const id = useId();
  const layout = useMemo(() => computeLayout(nodes, edges), [nodes, edges]);
  const nameOf = (n: PedigreeNode) => (n.role === "partner_A" ? labels.partnerA : n.role === "partner_B" ? labels.partnerB : n.id);
  const sexOf = (n: PedigreeNode) => (n.sex === "MALE" ? labels.male : n.sex === "FEMALE" ? labels.female : labels.unknownSex);
  const parentsOf = (cid: string) => edges.filter((e) => e.kind === "parent_of" && e.to === cid).map((e) => e.from);
  const anyConsanguineous = layout.couples.some((c) => c.consanguineous);
  const hasLoop = layout.loopNodes.size > 0;
  const hasUnplaced = [...layout.placed.values()].some((p) => p.unplaced);
  const desc = [
    labels.people.replace("{count}", String(nodes.length)),
    anyConsanguineous ? labels.consanguineousUnion : null,
    hasLoop ? labels.loop : null,
  ]
    .filter(Boolean)
    .join(". ");

  const P = layout.placed;
  const line = { stroke: "currentColor", strokeWidth: 2, fill: "none" } as const;

  return (
    <figure className={cn("space-y-4", className)} data-testid={testId}>
      <div className="overflow-x-auto rounded-lg border border-line bg-surface-1" dir="ltr">
        <svg
          role="img"
          aria-labelledby={`${id}-t ${id}-d`}
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          width={layout.width}
          height={layout.height}
          className="mx-auto block max-w-none text-ink"
          style={{ minWidth: Math.min(layout.width, 320) }}
        >
          <title id={`${id}-t`}>{title}</title>
          <desc id={`${id}-d`}>{desc}</desc>
          {/* Sibships: mating line between parents, descent line to a sibship bar, drops to each child. */}
          {layout.sibships.map((s, i) => {
            const ps = s.parents.map((p) => P.get(p)).filter((p): p is Placed => !!p);
            const cs = s.children.map((c) => P.get(c)).filter((c): c is Placed => !!c);
            if (!ps.length || !cs.length) return null;
            const py = ps[0].y;
            const left = Math.min(...ps.map((p) => p.x));
            const right = Math.max(...ps.map((p) => p.x));
            const mx = (left + right) / 2;
            const barY = py + GAP / 2;
            const cl = Math.min(mx, ...cs.map((c) => c.x));
            const cr = Math.max(mx, ...cs.map((c) => c.x));
            const loopDescent = s.parents.some((p) => layout.loopNodes.has(p));
            return (
              <g key={i} className="text-ink">
                {ps.length > 1 ? <line x1={left + R} y1={py} x2={right - R} y2={py} {...line} /> : null}
                <line x1={mx} y1={ps.length > 1 ? py : py + R} x2={mx} y2={barY} {...line} />
                <line x1={cl} y1={barY} x2={cr} y2={barY} {...line} />
                {cs.map((c) => {
                  const onLoop = loopDescent && layout.loopNodes.has(c.node.id);
                  return (
                    <line
                      key={c.node.id}
                      x1={c.x}
                      y1={barY}
                      x2={c.x}
                      y2={c.y - R - (c.node.sex === "UNKNOWN_SEX" ? 3 : 0)}
                      {...line}
                      stroke={onLoop ? "var(--signal-info-ink)" : "currentColor"}
                      strokeWidth={onLoop ? 3 : 2}
                      strokeDasharray={onLoop ? "6 4" : undefined}
                      data-loop-edge={onLoop || undefined}
                    />
                  );
                })}
              </g>
            );
          })}
          {/* Partner union: double line when consanguineous (standard notation). */}
          {layout.couples.map((c, i) => {
            const a = P.get(c.a);
            const b = P.get(c.b);
            if (!a || !b) return null;
            const [l, r] = a.x < b.x ? [a, b] : [b, a];
            return (
              <g key={`c${i}`} className="text-ink" data-union={c.consanguineous ? "consanguineous" : "union"}>
                {c.consanguineous ? (
                  <>
                    <line x1={l.x + R} y1={l.y - 3} x2={r.x - R} y2={r.y - 3} {...line} />
                    <line x1={l.x + R} y1={l.y + 3} x2={r.x - R} y2={r.y + 3} {...line} />
                  </>
                ) : (
                  <line x1={l.x + R} y1={l.y} x2={r.x - R} y2={r.y} {...line} />
                )}
              </g>
            );
          })}
          {[...P.values()].map((p) => (
            <Symbol key={p.node.id} p={p} loop={layout.loopNodes.has(p.node.id)} />
          ))}
          {[...P.values()].map((p) => {
            const partner = p.node.role === "partner_A" || p.node.role === "partner_B";
            return (
              <text
                key={`t-${p.node.id}`}
                x={p.x}
                y={p.y + R + 20}
                textAnchor="middle"
                className={cn(partner ? "fill-ink font-semibold" : "fill-ink-2 font-mono")}
                style={{ fontSize: partner ? 14 : 11 }}
              >
                {nameOf(p.node)}
              </text>
            );
          })}
        </svg>
      </div>

      <figcaption className="space-y-3 text-sm text-ink">
        {context ? <div data-testid="pedigree-context">{context}</div> : null}
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.08em] text-ink-2">{labels.legend}</p>
          <ul className="flex flex-wrap gap-x-5 gap-y-2" data-testid="pedigree-legend">
            <li className="inline-flex items-center gap-2">
              <svg aria-hidden width="16" height="16" className="text-ink"><rect x="2" y="2" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" /></svg>
              {labels.male}
            </li>
            <li className="inline-flex items-center gap-2">
              <svg aria-hidden width="16" height="16" className="text-ink"><circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" strokeWidth="2" /></svg>
              {labels.female}
            </li>
            <li className="inline-flex items-center gap-2">
              <svg aria-hidden width="16" height="16" className="text-ink"><polygon points="8,1 15,8 8,15 1,8" fill="none" stroke="currentColor" strokeWidth="2" /></svg>
              {labels.unknownSex}
            </li>
            <li className="inline-flex items-center gap-2">
              <svg aria-hidden width="16" height="16" className="text-ink"><rect x="2" y="2" width="12" height="12" fill="currentColor" stroke="currentColor" strokeWidth="2" /></svg>
              {labels.affected}
            </li>
            {anyConsanguineous ? (
              <li className="inline-flex items-center gap-2">
                <svg aria-hidden width="24" height="16" className="text-ink">
                  <line x1="0" y1="5" x2="24" y2="5" stroke="currentColor" strokeWidth="2" />
                  <line x1="0" y1="11" x2="24" y2="11" stroke="currentColor" strokeWidth="2" />
                </svg>
                {labels.consanguineousUnion}
              </li>
            ) : null}
            {hasLoop ? (
              <li className="inline-flex items-center gap-2" data-testid="pedigree-loop-legend">
                <svg aria-hidden width="24" height="16">
                  <line x1="0" y1="8" x2="24" y2="8" stroke="var(--signal-info-ink)" strokeWidth="3" strokeDasharray="6 4" />
                </svg>
                {labels.loop}
              </li>
            ) : null}
            {hasUnplaced ? (
              <li className="inline-flex items-center gap-2">
                <svg aria-hidden width="16" height="16" className="text-ink"><rect x="2" y="2" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="3 2" /></svg>
                {labels.unplaced}
              </li>
            ) : null}
          </ul>
        </div>
        <details className="rounded-md bg-surface-2 p-3">
          <summary className="min-h-11 cursor-pointer content-center font-semibold">{labels.listHeading}</summary>
          <ul className="mt-2 space-y-1" data-testid="pedigree-list">
            {nodes.map((n) => {
              const ps = parentsOf(n.id);
              return (
                <li key={n.id}>
                  <span className="font-semibold">{nameOf(n)}</span>
                  {n.role === "relative" ? null : <span className="font-mono text-xs text-ink-2"> ({n.id})</span>} · {sexOf(n)} ·{" "}
                  {n.affected ? labels.affected : labels.unaffected} · {labels.parents}:{" "}
                  {ps.length ? <span className="font-mono text-xs">{ps.join(", ")}</span> : labels.noParents}
                  {layout.placed.get(n.id)?.unplaced ? ` · ${labels.unplaced}` : null}
                </li>
              );
            })}
          </ul>
        </details>
      </figcaption>
    </figure>
  );
}
