/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#0ea5e9",
        },
        surface: {
          DEFAULT: "#1e293b",
          raised: "#334155",
          border: "#475569",
        },
        muted: "#94a3b8",
      },
    },
  },
  plugins: [],
};
