/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        display: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Calm green: links, active items, focus rings
        brand: {
          50: '#f1f7f4',
          100: '#deede6',
          200: '#bddbcd',
          300: '#92c2ae',
          400: '#63a48b',
          500: '#438870',
          600: '#326d59',
          700: '#2a5849',
          800: '#24473c',
          900: '#1f3b32',
          950: '#0f211c',
        },
        // Warm accent, used sparingly (counts, admin labels)
        accent: {
          50: '#fdf5ef',
          100: '#fae8d9',
          200: '#f4cdb1',
          300: '#edac80',
          400: '#e4854f',
          500: '#dc682e',
          600: '#c85123',
          700: '#a63d1f',
          800: '#853320',
          900: '#6c2c1d',
        },
        surface: {
          light: '#faf9f7',
          dark: '#1a1a19',
        },
        panel: {
          dark: '#242423',
        },
        sidebar: {
          light: '#f3f2ee',
          dark: '#141413',
        },
      },
      borderRadius: {
        xl: '0.75rem',
        '2xl': '1rem',
        '3xl': '1.25rem',
      },
      boxShadow: {
        subtle: '0 1px 2px 0 rgba(0,0,0,0.04)',
        card: 'none',
        'card-hover': '0 4px 16px -8px rgba(0,0,0,0.16)',
        glow: 'none',
        float: '0 8px 30px -12px rgba(0,0,0,0.25)',
      },
      fontSize: {
        xs: ['0.75rem', { lineHeight: '1.1rem' }],
        sm: ['0.875rem', { lineHeight: '1.35rem' }],
        base: ['0.9375rem', { lineHeight: '1.5rem' }],
        lg: ['1.0625rem', { lineHeight: '1.6rem' }],
        xl: ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.3rem' }],
      },
      backgroundImage: {
        // Kept as flat colours so older class names stay calm.
        'brand-gradient': 'linear-gradient(#326d59, #326d59)',
        'hero-gradient': 'linear-gradient(#24473c, #24473c)',
      },
    },
  },
  plugins: [],
}
