import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SentinelNet — Trust Layer for ERC-8004 Agents on Base",
  description:
    "Autonomous reputation scoring for ERC-8004 agents. 5-dimensional trust analysis with on-chain composability, IPFS evidence, and EAS attestations.",
  openGraph: {
    title: "SentinelNet — Trust Layer for ERC-8004 Agents",
    description:
      "Score every agent. Pin evidence. Write reputation on-chain. Zero human involvement.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="scroll-smooth">
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `window.addEventListener('error', function(e) {
  document.title = 'ERR: ' + e.message;
  var d = document.createElement('pre');
  d.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:99999;background:#080810;color:#ff3344;padding:2rem;font-size:14px;white-space:pre-wrap;max-height:100vh;overflow:auto';
  d.textContent = 'ERROR: ' + e.message + '\\n\\nFILE: ' + e.filename + ':' + e.lineno + ':' + e.colno + '\\n\\nSTACK: ' + (e.error && e.error.stack || 'none');
  document.body.prepend(d);
});`,
          }}
        />
      </head>
      <body className={inter.className}>{children}</body>
    </html>
  );
}
