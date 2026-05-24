import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        base: "var(--color-base)",
        surface: {
          1: "var(--color-s1)",
          2: "var(--color-s2)",
          3: "var(--color-s3)",
          4: "var(--color-s4)",
          5: "var(--color-s5)"
        },
        gold: "var(--color-gold)",
        gold2: "var(--color-gold-2)",
        silver: "var(--color-silver)",
        ink: "var(--color-text-primary)"
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"]
      },
      boxShadow: {
        shell: "0 24px 80px rgba(4, 9, 15, 0.45)",
        gold: "0 0 0 1px rgba(201,169,110,0.24), 0 12px 40px rgba(8, 16, 24, 0.35)"
      },
      backgroundImage: {
        "radial-shell": "radial-gradient(circle at top, rgba(42,74,97,0.34), transparent 38%), radial-gradient(circle at right top, rgba(201,169,110,0.12), transparent 24%)"
      }
    }
  },
  plugins: []
};

export default config;
