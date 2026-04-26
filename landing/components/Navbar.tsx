"use client";

import { useEffect, useState } from "react";
import { NAV_LINKS } from "@/lib/constants";
import ThemeToggle from "./ThemeToggle";

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 12);
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${
        scrolled
          ? "backdrop-blur-md bg-bg/80 border-b border-border"
          : "bg-transparent border-b border-transparent"
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <a href="/" className="inline-flex items-center gap-2 group">
            <span
              className="font-display text-2xl font-medium leading-none text-text"
              style={{ letterSpacing: "-0.05em" }}
            >
              SN
            </span>
            <span className="text-sm text-muted hidden sm:inline">
              SentinelNet
            </span>
          </a>

          <nav className="hidden md:flex items-center gap-7">
            {NAV_LINKS.filter((l) => !("external" in l) || !l.external).slice(0, 4).map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-sm text-muted hover:text-text transition-colors"
              >
                {link.label}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <span className="hidden sm:inline-flex items-center gap-2 text-xs text-muted mr-1">
              <span className="w-1.5 h-1.5 rounded-full bg-trust animate-pulse" />
              Base mainnet
            </span>
            <ThemeToggle />
            <a
              href="/dashboard"
              className="hidden sm:inline-flex items-center px-3.5 h-9 rounded-full bg-text text-bg text-sm font-medium hover:opacity-90 transition-opacity"
            >
              Open dashboard
            </a>
            <button
              onClick={() => setOpen(!open)}
              className="md:hidden text-text p-2 -mr-2"
              aria-label="Menu"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                {open ? <path d="M6 6l12 12M6 18L18 6" /> : <path d="M4 6h16M4 12h16M4 18h16" />}
              </svg>
            </button>
          </div>
        </div>
      </div>

      {open && (
        <div className="md:hidden border-t border-border bg-bg">
          <div className="px-6 py-4 space-y-3">
            {NAV_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="block text-sm text-muted hover:text-text"
                onClick={() => setOpen(false)}
              >
                {link.label}
              </a>
            ))}
            <a
              href="/dashboard"
              className="inline-flex items-center px-3.5 h-9 rounded-full bg-text text-bg text-sm font-medium mt-2"
            >
              Open dashboard
            </a>
          </div>
        </div>
      )}
    </header>
  );
}
