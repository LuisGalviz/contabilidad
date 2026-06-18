import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: '#0B6B57', dark: '#075446' },
        accent: '#C68A2D',
      },
    },
  },
  plugins: [],
}

export default config
