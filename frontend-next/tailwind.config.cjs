/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        app: {
          base: "rgb(var(--surface-base) / <alpha-value>)",
          muted: "rgb(var(--surface-muted) / <alpha-value>)",
          card: "rgb(var(--surface-card) / <alpha-value>)",
          border: "rgb(var(--border-soft) / <alpha-value>)",
          borderStrong: "rgb(var(--border-strong) / <alpha-value>)",
          text: "rgb(var(--text-primary) / <alpha-value>)",
          textSecondary: "rgb(var(--text-secondary) / <alpha-value>)",
          textMuted: "rgb(var(--text-muted) / <alpha-value>)",
          primaryFrom: "rgb(var(--primary-from) / <alpha-value>)",
          primaryTo: "rgb(var(--primary-to) / <alpha-value>)",
        },
      },
      backgroundImage: {
        primary: "var(--gradient-primary)",
        sidebar: "var(--gradient-sidebar)",
      },
      borderRadius: {
        loginSm: "var(--radius-sm)",
        loginMd: "var(--radius-md)",
        loginLg: "var(--radius-lg)",
        loginXl: "var(--radius-xl)",
      },
      boxShadow: {
        soft: "var(--shadow-soft)",
        card: "var(--shadow-card)",
        primary: "var(--shadow-primary)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
      },
      animation: {
        shimmer: "shimmer 3s linear infinite",
        "shimmer-delay1": "shimmer 3s linear infinite 0.5s",
        "shimmer-delay2": "shimmer 3s linear infinite 1s",
        float: "float 4s ease-in-out infinite",
        "float-delay": "float 4s ease-in-out infinite 1s",
      },
    },
  },
  plugins: [],
};
