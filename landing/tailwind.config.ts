import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        cream: "#FAFAF7",
        ink: "#0A0A0B",
        bg: "var(--bg)",
        surface: "var(--surface)",
        text: "var(--text)",
        muted: "var(--muted)",
        border: "var(--border)",
        accent: "#0052FF",
        "pastel-blue": "var(--pastel-blue)",
        "pastel-peach": "var(--pastel-peach)",
        "pastel-sage": "var(--pastel-sage)",
        trust: "#10B981",
        caution: "#F59E0B",
        reject: "#EF4444",
      },
      fontFamily: {
        display: ["var(--font-fraunces)", "Fraunces", "ui-serif", "Georgia", "serif"],
        sans: ["var(--font-geist-sans)", "Geist", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "Geist Mono", "JetBrains Mono", "ui-monospace", "monospace"],
      },
      letterSpacing: {
        display: "-0.04em",
        tighter: "-0.02em",
      },
      fontSize: {
        "display-1": ["clamp(3.5rem, 9vw, 7.5rem)", { lineHeight: "0.95", letterSpacing: "-0.04em" }],
        "display-2": ["clamp(2.5rem, 5vw, 4rem)", { lineHeight: "1.05", letterSpacing: "-0.03em" }],
        "display-3": ["clamp(1.75rem, 3vw, 2.5rem)", { lineHeight: "1.15", letterSpacing: "-0.02em" }],
      },
    },
  },
  plugins: [],
};

export default config;
