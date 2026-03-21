import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#080810",
        card: "#0f0f1a",
        border: "#1e1e3a",
        text: "#e8e8f0",
        muted: "#555570",
        sec: "#8888aa",
        blue: "#0088ff",
        cyan: "#00ccff",
        trust: "#00dd77",
        caution: "#ffaa22",
        reject: "#ff3344",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
