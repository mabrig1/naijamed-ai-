import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        green: { 50: "#E9F5F0", 600: "#0B6E4F", 700: "#085B42", 900: "#043B2B" },
        cream: "#FDF6EC",
        amber: "#F4A261"
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui"],
        serif: ["var(--font-fraunces)", "ui-serif", "Georgia"]
      },
      boxShadow: { soft: "0 14px 40px rgba(11, 110, 79, 0.10)" }
    }
  },
  plugins: []
};
export default config;
