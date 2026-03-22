import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  icons: {
    icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🛡</text></svg>",
  },
  title: "SentinelNet — Trust Layer for ERC-8004 Agents on Base",
  description:
    "Autonomous reputation scoring for ERC-8004 agents. 5-dimensional trust analysis with on-chain composability, IPFS evidence, and gasless paymaster transactions.",
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
      <body className={inter.className}>{children}</body>
    </html>
  );
}
