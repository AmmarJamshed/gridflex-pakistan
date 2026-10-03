/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        flex: {
          green: "#1FA97A",
          blue: "#1B6CA8",
          orange: "#E08A2B",
          red: "#C0392B",
          purple: "#6C4AB6",
          ink: "#0E1A24",
          mist: "#E8F1F5",
          sand: "#D9E4DC",
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', "system-ui", "sans-serif"],
        body: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
      },
      boxShadow: {
        panel: "0 18px 50px rgba(14, 26, 36, 0.12)",
      },
    },
  },
  plugins: [],
};