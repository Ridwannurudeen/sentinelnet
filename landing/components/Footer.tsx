import { ExternalLink } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-border/30 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="text-sm text-muted text-center sm:text-left">
          <span className="text-sec font-medium">SentinelNet v2.2</span>
          {" — "}
          Agent #31253 — The immune system for the ERC-8004 agent economy on Base
        </div>
        <div className="flex items-center gap-6">
          <a
            href="https://github.com/Ridwannurudeen/sentinelnet"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-sec hover:text-text transition-colors"
          >
            GitHub
            <ExternalLink className="w-3 h-3" />
          </a>
          <a
            href="/docs"
            className="text-sm text-sec hover:text-text transition-colors"
          >
            API Docs
          </a>
          <a
            href="/docs-guide"
            className="text-sm text-sec hover:text-text transition-colors"
          >
            Integrate
          </a>
        </div>
      </div>
    </footer>
  );
}
