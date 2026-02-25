// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Cyberpunk/Glassmorphism ozel tema: TonbilAiOS Dashboard

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Neon renk paleti
        neon: {
          cyan: "#00F0FF",
          magenta: "#FF00E5",
          green: "#39FF14",
          amber: "#FFB800",
          red: "#FF003C",
        },
        // Karanlik arka plan katmanlari
        surface: {
          900: "#0A0A0F",
          800: "#12121A",
          700: "#1A1A2E",
          600: "#252540",
        },
        // Cam efekti renkleri
        glass: {
          DEFAULT: "rgba(255, 255, 255, 0.05)",
          light: "rgba(255, 255, 255, 0.10)",
          border: "rgba(255, 255, 255, 0.12)",
        },
      },
      backdropBlur: {
        glass: "16px",
      },
      boxShadow: {
        neon: "0 0 20px rgba(0, 240, 255, 0.3)",
        "neon-magenta": "0 0 20px rgba(255, 0, 229, 0.3)",
        "neon-green": "0 0 20px rgba(57, 255, 20, 0.3)",
        glass: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Fira Code"', "monospace"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
      },
      animation: {
        "pulse-neon": "pulseNeon 2s ease-in-out infinite",
        glow: "glow 2s ease-in-out infinite alternate",
      },
      keyframes: {
        pulseNeon: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
        glow: {
          from: { boxShadow: "0 0 10px rgba(0, 240, 255, 0.2)" },
          to: { boxShadow: "0 0 30px rgba(0, 240, 255, 0.6)" },
        },
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};
