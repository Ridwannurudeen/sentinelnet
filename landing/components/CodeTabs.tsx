"use client";

import { useState } from "react";
import { CODE_TABS } from "@/lib/constants";

const TAB_KEYS = Object.keys(CODE_TABS) as (keyof typeof CODE_TABS)[];

function highlight(code: string, lang: string): string {
  const keywords: Record<string, string[]> = {
    Solidity: ["import", "contract", "function", "external", "is", "uint256", "interface", "modifier", "calldata", "view"],
    cURL: ["curl", "POST", "GET"],
    Python: ["import", "async", "def", "with", "as", "await", "return"],
    MCP: ["name", "arguments", "true"],
  };
  const kws = keywords[lang] || [];
  return code
    .split("\n")
    .map((line) => {
      const escaped = line
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
      const trimmed = escaped.trimStart();
      if (trimmed.startsWith("//") || trimmed.startsWith("#")) {
        return `<span class="text-muted">${escaped}</span>`;
      }
      let result = escaped.replace(
        /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g,
        '<span style="color:#10B981">$1</span>'
      );
      kws.forEach((kw) => {
        result = result.replace(
          new RegExp(`\\b(${kw})\\b`, "g"),
          '<span style="color:#0052FF">$1</span>'
        );
      });
      return result;
    })
    .join("\n");
}

export default function CodeTabs() {
  const [active, setActive] = useState<keyof typeof CODE_TABS>("Solidity");
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText(CODE_TABS[active]);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <section className="py-24 px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-10 max-w-2xl">
          <p className="text-sm text-muted mb-4">Drop in</p>
          <h2
            className="font-display font-light text-text"
            style={{ fontSize: "clamp(1.75rem, 4vw, 2.75rem)", lineHeight: "1.1", letterSpacing: "-0.03em" }}
          >
            One line. Four paths.
          </h2>
          <p className="mt-4 text-sm text-muted font-light max-w-md">
            Smart contract modifier, REST, Python, MCP. Pick the surface that
            fits your stack.
          </p>
        </div>

        <div className="surface-card rounded-3xl overflow-hidden">
          <div className="flex items-center border-b border-border">
            {TAB_KEYS.map((tab) => (
              <button
                key={tab}
                onClick={() => setActive(tab)}
                className={`px-5 py-3.5 text-sm transition-colors relative ${
                  active === tab
                    ? "text-text"
                    : "text-muted hover:text-text"
                }`}
              >
                {tab}
                {active === tab && (
                  <span className="absolute bottom-[-1px] left-3 right-3 h-px bg-text" />
                )}
              </button>
            ))}
            <div className="flex-1" />
            <button
              onClick={copy}
              className="mr-3 text-xs text-muted hover:text-text transition-colors px-3 py-1 rounded-full border border-border"
            >
              {copied ? "copied" : "copy"}
            </button>
          </div>
          <div className="p-6 sm:p-8 overflow-x-auto">
            <pre className="font-mono text-sm leading-relaxed text-text/90">
              <code dangerouslySetInnerHTML={{ __html: highlight(CODE_TABS[active], active) }} />
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
}
