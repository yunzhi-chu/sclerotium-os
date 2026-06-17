import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        cortex: {
          bg: "#0a0a0f",
          surface: "#141428",
          border: "#1e1e3a",
          primary: "#00d4aa",
          secondary: "#7c3aed",
          accent: "#f59e0b",
          danger: "#ef4444",
          warning: "#f59e0b",
          success: "#22c55e",
          info: "#3b82f6",
        },
        hyphal: {
          active: "#00ff88",
          idle: "#666688",
          overloaded: "#ff6644",
          offline: "#333355",
        },
        field: {
          signal: "#ff4466",
          nutrient: "#44ff66",
          damage: "#888899",
          temperature: "#ff8844",
        },
        faction: {
          aggressive: "#ff4444",
          conservative: "#4488ff",
          neutral: "#ffaa44",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      animation: {
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        "flow-right": "flow-right 1.5s linear infinite",
        "hyphal-grow": "hyphal-grow 0.5s ease-out",
        "node-spawn": "node-spawn 0.3s ease-out",
        "edge-flow": "edge-flow 1s linear infinite",
        "emergence-flash": "emergence-flash 0.5s ease-out",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { boxShadow: "0 0 20px rgba(0,212,170,0.2)" },
          "50%": { boxShadow: "0 0 40px rgba(0,212,170,0.5)" },
        },
        "flow-right": {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        "hyphal-grow": {
          "0%": { transform: "scaleX(0)", opacity: "0" },
          "100%": { transform: "scaleX(1)", opacity: "1" },
        },
        "node-spawn": {
          "0%": { transform: "scale(0)", opacity: "0" },
          "50%": { transform: "scale(1.2)" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
        "edge-flow": {
          "0%": { strokeDashoffset: "20" },
          "100%": { strokeDashoffset: "0" },
        },
        "emergence-flash": {
          "0%": { backgroundColor: "rgba(0,255,136,0.3)" },
          "100%": { backgroundColor: "transparent" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
