"use client";

import { useEffect, useState } from "react";
import CountUp from "./CountUp";
import TrustGraph from "./TrustGraph";

type Stats = {
  agents_scored: number;
  sybil_flagged: number;
  contagion_affected: number;
  ecosystem_health?: number;
  verdicts?: { TRUST?: number; CAUTION?: number; REJECT?: number };
};

const FALLBACK: Stats = {
  agents_scored: 39852,
  sybil_flagged: 20138,
  contagion_affected: 13648,
};

export default function Hero() {
  const [stats, setStats] = useState<Stats>(FALLBACK);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/stats")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (cancelled || !d) return;
        setStats({
          agents_scored: d.agents_scored ?? FALLBACK.agents_scored,
          sybil_flagged: d.sybil_flagged ?? FALLBACK.sybil_flagged,
          contagion_affected: d.contagion_affected ?? FALLBACK.contagion_affected,
          ecosystem_health: d.ecosystem_health,
          verdicts: d.verdicts,
        });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="relative pt-28 sm:pt-36 pb-16 overflow-hidden">
      <div className="absolute inset-0 -z-10 opacity-50 dark:opacity-30 text-text/30 pointer-events-none">
        <TrustGraph className="w-full h-full" />
      </div>
      <div
        className="absolute inset-0 -z-10 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse at center top, transparent 0%, var(--bg) 70%)",
        }}
      />

      <div className="max-w-6xl mx-auto px-6 lg:px-8">
        <div className="max-w-4xl">
          <p className="text-sm text-muted mb-6 inline-flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-trust animate-pulse" />
            Production on Base mainnet
          </p>
          <h1
            className="font-display font-light text-text"
            style={{
              fontSize: "clamp(3rem, 9vw, 7.5rem)",
              lineHeight: "0.95",
              letterSpacing: "-0.045em",
            }}
          >
            Reputation,
            <br />
            <span className="italic">on-chain,</span>
            <br />
            for every agent.
          </h1>
          <p className="mt-8 max-w-xl text-lg sm:text-xl text-muted leading-relaxed font-light">
            SentinelNet scores every ERC-8004 agent on Base — autonomous,
            slashable, composable in a single line of Solidity.
          </p>
          <div className="mt-10 flex flex-wrap items-center gap-3">
            <a
              href="/dashboard"
              className="inline-flex items-center gap-2 h-12 px-6 rounded-full bg-text text-bg text-sm font-medium hover:opacity-90 transition-opacity magnetic"
            >
              Open live dashboard
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                <path d="M5 12h14M13 5l7 7-7 7" />
              </svg>
            </a>
            <a
              href="/docs"
              className="inline-flex items-center h-12 px-6 rounded-full border border-border hover:border-text/40 text-text text-sm font-medium transition-colors"
            >
              Read the API
            </a>
          </div>
        </div>

        <div className="mt-20 sm:mt-28 grid grid-cols-3 gap-6 sm:gap-12 max-w-3xl">
          <Stat value={stats.agents_scored} label="agents scored" />
          <Stat value={stats.sybil_flagged} label="sybils flagged" />
          <Stat value={stats.contagion_affected} label="contagion-penalised" />
        </div>
      </div>
    </section>
  );
}

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <div>
      <div className="ticker text-text font-light" style={{ fontSize: "clamp(2rem, 5vw, 3.75rem)", letterSpacing: "-0.03em" }}>
        <CountUp to={value} />
      </div>
      <div className="mt-2 text-xs sm:text-sm text-muted leading-snug">
        {label}
      </div>
    </div>
  );
}
