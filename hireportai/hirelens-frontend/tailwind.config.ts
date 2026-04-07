import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Syne', 'Inter', 'sans-serif'],
        editorial: ['"Bebas Neue"', 'Impact', 'sans-serif'],
        serif: ['"Playfair Display"', 'Georgia', 'serif'],
        body: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        'bg-base': '#0A0A0B',
        'bg-surface': '#111113',
        'bg-elevated': '#1A1A1D',
        'bg-overlay': '#242428',
        'accent-primary': '#DC2626',
        'accent-secondary': '#EF4444',
        'text-primary': '#FAFAFA',
        'text-secondary': '#A3A3A3',
        'text-muted': '#525252',
        success: '#22c55e',
        warning: '#eab308',
        danger: '#ef4444',
        'score-high': '#22c55e',
        'score-mid': '#eab308',
        'score-low': '#ef4444',
      },
      boxShadow: {
        glow: '0 0 20px rgba(220,38,38,0.15)',
        'glow-lg': '0 0 40px rgba(220,38,38,0.22)',
        'glow-xl': '0 0 60px rgba(220,38,38,0.28)',
        'glow-violet': '0 0 20px rgba(124,58,237,0.2)',
        'glow-red': '0 0 24px rgba(220,38,38,0.4)',
        'glow-green': '0 0 20px rgba(34,197,94,0.2)',
        'glow-yellow': '0 0 20px rgba(234,179,8,0.2)',
        card: '0 1px 2px rgba(0,0,0,0.4), 0 4px 16px rgba(0,0,0,0.3)',
        'card-hover': '0 2px 4px rgba(0,0,0,0.5), 0 8px 24px rgba(0,0,0,0.4)',
        modal: '0 16px 48px rgba(0,0,0,0.6), 0 2px 8px rgba(0,0,0,0.4)',
        'depth': '0 8px 30px rgba(0,0,0,0.5), 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.04)',
        'depth-hover': '0 16px 50px rgba(0,0,0,0.6), 0 4px 12px rgba(0,0,0,0.4), 0 0 30px rgba(220,38,38,0.08)',
      },
      borderRadius: {
        xl: '12px',
        '2xl': '16px',
        '3xl': '20px',
        '4xl': '24px',
      },
      animation: {
        'fade-up': 'fadeUp 0.5s ease-out',
        'glow-pulse': 'glowPulse 3s ease-in-out infinite',
        'scan-line': 'scanLine 1.5s linear infinite',
        float: 'float 4s ease-in-out infinite',
        'float-slow': 'float 6s ease-in-out infinite',
        'float-slower': 'float 8s ease-in-out infinite',
        'mesh-shift': 'meshShift 8s ease infinite',
        'spin-slow': 'spin 8s linear infinite',
        'spin-slower': 'spin 20s linear infinite',
        marquee: 'marquee 30s linear infinite',
        'marquee-fast': 'marquee 15s linear infinite',
        'marquee-slow': 'marquee 50s linear infinite',
        'line-grow': 'lineGrow 0.8s cubic-bezier(0.25,0.46,0.45,0.94) forwards',
        'gradient-x': 'gradientX 6s ease infinite',
        'aurora': 'aurora 15s ease-in-out infinite',
        'aurora-slow': 'aurora 22s ease-in-out infinite',
        'pulse-soft': 'pulseSoft 4s ease-in-out infinite',
        'shimmer': 'shimmer 4s linear infinite',
        'breathe': 'breathe 6s ease-in-out infinite',
        'orbit': 'orbit 20s linear infinite',
      },
      keyframes: {
        fadeUp: {
          from: { opacity: '0', transform: 'translateY(16px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        glowPulse: {
          '0%, 100%': { boxShadow: '0 0 16px rgba(220,38,38,0.1)' },
          '50%': { boxShadow: '0 0 36px rgba(220,38,38,0.28)' },
        },
        scanLine: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        meshShift: {
          '0%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        },
        marquee: {
          '0%': { transform: 'translateX(0%)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        lineGrow: {
          from: { transform: 'scaleX(0)', transformOrigin: 'left' },
          to: { transform: 'scaleX(1)', transformOrigin: 'left' },
        },
        gradientX: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        aurora: {
          '0%': { transform: 'translate(0, 0) rotate(0deg) scale(1)' },
          '25%': { transform: 'translate(30px, -50px) rotate(90deg) scale(1.1)' },
          '50%': { transform: 'translate(-20px, 20px) rotate(180deg) scale(0.95)' },
          '75%': { transform: 'translate(40px, 30px) rotate(270deg) scale(1.05)' },
          '100%': { transform: 'translate(0, 0) rotate(360deg) scale(1)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '0.5' },
          '50%': { opacity: '1' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% center' },
          '100%': { backgroundPosition: '200% center' },
        },
        breathe: {
          '0%, 100%': { transform: 'scale(1)', opacity: '0.5' },
          '50%': { transform: 'scale(1.05)', opacity: '0.8' },
        },
        orbit: {
          '0%': { transform: 'rotate(0deg) translateX(100px) rotate(0deg)' },
          '100%': { transform: 'rotate(360deg) translateX(100px) rotate(-360deg)' },
        },
      },
      backgroundImage: {
        'gradient-mesh':
          'radial-gradient(ellipse at 20% 50%, rgba(220,38,38,0.07) 0%, transparent 50%), radial-gradient(ellipse at 80% 20%, rgba(220,38,38,0.04) 0%, transparent 50%)',
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [],
}

export default config
