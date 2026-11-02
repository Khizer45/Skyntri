/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['"Plus Jakarta Sans"', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Fresh teal - calm, clinical, skincare
        brand: {
          50: '#ecfdf8',
          100: '#d1faee',
          200: '#a7f3df',
          300: '#6ee7cb',
          400: '#34d3b1',
          500: '#12b79a',
          600: '#09947e',
          700: '#0b7667',
          800: '#0e5d53',
          900: '#0f4d45',
          950: '#042f2b',
        },
        // Warm coral accent - highlights, badges, shop
        accent: {
          50: '#fff4f1',
          100: '#ffe6df',
          200: '#ffcfc2',
          300: '#ffad97',
          400: '#ff7f5f',
          500: '#f8603a',
          600: '#e5441d',
          700: '#c03515',
          800: '#9e2f17',
          900: '#832c19',
        },
        surface: {
          light: '#f6f8f7',
          dark: '#0b1012',
        },
        panel: {
          dark: '#121a1d',
        },
      },
      borderRadius: {
        xl: '0.875rem',
        '2xl': '1.125rem',
        '3xl': '1.5rem',
      },
      boxShadow: {
        subtle: '0 1px 2px 0 rgba(16,24,40,0.04)',
        card: '0 1px 2px rgba(16,24,40,0.04), 0 4px 16px -6px rgba(16,24,40,0.08)',
        'card-hover': '0 2px 4px rgba(16,24,40,0.05), 0 12px 28px -10px rgba(16,24,40,0.18)',
        glow: '0 8px 24px -8px rgba(9,148,126,0.45)',
      },
      fontSize: {
        xs: ['0.75rem', { lineHeight: '1rem' }],
        sm: ['0.8125rem', { lineHeight: '1.25rem' }],
        base: ['0.875rem', { lineHeight: '1.375rem' }],
        lg: ['1rem', { lineHeight: '1.5rem' }],
        xl: ['1.125rem', { lineHeight: '1.65rem' }],
        '2xl': ['1.375rem', { lineHeight: '1.85rem' }],
        '3xl': ['1.75rem', { lineHeight: '2.2rem' }],
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(135deg, #09947e 0%, #12b79a 55%, #34d3b1 100%)',
        'hero-gradient': 'linear-gradient(120deg, #0b7667 0%, #09947e 45%, #12b79a 100%)',
      },
    },
  },
  plugins: [],
}
