/**
 * ThemeContext — stores selected theme in localStorage, applies CSS variables
 * on :root, and exposes useTheme() hook.
 *
 * The theme is applied synchronously before the first render (via applyInitialTheme
 * called in main.tsx) so there is no flash of wrong colours.
 */
import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { themes, DEFAULT_THEME_ID, applyTheme, type Theme } from '@/styles/design-tokens'
import { capture } from '@/utils/posthog'

const STORAGE_KEY = 'sf-theme'

// ── Read persisted theme (sync, safe for SSR-less SPA) ──────────────────────

function getStoredThemeId(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? DEFAULT_THEME_ID
  } catch {
    return DEFAULT_THEME_ID
  }
}

// ── Apply theme before React mounts (call in main.tsx) ──────────────────────

export function applyInitialTheme(): void {
  applyTheme(getStoredThemeId())
}

// ── Context ─────────────────────────────────────────────────────────────────

interface ThemeContextValue {
  theme: Theme
  setTheme: (id: string) => void
  themes: Theme[]
}

const ThemeCtx = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [currentId, setCurrentId] = useState(getStoredThemeId)

  const currentTheme = themes.find((t) => t.id === currentId) ?? themes[0]

  const setTheme = useCallback(
    (id: string) => {
      const prev = currentId
      setCurrentId(id)
      try {
        localStorage.setItem(STORAGE_KEY, id)
      } catch {
        // quota exceeded — ignore
      }
      applyTheme(id)
      if (prev !== id) {
        capture('theme_changed', { from_theme: prev, to_theme: id })
      }
    },
    [currentId],
  )

  return (
    <ThemeCtx.Provider value={{ theme: currentTheme, setTheme, themes }}>
      {children}
    </ThemeCtx.Provider>
  )
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeCtx)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
