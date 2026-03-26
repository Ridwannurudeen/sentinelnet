"use client";

import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import { Users, ShieldCheck, AlertTriangle, XCircle } from "lucide-react";
import ScrollReveal from "./ScrollReveal";

interface Stats {
  agents_scored: number;
  verdicts: { TRUST: number; CAUTION: number; REJECT: number };
}

function AnimatedCounter({ target, duration = 1500 }: { target: number; duration?: number }) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const prevTarget = useRef(0);

  useEffect(() => {
    if (target === 0) return;

    const from = prevTarget.current;
    prevTarget.current = target;

    // Skip animation if value hasn't changed
    if (from === target) {
      setCount(target);
      return;
    }

    const start = performance.now();
    let raf: number;
    function tick(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(from + eased * (target - from)));
      if (progress < 1) raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return <span ref={ref}>{count}</span>;
}

const STAT_CARDS = [
  { key: "total", label: "Agents Scored", icon: Users, color: "cyan" },
  { key: "trust", label: "Trusted", icon: ShieldCheck, color: "trust" },
  { key: "caution", label: "Caution", icon: AlertTriangle, color: "caution" },
  { key: "reject", label: "Rejected", icon: XCircle, color: "reject" },
] as const;

const colorMap: Record<string, string> = {
  cyan: "text-cyan border-cyan/20 bg-cyan/5",
  trust: "text-trust border-trust/20 bg-trust/5",
  caution: "text-caution border-caution/20 bg-caution/5",
  reject: "text-reject border-reject/20 bg-reject/5",
};

const iconBgMap: Record<string, string> = {
  cyan: "bg-cyan/10",
  trust: "bg-trust/10",
  caution: "bg-caution/10",
  reject: "bg-reject/10",
};

export default function LiveStats() {
  const [stats, setStats] = useState<Stats | null>(null);

  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch("/api/stats")
      .then((r) => r.json())
      .then((d) => setStats(d))
      .catch(() => setFailed(true));
  }, []);

  const values = stats
    ? [
        stats.agents_scored,
        stats.verdicts.TRUST,
        stats.verdicts.CAUTION,
        stats.verdicts.REJECT,
      ]
    : [0, 0, 0, 0];

  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <ScrollReveal>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {STAT_CARDS.map((card, i) => {
            const Icon = card.icon;
            return (
              <motion.div
                key={card.key}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1, duration: 0.5 }}
                className={`glass-hover rounded-2xl p-6 ${colorMap[card.color]}`}
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className={`p-2 rounded-lg ${iconBgMap[card.color]}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="text-sm text-sec font-medium">
                    {card.label}
                  </span>
                </div>
                <div className="text-3xl sm:text-4xl font-bold tabular-nums">
                  {!stats && !failed ? (
                    <span className="text-sec text-lg">Loading...</span>
                  ) : failed && !stats ? (
                    <span className="text-sec text-lg">--</span>
                  ) : (
                    <AnimatedCounter target={values[i]} />
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      </ScrollReveal>
    </section>
  );
}
