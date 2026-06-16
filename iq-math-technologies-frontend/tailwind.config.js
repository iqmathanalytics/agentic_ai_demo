/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        nexperts: {
          maroon: "#9B1B30",
          "maroon-dark": "#6B1222",
          "maroon-deep": "#3D0A14",
          gold: "#D4A017",
          blush: "#FAF5F6",
        },
        premium: {
          bg: "#1A0A0E",
          surface: "#241018",
          card: "#2E1520",
          border: "#4A2030",
          accent: "#9B1B30",
          accentLight: "#C41E3A",
          gold: "#D4A017",
          green: "#10B981",
          amber: "#F59E0B",
          red: "#EF4444",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
};
