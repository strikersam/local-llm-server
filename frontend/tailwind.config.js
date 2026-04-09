/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: '#0A0A0A',
        surface: '#141414',
        elevated: '#1A1A1A',
        accent: '#002FA7',
        'accent-hover': '#002585',
        danger: '#FF3333',
        warning: '#FFFF00',
      },
      fontFamily: {
        heading: ['"Cabinet Grotesk"', 'Chivo', 'sans-serif'],
        mono: ['"IBM Plex Mono"', '"JetBrains Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
};
