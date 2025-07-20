/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Amazon brand colors
        'amazon': {
          orange: '#ff9900',
          'orange-light': '#ffad1a',
          'orange-dark': '#e68a00',
          blue: '#146eb4',
          'blue-light': '#1a7cc7',
          'blue-dark': '#0e5a8a',
          navy: '#232f3e',
          'navy-light': '#2c3a4a',
          'navy-dark': '#1a2332',
          black: '#000000',
          gray: '#f2f2f2',
          'gray-dark': '#dddddd',
        },
        // Override default Tailwind colors with Amazon equivalents
        primary: {
          50: '#fff7e6',
          100: '#ffebcc',
          200: '#ffd699',
          300: '#ffc266',
          400: '#ffad33',
          500: '#ff9900', // Amazon orange
          600: '#e68a00',
          700: '#cc7a00',
          800: '#b36b00',
          900: '#995c00',
        },
        secondary: {
          50: '#e6f3ff',
          100: '#cce7ff',
          200: '#99cfff',
          300: '#66b7ff',
          400: '#339fff',
          500: '#146eb4', // Amazon blue
          600: '#0e5a8a',
          700: '#0b4a73',
          800: '#083a5c',
          900: '#052a45',
        },
        neutral: {
          50: '#f9fafb',
          100: '#f2f2f2', // Amazon gray
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#9ca3af',
          500: '#6b7280',
          600: '#4b5563',
          700: '#374151',
          800: '#232f3e', // Amazon navy
          900: '#1a2332',
        }
      }
    },
  },
  plugins: [],
}