import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        slate: {
          850: '#172033',
        },
      },
    },
  },
  plugins: [],
} satisfies Config
