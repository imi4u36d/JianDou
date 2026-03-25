/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{vue,ts}"],
  theme: {
    extend: {
      colors: {
        ink: "#101724",
        slate: "#1f2937",
        accent: "#f97316",
        ember: "#fb923c",
        mist: "#e2e8f0"
      },
      boxShadow: {
        panel: "0 24px 60px rgba(15, 23, 42, 0.18)"
      }
    }
  },
  plugins: []
};

