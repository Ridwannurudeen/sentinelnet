"use client";

import { motion } from "framer-motion";
import { ArrowRight, BookOpen } from "lucide-react";

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
      {/* Animated background blobs */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] rounded-full bg-cyan/5 blur-[120px] animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full bg-blue/5 blur-[100px] animate-pulse [animation-delay:1s]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-trust/5 blur-[150px] animate-pulse [animation-delay:2s]" />
      </div>

      {/* Grid pattern overlay */}
      <div
        className="absolute inset-0 -z-10 opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0,204,255,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(0,204,255,0.3) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
        >
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-cyan/5 border border-cyan/20 mb-8"
          >
            <span className="w-2 h-2 rounded-full bg-trust animate-pulse" />
            <span className="text-sm text-sec">Synthesis 2026 Hackathon</span>
          </motion.div>

          {/* Heading */}
          <h1 className="text-4xl sm:text-5xl md:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
            The{" "}
            <span className="text-gradient">trust layer</span>
            <br />
            for ERC-8004 agents
            <br />
            <span className="text-sec text-3xl sm:text-4xl md:text-5xl font-medium">
              on Base
            </span>
          </h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.6 }}
            className="max-w-2xl mx-auto text-lg sm:text-xl text-sec leading-relaxed mb-10"
          >
            SentinelNet scores every agent&apos;s trustworthiness across 5
            dimensions, pins evidence to IPFS, and writes composable reputation
            on-chain. One query. One trust score. Zero human involvement.
          </motion.p>

          {/* CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.6 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <a
              href="/dashboard"
              className="group inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-gradient-to-r from-cyan to-blue text-white font-semibold text-sm transition-all hover:shadow-[0_0_30px_rgba(0,204,255,0.4)] hover:scale-[1.02]"
            >
              Live Dashboard
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </a>
            <a
              href="/docs"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl border border-border hover:border-cyan/40 text-sec hover:text-text font-semibold text-sm transition-all"
            >
              <BookOpen className="w-4 h-4" />
              API Docs
            </a>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
