"use client";

import { CONTRACTS } from "@/lib/constants";
import { ExternalLink } from "lucide-react";
import ScrollReveal from "./ScrollReveal";

export default function ContractsTable() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <ScrollReveal>
        <div className="text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            On-chain <span className="text-gradient">contracts</span>
          </h2>
          <p className="text-sec max-w-xl mx-auto">
            Deployed and verified on Base Mainnet. Fully open-source.
          </p>
        </div>
      </ScrollReveal>

      <ScrollReveal delay={0.1}>
        <div className="max-w-3xl mx-auto glass rounded-2xl overflow-hidden">
          <div className="divide-y divide-border/50">
            {CONTRACTS.map((contract) => (
              <div
                key={contract.name}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-6 py-5 hover:bg-white/[0.02] transition-colors"
              >
                <div>
                  <h3 className="font-semibold text-text text-sm mb-1">
                    {contract.name}
                  </h3>
                  <code className="text-xs text-muted font-mono break-all">
                    {contract.address}
                  </code>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="px-2.5 py-1 rounded-full bg-blue/10 border border-blue/20 text-xs font-medium text-blue">
                    Base
                  </span>
                  <a
                    href={contract.explorer}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-sec hover:text-cyan transition-colors"
                  >
                    Blockscout
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      </ScrollReveal>
    </section>
  );
}
