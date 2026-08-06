import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        terminal: '#05070d',
        panel: '#0b1020',
        grid: '#182033',
        profit: '#00ff9c',
        loss: '#ff4d6d',
        amber: '#ffb000'
      },
      boxShadow: {
        glow: '0 0 30px rgba(0,255,156,0.12)'
      }
    }
  },
  plugins: []
};

export default config;
