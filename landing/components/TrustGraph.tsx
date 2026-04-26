"use client";

import { useEffect, useMemo, useState } from "react";

type Node = { id: number; x: number; y: number; r: number; verdict: "trust" | "caution" | "reject" };
type Edge = { from: number; to: number };

function generateFromAgents(
  agents: Array<{ verdict?: string; agent_id: number }>,
  seed = 7891
): { nodes: Node[]; edges: Edge[] } {
  let s = seed;
  const rand = () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };

  const buckets = { trust: [] as typeof agents, caution: [] as typeof agents, reject: [] as typeof agents };
  for (const a of agents) {
    const v = (a.verdict || "").toLowerCase();
    if (v === "trust") buckets.trust.push(a);
    else if (v === "caution") buckets.caution.push(a);
    else buckets.reject.push(a);
  }

  const target = 90;
  const trustCount = Math.max(8, Math.min(Math.floor(target * (buckets.trust.length / agents.length)), 60));
  const cautionCount = Math.max(6, Math.min(Math.floor(target * (buckets.caution.length / agents.length)), 30));
  const rejectCount = Math.max(8, Math.min(target - trustCount - cautionCount, 60));

  const clusters = [
    { cx: 25, cy: 50, count: trustCount, verdict: "trust" as const },
    { cx: 55, cy: 35, count: cautionCount, verdict: "caution" as const },
    { cx: 78, cy: 65, count: rejectCount, verdict: "reject" as const },
  ];

  const nodes: Node[] = [];
  let id = 0;
  for (const c of clusters) {
    for (let i = 0; i < c.count; i++) {
      const angle = rand() * Math.PI * 2;
      const radius = Math.pow(rand(), 0.7) * 18;
      nodes.push({
        id: id++,
        x: c.cx + Math.cos(angle) * radius,
        y: c.cy + Math.sin(angle) * radius,
        r: 1 + rand() * 1.6,
        verdict: c.verdict,
      });
    }
  }

  const edges: Edge[] = [];
  for (let i = 0; i < nodes.length; i++) {
    const a = nodes[i];
    const candidates = nodes
      .map((b, j) => ({ j, d: Math.hypot(a.x - b.x, a.y - b.y), b }))
      .filter((c) => c.j !== i)
      .sort((x, y) => x.d - y.d);
    const links = 1 + Math.floor(rand() * 2);
    for (let k = 0; k < links && k < candidates.length; k++) {
      const c = candidates[k];
      if (c.d < 12 && rand() < 0.7) {
        edges.push({ from: i, to: c.j });
      }
    }
  }

  return { nodes, edges };
}

const COLOR: Record<Node["verdict"], string> = {
  trust: "#10B981",
  caution: "#F59E0B",
  reject: "#EF4444",
};

const FALLBACK_AGENTS = Array.from({ length: 90 }, (_, i) => ({
  agent_id: i,
  verdict: i < 50 ? "TRUST" : i < 70 ? "CAUTION" : "REJECT",
}));

export default function TrustGraph({ className = "" }: { className?: string }) {
  const [agents, setAgents] = useState<Array<{ verdict?: string; agent_id: number }>>(FALLBACK_AGENTS);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/scores?limit=200")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (cancelled || !data) return;
        const list = Array.isArray(data) ? data : data.agents || data.scores || data.items || [];
        if (list.length === 0) return;
        setAgents(list.map((x: any) => ({ agent_id: x.agent_id, verdict: x.verdict })));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const { nodes, edges } = useMemo(() => generateFromAgents(agents), [agents]);

  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      <g opacity="0.18">
        {edges.map((e, i) => {
          const a = nodes[e.from];
          const b = nodes[e.to];
          if (!a || !b) return null;
          const sameCluster = a.verdict === b.verdict;
          return (
            <line
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={sameCluster ? COLOR[a.verdict] : "currentColor"}
              strokeWidth={sameCluster ? 0.08 : 0.05}
              vectorEffect="non-scaling-stroke"
            />
          );
        })}
      </g>
      <g>
        {nodes.map((n) => (
          <circle
            key={n.id}
            cx={n.x}
            cy={n.y}
            r={n.r}
            fill={COLOR[n.verdict]}
            opacity={n.verdict === "reject" ? 0.85 : n.verdict === "caution" ? 0.75 : 0.65}
          >
            <animate
              attributeName="opacity"
              values={`${0.4 + (n.id % 5) * 0.05};${0.85};${0.4 + (n.id % 5) * 0.05}`}
              dur={`${4 + (n.id % 6)}s`}
              repeatCount="indefinite"
              begin={`${(n.id % 10) * 0.3}s`}
            />
          </circle>
        ))}
      </g>
    </svg>
  );
}
