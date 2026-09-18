/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        dopely: {
          navy: '#1F2243',
          'navy-dark': '#171933',
          steel: '#4F546F',
          'steel-light': '#6B7280',
          ice: '#ACC1D6',
          'ice-light': '#F0F4F8',
          'ice-subtle': '#E2E8F0',
          amber: '#E67E22',
          'amber-hover': '#D97706',
          bg: '#F4F6F9',
          surface: '#FFFFFF',
        },
      },
    },
  },
  plugins: [],
};
