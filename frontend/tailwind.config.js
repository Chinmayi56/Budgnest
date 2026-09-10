/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
      },
      colors: {
        ink: "#10231D",
        paper: "#F4F6F4",
        surface: "#FFFFFF",
        border: "#E2E8E4",
        brand: {
          50: "#EAF6F1",
          100: "#CFEBDF",
          300: "#7FC7A9",
          500: "#0F6E5C",
          600: "#0B5548",
          700: "#083F37",
        },
        income: {
          DEFAULT: "#1B8A5A",
          soft: "#E6F5EC",
        },
        expense: {
          DEFAULT: "#C24A3B",
          soft: "#FBEAE7",
        },
      },
      boxShadow: {
        card: "0 1px 2px rgba(16, 35, 29, 0.04), 0 4px 16px rgba(16, 35, 29, 0.06)",
      },
      borderRadius: {
        xl2: "1.1rem",
      },
    },
  },
  plugins: [],
};
