/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        notion: {
          bg:       '#f7f6f3',
          white:    '#ffffff',
          border:   '#e9e8e4',
          hover:    '#f1f1ef',
          text:     '#37352f',
          muted:    '#787774',
          faint:    '#9b9a97',
          green:    '#0f9b58',
          greenBg:  '#edf3ec',
          blue:     '#337ea9',
          blueBg:   '#e7f0f6',
          yellow:   '#cb912f',
          yellowBg: '#fdf3e4',
          purple:   '#6940a5',
          purpleBg: '#f4f0f9',
          red:      '#e03e3e',
          redBg:    '#fdecea',
        }
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'notion': '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        'notion-md': '0 4px 12px rgba(0,0,0,0.08), 0 1px 3px rgba(0,0,0,0.05)',
      },
    },
  },
  plugins: [],
}
