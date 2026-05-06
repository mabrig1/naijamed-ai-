/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        forest: {
          50:  "#f0f7f4",
          100: "#d8ede5",
          200: "#b1daca",
          300: "#7bbfa8",
          400: "#4a9f83",
          500: "#2d7a5e",
          600: "#1B4332",
          700: "#163828",
          800: "#102a1f",
          900: "#091c14",
        },
        gold: {
          50:  "#fdf9e9",
          100: "#faf0c0",
          200: "#f5d96a",
          300: "#eec031",
          400: "#D4A017",
          500: "#b88510",
          600: "#8f660b",
          700: "#6a4c08",
        },
        earth: {
          300: "#c4845a",
          400: "#a0612e",
          500: "#8B4513",
          600: "#6b340f",
          700: "#4c250b",
        },
        cream: "#F5F0E8",
        naijamed: {
          primary:   "#1B4332",
          secondary: "#D4A017",
          accent:    "#8B4513",
          bg:        "#F5F0E8",
          dark:      "#1A1A1A",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Georgia", "serif"],
      },
      backgroundImage: {
        "hero-pattern": "linear-gradient(135deg, #1B4332 0%, #2d7a5e 50%, #1B4332 100%)",
        "gold-shimmer":  "linear-gradient(90deg, #D4A017, #f5d96a, #D4A017)",
      },
    },
  },
  plugins: [],
};
