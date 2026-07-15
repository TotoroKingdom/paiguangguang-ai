import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui"]
      },
      colors: {
        ink: "rgb(var(--color-ink) / <alpha-value>)",
        paper: "rgb(var(--color-paper) / <alpha-value>)",
        moss: "rgb(var(--color-moss) / <alpha-value>)",
        clay: "rgb(var(--color-clay) / <alpha-value>)",
        brass: "rgb(var(--color-brass) / <alpha-value>)",
        tide: "rgb(var(--color-tide) / <alpha-value>)"
      }
    }
  },
  plugins: []
};

export default config;
