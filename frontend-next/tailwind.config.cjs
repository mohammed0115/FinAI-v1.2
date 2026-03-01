/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
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

