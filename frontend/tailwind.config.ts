import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#070b12",
        surface: "#0f1623",
        panel: "#151d2e",
        border: "#1e2a3d",
        primary: "#06b6d4",
        secondary: "#8b5cf6",
        danger: "#f43f5e",
        success: "#10b981",
        warn: "#f59e0b",
        muted: "#94a3b8",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "monospace"],
      },
      animation: {
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
        "slide-in": "slide-in 0.3s ease-out",
      },
      keyframes: {
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.6" },
        },
        "slide-in": {
          from: { transform: "translateX(100%)", opacity: "0" },
          to: { transform: "translateX(0)", opacity: "1" },
        },
      },
      boxShadow: {
        glow: "0 0 24px rgba(6, 182, 212, 0.15)",
        "glow-danger": "0 0 24px rgba(244, 63, 94, 0.2)",
      },
    },
  },
  plugins: [],
};

export default config;
