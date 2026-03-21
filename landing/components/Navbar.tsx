"use client";

import { motion } from "framer-motion";
import { NAV_LINKS } from "@/lib/constants";
import { ExternalLink, Menu, X } from "lucide-react";
import { useState } from "react";

export default function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/30"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <a href="/" className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan to-blue flex items-center justify-center">
              <span className="text-sm font-bold text-white">S</span>
            </div>
            <span className="text-lg font-bold text-cyan">SentinelNet</span>
          </a>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-6">
            {NAV_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                {...("external" in link && link.external
                  ? { target: "_blank", rel: "noopener noreferrer" }
                  : {})}
                className="text-sm text-sec hover:text-text transition-colors flex items-center gap-1"
              >
                {link.label}
                {"external" in link && link.external && (
                  <ExternalLink className="w-3 h-3" />
                )}
              </a>
            ))}
            <div className="flex items-center gap-2 ml-4 px-3 py-1.5 rounded-full bg-trust/10 border border-trust/30">
              <span className="w-2 h-2 rounded-full bg-trust animate-pulse" />
              <span className="text-xs font-medium text-trust">Base Mainnet</span>
            </div>
          </div>

          {/* Mobile toggle */}
          <button
            onClick={() => setOpen(!open)}
            className="md:hidden text-sec hover:text-text"
          >
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="md:hidden glass border-t border-border/30"
        >
          <div className="px-4 py-4 space-y-3">
            {NAV_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                {...("external" in link && link.external
                  ? { target: "_blank", rel: "noopener noreferrer" }
                  : {})}
                className="block text-sm text-sec hover:text-text transition-colors"
                onClick={() => setOpen(false)}
              >
                {link.label}
              </a>
            ))}
            <div className="flex items-center gap-2 pt-2">
              <span className="w-2 h-2 rounded-full bg-trust animate-pulse" />
              <span className="text-xs font-medium text-trust">Base Mainnet — Live</span>
            </div>
          </div>
        </motion.div>
      )}
    </motion.nav>
  );
}
