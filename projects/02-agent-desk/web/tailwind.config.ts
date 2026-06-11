import type { Config } from 'tailwindcss'

export default {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        void: '#05070b',
        surface: '#0b1018', 
        panel: '#111823',
        text: '#e8eef7',
        muted: '#8b9bb4',
        accent: '#3dffb5',
        'accent-2': '#4cc9ff',
        line: 'rgba(148, 163, 184, 0.14)'
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        display: ['Syne', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace']
      }
    }
  },
  plugins: []
} satisfies Config