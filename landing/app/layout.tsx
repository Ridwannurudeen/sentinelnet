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
      <body className={inter.className}>{children}</body>
    </html>
  );
}
