"use client";

import { useEffect, useState } from "react";

type Score = {
  agent_id: number;
  trust_score: number;
  verdict: "TRUST" | "CAUTION" | "REJECT";
  scored_at: string;
};

const FALLBACK: Score[] = [
  { agent_id: 37506, trust_score: 92, verdict: "TRUST", scored_at: new Date(Date.now() - 60_000).toISOString() },
  { agent_id: 28559, trust_score: 64, verdict: "CAUTION", scored_at: new Date(Date.now() - 180_000).toISOString() },
  { agent_id: 31253, trust_score: 88, verdict: "TRUST", scored_at: new Date(Date.now() - 360_000).toISOString() },
  { agent_id: 14827, trust_score: 19, verdict: "REJECT", scored_at: new Date(Date.now() - 720_000).toISOString() },
  { agent_id: 9214, trust_score: 76, verdict: "TRUST", scored_at: new Date(Date.now() - 1200_000).toISOString() },
];

const VERDICT_COLOR: Record<string, string> = {
  TRUST: "text-trust",
  CAUTION: "text-caution",
  REJECT: "text-reject",
};

const VERDICT_BG: Record<string, string> = {
  TRUST: "bg-trust/10",
  CAUTION: "bg-caution/10",
  REJECT: "bg-reject/10",
};

function ago(iso: string): string {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function RecentActivity() {
  const [items, setItems] = useState<Score[]>(FALLBACK);

  useEffect(() => {
    let cancelled = false;
    function load() {
      fetch("/api/scores?limit=5")
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          if (cancelled || !data) return;
          const list: any[] = Array.isArray(data) ? data : data.agents || data.scores || data.items || [];
          if (list.length === 0) return;
          const mapped: Score[] = list.slice(0, 5).map((x) => ({
            agent_id: x.agent_id,
            trust_score: x.trust_score ?? 0,
            verdict: (x.verdict || "CAUTION") as Score["verdict"],
            scored_at: x.scored_at || new Date().toISOString(),
          }));
          setItems(mapped);
        })
        .catch(() => {});
    }
    load();
    const interval = setInterval(load, 30_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <section className="py-20 px-6 lg:px-8">
      <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-12 gap-8">
        <div className="md:col-span-5">
          <p className="text-sm text-muted mb-4 inline-flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-trust animate-pulse" />
            Live
          </p>
          <h2
            className="font-display font-light text-text"
            style={{ fontSize: "clamp(1.75rem, 4vw, 2.75rem)", lineHeight: "1.1", letterSpacing: "-0.03em" }}
          >
            Latest scoring
            <br />
            <span className="italic">on Base.</span>
          </h2>
          <p className="mt-5 text-sm text-muted font-light leading-relaxed max-w-sm">
            Every score is published on-chain via TrustGate, backed by ETH staked
            on the SentinelNetStaking contract, and challengeable for 72 hours.
          </p>
        </div>

        <div className="md:col-span-7 surface-card rounded-3xl divide-y divide-border overflow-hidden">
          {items.map((item, i) => (
            <a
              key={`${item.agent_id}-${item.scored_at}-${i}`}
              href={`/agent/${item.agent_id}`}
              className="flex items-center justify-between px-6 py-5 hover:bg-text/[0.02] transition-colors"
            >
              <div className="flex items-center gap-4 min-w-0">
                <span
                  className={`inline-flex items-center justify-center w-2.5 h-2.5 rounded-full ${
                    item.verdict === "TRUST"
                      ? "bg-trust"
                      : item.verdict === "CAUTION"
                      ? "bg-caution"
                      : "bg-reject"
                  }`}
                />
                <div className="min-w-0">
                  <div className="ticker text-text">agent #{item.agent_id}</div>
                  <div className="text-xs text-muted mt-0.5">
                    <span className={VERDICT_COLOR[item.verdict]}>{item.verdict.toLowerCase()}</span>
                    <span className="ml-1.5">· score {item.trust_score}</span>
                    <span className="ml-1.5">· {ago(item.scored_at)}</span>
                  </div>
                </div>
              </div>
              <span
                className={`text-[10px] uppercase tracking-widest px-2.5 py-1 rounded-full ${VERDICT_BG[item.verdict]} ${VERDICT_COLOR[item.verdict]}`}
              >
                {item.verdict}
              </span>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}
