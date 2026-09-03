/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        canvas: {
          DEFAULT: "#FAF8F3",
          soft: "#F3F1EA",
        },
        surface: {
          DEFAULT: "#FFFFFF",
          muted: "#F6F4EE",
        },
        ink: {
          900: "#1C1D1B",
          700: "#3F413D",
          500: "#6B6D67",
          300: "#A8AAA3",
        },
        brand: {
          50: "#EFF9F4",
          100: "#D9F0E3",
          200: "#B3E1C8",
          300: "#84CBA7",
          400: "#4FAE81",
          500: "#2D9166",
          600: "#1F7A53",
          700: "#186043",
          800: "#144D37",
          900: "#0F3B2A",
        },
        risk: {
          low: "#2D9166",
          "low-bg": "#EAF6EF",
          medium: "#B5760B",
          "medium-bg": "#FCF1DE",
          high: "#B23A2E",
          "high-bg": "#FBEAE7",
        },
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Inter",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      boxShadow: {
        card: "0 1px 2px rgba(28,29,27,0.04), 0 1px 8px rgba(28,29,27,0.04)",
        raised: "0 4px 16px rgba(28,29,27,0.08)",
      },
      borderRadius: {
        xl2: "1.25rem",
      },
    },
  },
  plugins: [],
};
