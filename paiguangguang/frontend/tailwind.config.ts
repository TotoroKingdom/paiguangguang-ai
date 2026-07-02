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
        ink: "#151815",
        paper: "#f8f4ea",
        moss: "#66735c",
        clay: "#b65f3b",
        brass: "#c39a3d",
        tide: "#2d6f73"
      }
    }
  },
  plugins: []
};

export default config;
