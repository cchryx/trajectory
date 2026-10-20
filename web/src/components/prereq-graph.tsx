"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import type { GraphEdge, GraphNode } from "@/lib/api";

const NODE_W = 150;
const NODE_H = 46;
const COL_GAP = 70;
const ROW_GAP = 14;
const PAD = 12;
const GROUP_COLORS = ["#0b7a62", "#a16207", "#7c3aed", "#be185d", "#2563eb"];

// Other campuses (UTM ends in 5, UTSC in 3) clutter the graph, so they start hidden.
const isMainCampus = (code: string) => /[HY]1$/.test(code);

export function PrereqGraph({
  rootId,
  nodes,
  edges,
}: {
  rootId: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}) {
  const router = useRouter();
  const [showAll, setShowAll] = useState(false);

  const layout = useMemo(() => {
    const keep = new Set(
      nodes
        .filter((n) => n.id === rootId || showAll || isMainCampus(n.code))
        .map((n) => n.id),
    );
    const shown = edges.filter((e) => keep.has(e.from) && keep.has(e.to));

    // A node's column is how many steps back it is from the course.
    const level = new Map<string, number>([[rootId, 0]]);
    for (const e of [...shown].sort((a, b) => a.level - b.level)) {
      if (!level.has(e.from)) level.set(e.from, e.level);
    }
    const maxLevel = Math.max(0, ...level.values());
    const columns: GraphNode[][] = Array.from(
      { length: maxLevel + 1 },
      () => [],
    );
    for (const n of nodes) {
      const l = level.get(n.id);
      if (l !== undefined && keep.has(n.id)) columns[l].push(n);
    }
    for (const col of columns) col.sort((a, b) => a.code.localeCompare(b.code));

    const pos = new Map<string, { x: number; y: number }>();
    const tallest = Math.max(1, ...columns.map((c) => c.length));
    const height = PAD * 2 + tallest * NODE_H + (tallest - 1) * ROW_GAP;
    columns.forEach((col, l) => {
      const x = PAD + (maxLevel - l) * (NODE_W + COL_GAP);
      const colHeight = col.length * NODE_H + (col.length - 1) * ROW_GAP;
      const top = (height - colHeight) / 2;
      col.forEach((n, i) => {
        pos.set(n.id, { x, y: top + i * (NODE_H + ROW_GAP) });
      });
    });
    const width = PAD * 2 + (maxLevel + 1) * NODE_W + maxLevel * COL_GAP;
    const byId = new Map(nodes.map((n) => [n.id, n]));
    return { shown, pos, width, height, byId };
  }, [nodes, edges, rootId, showAll]);

  const hidden = nodes.filter((n) => !isMainCampus(n.code)).length;
  if (edges.length === 0) {
    return <p className="text-sm text-muted">No prerequisites listed.</p>;
  }

  return (
    <div className="grid gap-2">
      <div className="overflow-x-auto rounded-lg border border-line bg-surface">
        <svg
          width={layout.width}
          height={layout.height}
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          role="img"
          aria-label="Prerequisite graph. The same list is written out below."
        >
          {layout.shown.map((e) => {
            const a = layout.pos.get(e.from);
            const b = layout.pos.get(e.to);
            if (!a || !b) return null;
            const x1 = a.x + NODE_W;
            const y1 = a.y + NODE_H / 2;
            const x2 = b.x;
            const y2 = b.y + NODE_H / 2;
            const mid = (x1 + x2) / 2;
            return (
              <path
                key={`${e.from}-${e.to}-${e.group}`}
                d={`M${x1} ${y1} C${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`}
                fill="none"
                stroke={GROUP_COLORS[e.group % GROUP_COLORS.length]}
                strokeWidth={1.5}
                opacity={0.7}
              />
            );
          })}
          {[...layout.pos.entries()].map(([id, p]) => {
            const n = layout.byId.get(id);
            if (!n) return null;
            const root = id === rootId;
            const go = () => {
              if (n.loaded && !root)
                router.push(`/courses/${encodeURIComponent(id)}`);
            };
            return (
              // biome-ignore lint/a11y/noStaticElementInteractions: the same links are in the list below
              <g
                key={id}
                transform={`translate(${p.x},${p.y})`}
                onClick={go}
                style={{ cursor: n.loaded && !root ? "pointer" : "default" }}
              >
                <rect
                  width={NODE_W}
                  height={NODE_H}
                  rx={6}
                  fill={root ? "var(--accent-soft)" : "var(--surface)"}
                  stroke={root ? "var(--accent)" : "var(--line)"}
                  strokeDasharray={n.loaded ? undefined : "4 3"}
                />
                <text
                  x={10}
                  y={19}
                  fontSize={13}
                  fontWeight={700}
                  fill="var(--foreground)"
                >
                  {n.code}
                </text>
                <text x={10} y={36} fontSize={11} fill="var(--muted)">
                  {(n.title ?? "Not loaded").slice(0, 22)}
                  {(n.title ?? "").length > 22 ? "…" : ""}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted">
        <span>Lines with the same color: any one of them is enough.</span>
        <span>Dashed box: not in our course list yet.</span>
        {hidden > 0 && (
          <button
            type="button"
            className="text-accent underline"
            onClick={() => setShowAll(!showAll)}
          >
            {showAll
              ? "Hide other campuses"
              : `Show other campuses (${hidden})`}
          </button>
        )}
      </div>
    </div>
  );
}
