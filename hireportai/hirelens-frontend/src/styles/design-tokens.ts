/**
 * Design System Tokens — SkillForge
 *
 * Three themes: Dark (default), Light, Midnight Blue.
 * Each theme defines CSS variables that are applied to :root by ThemeContext.
 *
 * Variable naming:
 *   --color-*   = space-separated RGB (for Tailwind opacity modifiers)
 *   --*         = hex or full CSS value (for inline styles / CSS usage)
 *   --sf-*      = LandingPage design tokens (Midnight Forge visual language)
 */

// ── Typography Scale ────────────────────────────────────────────────────────

export const typography = {
  xs: '12px',
  sm: '14px',
  base: '16px',
  lg: '18px',
  xl: '20px',
  '2xl': '24px',
  '3xl': '30px',
  '4xl': '36px',
} as const

// ── Spacing Scale (4px increments) ──────────────────────────────────────────

export const spacing = [4, 8, 12, 16, 20, 24, 32, 40, 48, 64] as const

// ── Border Radius ───────────────────────────────────────────────────────────

export const radius = {
  sm: '4px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  full: '9999px',
} as const

// ── Shadows ─────────────────────────────────────────────────────────────────

export const shadows = {
  sm: '0 1px 2px rgba(0,0,0,0.2), 0 2px 8px rgba(0,0,0,0.15)',
  md: '0 4px 16px rgba(0,0,0,0.25), 0 1px 4px rgba(0,0,0,0.2)',
  lg: '0 16px 48px rgba(0,0,0,0.4), 0 2px 8px rgba(0,0,0,0.3)',
} as const

// ── Transitions ─────────────────────────────────────────────────────────────

export const transitions = {
  fast: '150ms',
  normal: '250ms',
  slow: '350ms',
} as const

// ── Theme type ──────────────────────────────────────────────────────────────

export interface Theme {
  id: string
  name: string
  /** CSS variables to set on :root */
  vars: Record<string, string>
  /**
   * Browser `color-scheme` for native form controls (date picker,
   * scrollbars, spinners). Without this set, the native `<input type="date">`
   * calendar icon renders dark-on-dark on dark themes and is invisible.
   */
  colorScheme: 'dark' | 'light'
}

// ── Dark Theme (default) ────────────────────────────────────────────────────

const dark: Theme = {
  id: 'dark',
  name: 'Dark',
  colorScheme: 'dark',
  vars: {
    // ── App colors (hex for inline styles) ──
    '--bg-base': '#0A0A0B',
    '--bg-surface': '#111113',
    '--bg-elevated': '#1A1A1D',
    '--bg-overlay': '#242428',
    '--accent-primary': '#DC2626',
    '--accent-secondary': '#EF4444',
    '--text-primary': '#FAFAFA',
    '--text-secondary': '#A3A3A3',
    '--text-muted': '#525252',
    '--success': '#22c55e',
    '--warning': '#eab308',
    '--danger': '#ef4444',
    '--border': 'rgba(255, 255, 255, 0.06)',
    '--border-accent': 'rgba(220, 38, 38, 0.3)',
    '--accent-glow': 'rgba(220, 38, 38, 0.15)',

    // ── App colors (space-separated RGB for Tailwind opacity) ──
    '--color-bg-base': '10 10 11',
    '--color-bg-surface': '17 17 19',
    '--color-bg-elevated': '26 26 29',
    '--color-bg-overlay': '36 36 40',
    '--color-accent-primary': '220 38 38',
    '--color-accent-secondary': '239 68 68',
    '--color-text-primary': '250 250 250',
    '--color-text-secondary': '163 163 163',
    '--color-text-muted': '82 82 82',
    '--color-success': '34 197 94',
    '--color-warning': '234 179 8',
    '--color-danger': '239 68 68',
    '--color-contrast': '255 255 255',

    // ── Score colors (RGB) ──
    '--color-score-high': '34 197 94',
    '--color-score-mid': '234 179 8',
    '--color-score-low': '239 68 68',

    // ── Landing page --sf-* tokens ──
    '--sf-bg-primary': '#06060A',
    '--sf-bg-secondary': '#0C0C14',
    '--sf-bg-tertiary': '#12121E',
    '--sf-bg-elevated': '#1A1A2E',
    '--sf-bg-glass': 'rgba(18, 18, 30, 0.7)',
    '--sf-accent-primary': '#00D4FF',
    '--sf-accent-secondary': '#7B61FF',
    '--sf-accent-warm': '#FF8A50',
    '--sf-accent-success': '#00E68A',
    '--sf-accent-danger': '#FF4D6A',
    '--sf-text-primary': '#F0F0F5',
    '--sf-text-secondary': '#9494A8',
    '--sf-text-tertiary': '#5A5A72',
    '--sf-text-on-accent': '#06060A',
    '--sf-border-subtle': 'rgba(148, 148, 168, 0.12)',
    '--sf-border-medium': 'rgba(148, 148, 168, 0.25)',
    '--sf-border-accent': 'rgba(0, 212, 255, 0.3)',
    '--sf-gradient-hero': 'linear-gradient(135deg, #00D4FF 0%, #7B61FF 50%, #FF8A50 100%)',
    '--sf-gradient-cta': 'linear-gradient(135deg, #00D4FF 0%, #7B61FF 100%)',
    '--sf-gradient-warm': 'linear-gradient(135deg, #FF8A50 0%, #FF4D6A 100%)',
    '--sf-gradient-subtle': 'linear-gradient(180deg, rgba(0,212,255,0.08) 0%, transparent 60%)',
    '--sf-glow-accent': '0 0 20px rgba(0, 212, 255, 0.15), 0 0 60px rgba(0, 212, 255, 0.05)',
    '--sf-glow-warm': '0 0 20px rgba(255, 138, 80, 0.15), 0 0 60px rgba(255, 138, 80, 0.05)',
    '--sf-glow-card': '0 0 0 1px rgba(148, 148, 168, 0.12), 0 4px 24px rgba(0, 0, 0, 0.4)',

    // ── Landing page SF color RGB (for CSS utility classes) ──
    '--sf-accent-primary-rgb': '0 212 255',
    '--sf-accent-secondary-rgb': '123 97 255',
    '--sf-accent-warm-rgb': '255 138 80',
    '--sf-contrast-rgb': '148 148 168',
  },
}

// ── Light Theme ─────────────────────────────────────────────────────────────

const light: Theme = {
  id: 'light',
  name: 'Light',
  colorScheme: 'light',
  vars: {
    '--bg-base': '#FAFAFA',
    '--bg-surface': '#FFFFFF',
    '--bg-elevated': '#F0F0F2',
    '--bg-overlay': '#E5E5E8',
    '--accent-primary': '#DC2626',
    '--accent-secondary': '#EF4444',
    '--text-primary': '#18181B',
    '--text-secondary': '#52525B',
    '--text-muted': '#A1A1AA',
    '--success': '#16a34a',
    '--warning': '#ca8a04',
    '--danger': '#dc2626',
    '--border': 'rgba(0, 0, 0, 0.08)',
    '--border-accent': 'rgba(220, 38, 38, 0.3)',
    '--accent-glow': 'rgba(220, 38, 38, 0.1)',

    '--color-bg-base': '250 250 250',
    '--color-bg-surface': '255 255 255',
    '--color-bg-elevated': '240 240 242',
    '--color-bg-overlay': '229 229 232',
    '--color-accent-primary': '220 38 38',
    '--color-accent-secondary': '239 68 68',
    '--color-text-primary': '24 24 27',
    '--color-text-secondary': '82 82 91',
    '--color-text-muted': '161 161 170',
    '--color-success': '22 163 74',
    '--color-warning': '202 138 4',
    '--color-danger': '220 38 38',
    '--color-contrast': '0 0 0',

    '--color-score-high': '22 163 74',
    '--color-score-mid': '202 138 4',
    '--color-score-low': '220 38 38',

    '--sf-bg-primary': '#FAFAFA',
    '--sf-bg-secondary': '#F0F0F5',
    '--sf-bg-tertiary': '#FFFFFF',
    '--sf-bg-elevated': '#E8E8F0',
    '--sf-bg-glass': 'rgba(255, 255, 255, 0.8)',
    '--sf-accent-primary': '#0091B8',
    '--sf-accent-secondary': '#5B41CF',
    '--sf-accent-warm': '#E67A40',
    '--sf-accent-success': '#16a34a',
    '--sf-accent-danger': '#DC2626',
    '--sf-text-primary': '#1A1A2E',
    '--sf-text-secondary': '#6B6B80',
    '--sf-text-tertiary': '#9494A8',
    '--sf-text-on-accent': '#FFFFFF',
    '--sf-border-subtle': 'rgba(0, 0, 0, 0.08)',
    '--sf-border-medium': 'rgba(0, 0, 0, 0.15)',
    '--sf-border-accent': 'rgba(0, 145, 184, 0.3)',
    '--sf-gradient-hero': 'linear-gradient(135deg, #0091B8 0%, #5B41CF 50%, #E67A40 100%)',
    '--sf-gradient-cta': 'linear-gradient(135deg, #0091B8 0%, #5B41CF 100%)',
    '--sf-gradient-warm': 'linear-gradient(135deg, #E67A40 0%, #DC2626 100%)',
    '--sf-gradient-subtle': 'linear-gradient(180deg, rgba(0,145,184,0.06) 0%, transparent 60%)',
    '--sf-glow-accent': '0 0 20px rgba(0, 145, 184, 0.1), 0 0 60px rgba(0, 145, 184, 0.03)',
    '--sf-glow-warm': '0 0 20px rgba(230, 122, 64, 0.1), 0 0 60px rgba(230, 122, 64, 0.03)',
    '--sf-glow-card': '0 0 0 1px rgba(0, 0, 0, 0.08), 0 4px 24px rgba(0, 0, 0, 0.06)',

    '--sf-accent-primary-rgb': '0 145 184',
    '--sf-accent-secondary-rgb': '91 65 207',
    '--sf-accent-warm-rgb': '230 122 64',
    '--sf-contrast-rgb': '0 0 0',
  },
}

// ── Midnight Blue Theme ─────────────────────────────────────────────────────

const midnightBlue: Theme = {
  id: 'midnight-blue',
  name: 'Midnight Blue',
  colorScheme: 'dark',
  vars: {
    '--bg-base': '#060810',
    '--bg-surface': '#0C1020',
    '--bg-elevated': '#141A2E',
    '--bg-overlay': '#1C2340',
    '--accent-primary': '#3B82F6',
    '--accent-secondary': '#60A5FA',
    '--text-primary': '#F0F6FF',
    '--text-secondary': '#94A3B8',
    '--text-muted': '#475569',
    '--success': '#22c55e',
    '--warning': '#eab308',
    '--danger': '#ef4444',
    '--border': 'rgba(148, 163, 184, 0.08)',
    '--border-accent': 'rgba(59, 130, 246, 0.3)',
    '--accent-glow': 'rgba(59, 130, 246, 0.15)',

    '--color-bg-base': '6 8 16',
    '--color-bg-surface': '12 16 32',
    '--color-bg-elevated': '20 26 46',
    '--color-bg-overlay': '28 35 64',
    '--color-accent-primary': '59 130 246',
    '--color-accent-secondary': '96 165 250',
    '--color-text-primary': '240 246 255',
    '--color-text-secondary': '148 163 184',
    '--color-text-muted': '71 85 105',
    '--color-success': '34 197 94',
    '--color-warning': '234 179 8',
    '--color-danger': '239 68 68',
    '--color-contrast': '255 255 255',

    '--color-score-high': '34 197 94',
    '--color-score-mid': '234 179 8',
    '--color-score-low': '239 68 68',

    '--sf-bg-primary': '#060810',
    '--sf-bg-secondary': '#0C1020',
    '--sf-bg-tertiary': '#141A2E',
    '--sf-bg-elevated': '#1C2340',
    '--sf-bg-glass': 'rgba(20, 26, 46, 0.7)',
    '--sf-accent-primary': '#38BDF8',
    '--sf-accent-secondary': '#818CF8',
    '--sf-accent-warm': '#FB923C',
    '--sf-accent-success': '#22c55e',
    '--sf-accent-danger': '#F87171',
    '--sf-text-primary': '#F0F6FF',
    '--sf-text-secondary': '#8B95A5',
    '--sf-text-tertiary': '#4A5568',
    '--sf-text-on-accent': '#060810',
    '--sf-border-subtle': 'rgba(148, 163, 184, 0.1)',
    '--sf-border-medium': 'rgba(148, 163, 184, 0.2)',
    '--sf-border-accent': 'rgba(56, 189, 248, 0.3)',
    '--sf-gradient-hero': 'linear-gradient(135deg, #38BDF8 0%, #818CF8 50%, #FB923C 100%)',
    '--sf-gradient-cta': 'linear-gradient(135deg, #38BDF8 0%, #818CF8 100%)',
    '--sf-gradient-warm': 'linear-gradient(135deg, #FB923C 0%, #F87171 100%)',
    '--sf-gradient-subtle': 'linear-gradient(180deg, rgba(56,189,248,0.08) 0%, transparent 60%)',
    '--sf-glow-accent': '0 0 20px rgba(56, 189, 248, 0.15), 0 0 60px rgba(56, 189, 248, 0.05)',
    '--sf-glow-warm': '0 0 20px rgba(251, 146, 60, 0.15), 0 0 60px rgba(251, 146, 60, 0.05)',
    '--sf-glow-card': '0 0 0 1px rgba(148, 163, 184, 0.1), 0 4px 24px rgba(0, 0, 0, 0.5)',

    '--sf-accent-primary-rgb': '56 189 248',
    '--sf-accent-secondary-rgb': '129 140 248',
    '--sf-accent-warm-rgb': '251 146 60',
    '--sf-contrast-rgb': '255 255 255',
  },
}

// ── Shared tokens (same across all themes) ──────────────────────────────────

const shared: Record<string, string> = {
  '--sf-font-display': "'Cabinet Grotesk', 'Satoshi', system-ui, sans-serif",
  '--sf-font-body': "'General Sans', 'Switzer', system-ui, sans-serif",
  '--sf-font-mono': "'JetBrains Mono', 'Fira Code', monospace",
  '--sf-space-xs': '4px',
  '--sf-space-sm': '8px',
  '--sf-space-md': '16px',
  '--sf-space-lg': '24px',
  '--sf-space-xl': '32px',
  '--sf-space-2xl': '48px',
  '--sf-space-3xl': '64px',
  '--sf-space-4xl': '96px',
  '--sf-radius-sm': '6px',
  '--sf-radius-md': '10px',
  '--sf-radius-lg': '16px',
  '--sf-radius-xl': '24px',
  '--sf-radius-full': '999px',
  '--sf-ease-out': 'cubic-bezier(0.16, 1, 0.3, 1)',
  '--sf-ease-spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
  '--sf-duration-fast': '150ms',
  '--sf-duration-normal': '300ms',
  '--sf-duration-slow': '500ms',
}

// ── Exports ─────────────────────────────────────────────────────────────────

export const themes: Theme[] = [dark, light, midnightBlue]

export const DEFAULT_THEME_ID = 'dark'

/** Apply a theme's CSS variables (plus shared tokens) to an element. */
export function applyTheme(themeId: string, el: HTMLElement = document.documentElement): void {
  const theme = themes.find((t) => t.id === themeId) ?? themes[0]
  const allVars = { ...shared, ...theme.vars }
  for (const [prop, value] of Object.entries(allVars)) {
    el.style.setProperty(prop, value)
  }
  // B-026: set `color-scheme` so native form controls (date picker calendar
  // icon, scrollbars, number spinners) render with theme-aware chrome.
  // Without this, `<input type="date">` shows a dark-grey icon on dark
  // backgrounds that's effectively invisible.
  el.style.colorScheme = theme.colorScheme
}
