/**
 * ThemePicker — 3 theme cards with preview swatches.
 * Click to switch; instant transition.
 */
import { motion } from 'framer-motion'
import { Check, Palette } from 'lucide-react'
import clsx from 'clsx'
import { useTheme } from '@/context/ThemeContext'

/** Small swatch circles previewing a theme's palette. */
function Swatches({ vars }: { vars: Record<string, string> }) {
  const colors = [
    vars['--bg-base'],
    vars['--bg-surface'],
    vars['--accent-primary'],
    vars['--accent-secondary'],
    vars['--text-primary'],
  ]
  return (
    <div className="flex gap-1.5 mt-3">
      {colors.map((c, i) => (
        <div
          key={i}
          className="w-5 h-5 rounded-full border border-contrast/[0.1]"
          style={{ background: c }}
        />
      ))}
    </div>
  )
}

export function ThemePicker() {
  const { theme: current, setTheme, themes } = useTheme()

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <Palette size={14} className="text-accent-primary" />
        <h2 className="text-[11px] uppercase tracking-[0.15em] text-text-secondary font-semibold">
          Theme
        </h2>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {themes.map((t) => {
          const isActive = t.id === current.id
          return (
            <motion.button
              key={t.id}
              whileHover={{ y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setTheme(t.id)}
              className={clsx(
                'relative text-left rounded-xl border p-4 transition-all duration-200',
                isActive
                  ? 'border-accent-primary/40 bg-accent-primary/[0.06]'
                  : 'border-contrast/[0.08] bg-bg-surface/60 hover:border-contrast/[0.14]',
              )}
            >
              {isActive && (
                <div className="absolute top-3 right-3 w-5 h-5 rounded-full bg-accent-primary flex items-center justify-center">
                  <Check size={11} className="text-bg-base" strokeWidth={3} />
                </div>
              )}
              <p className="text-sm font-semibold text-text-primary">{t.name}</p>
              <Swatches vars={t.vars} />
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}
