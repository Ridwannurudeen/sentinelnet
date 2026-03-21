"use client";

import { motion } from "framer-motion";
import {
  Layers,
  Link,
  Coins,
  HardDrive,
  Timer,
  ShieldAlert,
  Workflow,
  Radar,
  BadgeCheck,
} from "lucide-react";
import { FEATURES } from "@/lib/constants";
import ScrollReveal from "./ScrollReveal";

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  Layers,
  Link,
  Coins,
  HardDrive,
  Timer,
  ShieldAlert,
  Workflow,
  Radar,
  BadgeCheck,
};

export default function FeatureGrid() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <ScrollReveal>
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            Why <span className="text-gradient">SentinelNet</span>
          </h2>
          <p className="text-sec max-w-xl mx-auto">
            Nine capabilities that make agent reputation composable, verifiable,
            and unstoppable.
          </p>
        </div>
      </ScrollReveal>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {FEATURES.map((feature, i) => {
          const Icon = iconMap[feature.icon];
          return (
            <ScrollReveal key={feature.title} delay={i * 0.05}>
              <motion.div
                whileHover={{ y: -4 }}
                className="glass-hover rounded-2xl p-6 h-full"
              >
                <div className="flex items-start gap-4">
                  <div className="p-2.5 rounded-xl bg-cyan/5 border border-cyan/10 shrink-0">
                    {Icon && <Icon className="w-5 h-5 text-cyan" />}
                  </div>
                  <div>
                    <h3 className="font-semibold text-text mb-2">
                      {feature.title}
                    </h3>
                    <p className="text-sm text-sec leading-relaxed">
                      {feature.description}
                    </p>
                  </div>
                </div>
              </motion.div>
            </ScrollReveal>
          );
        })}
      </div>
    </section>
  );
}
