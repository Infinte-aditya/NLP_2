/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ggs: {
          black: '#1a1a1a',
          darkGrey: '#2d2d2d',
          lightGrey: '#e5e5e5',
          white: '#ffffff',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'], // Assuming Google Fonts 'Inter'
      }
    },
  },
  plugins: [],
}
