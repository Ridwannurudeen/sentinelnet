import type { Metadata } from "next";
import { Fraunces } from "next/font/google";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  display: "swap",
  weight: ["300", "400", "500", "600"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://sentinelnet.gudman.xyz"),
  icons: {
    icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🛡</text></svg>",
  },
  title: "SentinelNet — Reputation, on-chain, for every agent.",
  description:
    "Autonomous agent reputation infrastructure on Base. 4,320+ ERC-8004 agents scored, 84 sybil networks unmasked, slashable trust, composable in one line of Solidity.",
  openGraph: {
    title: "SentinelNet — Reputation, on-chain, for every agent.",
    description:
      "The trust layer for the ERC-8004 agent economy. Live on Base mainnet.",
    type: "website",
    url: "https://sentinelnet.gudman.xyz",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "SentinelNet — Reputation, on-chain, for every agent.",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "SentinelNet — Reputation, on-chain, for every agent.",
    description:
      "Autonomous agent reputation infrastructure on Base. Slashable, composable, in one line of Solidity.",
    images: ["/og-image.png"],
  },
  other: {
    // Talent Protocol project ownership verification
    "talentapp:project_verification":
      "5805f4ccfd04a9e8ae5b9d6a6c3cd6fe2f4e4a7e1ba6c318ebf7d0221d40c9b34100b8979c54b5a9f7f364572b857c7e565fda0f5ce61da717470f99e315ecec",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`scroll-smooth ${fraunces.variable} ${GeistSans.variable} ${GeistMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('theme');var d=t?t==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;document.documentElement.classList.toggle('dark',d);}catch(e){}})();`,
          }}
        />
      </head>
      <body className="bg-bg text-text font-sans font-light tracking-tighter antialiased">
        {children}
      </body>
    </html>
  );
}
