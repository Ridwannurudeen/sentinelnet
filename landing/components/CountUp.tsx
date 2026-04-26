"use client";

import { useEffect, useRef, useState } from "react";

export default function CountUp({
  to,
  duration = 1600,
  format = (n: number) => n.toLocaleString(),
  className = "",
}: {
  to: number;
  duration?: number;
  format?: (n: number) => string;
  className?: string;
}) {
  const [n, setN] = useState(0);
  const started = useRef(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const el = ref.current;
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting && !started.current) {
            started.current = true;
            const start = performance.now();
            let raf = 0;
            function tick(now: number) {
              const p = Math.min((now - start) / duration, 1);
              const eased = 1 - Math.pow(1 - p, 3);
              setN(Math.round(eased * to));
              if (p < 1) raf = requestAnimationFrame(tick);
            }
            raf = requestAnimationFrame(tick);
            return () => cancelAnimationFrame(raf);
          }
        });
      },
      { threshold: 0.4 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [to, duration]);

  return (
    <span ref={ref} className={className}>
      {format(n)}
    </span>
  );
}
