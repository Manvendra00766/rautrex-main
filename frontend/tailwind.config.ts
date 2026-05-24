import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--bg-primary)",
        foreground: "var(--text-primary)",
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        input: "var(--input)",
        ring: "var(--ring)",
        surface: "var(--bg-surface)",
        elevated: "var(--bg-secondary)",
        card: "var(--bg-card)",
        "card-foreground": "var(--text-primary)",
        popover: "var(--bg-surface)",
        "popover-foreground": "var(--text-primary)",
        accent: "var(--accent)",
        positive: "var(--positive)",
        negative: "var(--negative)",
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        "text-primary": "var(--text-primary)",
        "text-secondary": "var(--text-secondary)",
        "text-muted": "var(--text-muted)",
        sidebar: "var(--sidebar-bg)",
        navbar: "var(--navbar-bg)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "sans-serif"],
        serif: ["var(--font-serif)", "serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      gridTemplateColumns: {
        '13': 'repeat(13, minmax(0, 1fr))',
      },
    },
  },
  plugins: [],
};
export default config;
