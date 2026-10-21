/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          50: '#effcfa',
          100: '#c9f5ee',
          200: '#94ebde',
          300: '#5cd8c9',
          400: '#2fbcae',
          500: '#159b90',
          600: '#0f7c74',
          700: '#10635e',
          800: '#124f4c',
          900: '#124240',
        },
        surface: {
          light: '#fbfbfa',
          dark: '#0d1117',
        },
        panel: {
          dark: '#151b23',
        },
      },
      boxShadow: {
        subtle: '0 1px 2px 0 rgba(0,0,0,0.04)',
      },
      fontSize: {
        xs: ['0.75rem', { lineHeight: '1rem' }],
        sm: ['0.8125rem', { lineHeight: '1.25rem' }],
        base: ['0.875rem', { lineHeight: '1.375rem' }],
        lg: ['1rem', { lineHeight: '1.5rem' }],
        xl: ['1.125rem', { lineHeight: '1.65rem' }],
        '2xl': ['1.375rem', { lineHeight: '1.85rem' }],
      },
    },
  },
  plugins: [],
}
