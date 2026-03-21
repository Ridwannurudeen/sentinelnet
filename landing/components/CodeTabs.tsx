"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CODE_TABS } from "@/lib/constants";
import { Copy, Check } from "lucide-react";
import ScrollReveal from "./ScrollReveal";

const TAB_KEYS = Object.keys(CODE_TABS) as (keyof typeof CODE_TABS)[];

function highlightSyntax(code: string, lang: string): string {
  const keywords: Record<string, string[]> = {
    Solidity: ["import", "contract", "function", "external", "is", "uint256"],
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
        '<span class="text-trust">$1</span>'
      );

      kws.forEach((kw) => {
        result = result.replace(
          new RegExp(`\\b(${kw})\\b`, "g"),
          '<span class="text-cyan font-semibold">$1</span>'
        );
      });

      return result;
    })
    .join("\n");
}

export default function CodeTabs() {
  const [active, setActive] = useState<keyof typeof CODE_TABS>("Solidity");
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(CODE_TABS[active]);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <ScrollReveal>
        <div className="text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            Integrate in <span className="text-gradient">minutes</span>
          </h2>
          <p className="text-sec max-w-xl mx-auto">
            Smart contract modifier, REST API, Python SDK, or MCP tool — pick
            your path.
          </p>
        </div>
      </ScrollReveal>

      <ScrollReveal delay={0.1}>
        <div className="max-w-3xl mx-auto">
          <div className="glass rounded-2xl overflow-hidden">
            {/* Tab bar */}
            <div className="flex items-center border-b border-border/50 px-2">
              {TAB_KEYS.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActive(tab)}
                  className={`relative px-4 py-3 text-sm font-medium transition-colors ${
                    active === tab ? "text-cyan" : "text-muted hover:text-sec"
                  }`}
                >
                  {tab}
                  {active === tab && (
                    <motion.div
                      layoutId="tab-underline"
                      className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan"
                    />
                  )}
                </button>
              ))}
              <div className="flex-1" />
              <button
                onClick={handleCopy}
                className="p-2 text-muted hover:text-sec transition-colors"
                title="Copy code"
              >
                {copied ? (
                  <Check className="w-4 h-4 text-trust" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>
            </div>

            {/* Code block */}
            <AnimatePresence mode="wait">
              <motion.div
                key={active}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="p-6 overflow-x-auto"
              >
                <pre className="text-sm font-mono leading-relaxed">
                  <code
                    dangerouslySetInnerHTML={{
                      __html: highlightSyntax(CODE_TABS[active], active),
                    }}
                  />
                </pre>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </ScrollReveal>
    </section>
  );
}
