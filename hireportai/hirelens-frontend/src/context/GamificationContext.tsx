/**
 * GamificationContext — shared XP/streak/badges store.
 *
 * Why a context: the StreakBadge in the navbar and the Profile page need to
 * stay in sync after a review. Rather than each subscribing to its own
 * fetch, they share one cached stats object that gets refreshed whenever a
 * review (or other XP-earning event) finishes.
 *
 * Usage:
 *   const { stats, refresh } = useGamification()
 *   await submitReview(...)
 *   await refresh()  // pulls the new XP/streak from the backend
 *
 * Side effect: this provider also detects streak transitions and badge
 * additions across refreshes, and fires PostHog `streak_incremented` and
 * `badge_earned` events client-side. Server analytics already covers these,
 * but the client-side captures power funnels keyed off frontend session ids.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { fetchGamificationStats } from '@/services/api'
import { capture } from '@/utils/posthog'
import { useAuth } from '@/context/AuthContext'
import type { GamificationStats } from '@/types'

interface GamificationContextValue {
  stats: GamificationStats | null
  isLoading: boolean
  error: string | null
  refresh: () => Promise<void>
}

const GamificationContext = createContext<GamificationContextValue | null>(null)

export function GamificationProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [stats, setStats] = useState<GamificationStats | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Track previous values so we can detect transitions on each refresh.
  const prevStreakRef = useRef<number | null>(null)
  const prevBadgeIdsRef = useRef<Set<string>>(new Set())

  const refresh = useCallback(async () => {
    if (!user) {
      setStats(null)
      prevStreakRef.current = null
      prevBadgeIdsRef.current = new Set()
      return
    }
    setIsLoading(true)
    setError(null)
    try {
      const next = await fetchGamificationStats()

      // Detect streak transitions (n → n+1) and emit analytics.
      const prevStreak = prevStreakRef.current
      if (prevStreak !== null && next.current_streak > prevStreak) {
        capture('streak_incremented', {
          new_length: next.current_streak,
          previous_length: prevStreak,
        })
      }
      prevStreakRef.current = next.current_streak

      // Detect newly earned badges since the last refresh.
      const prevIds = prevBadgeIdsRef.current
      for (const b of next.badges) {
        if (!prevIds.has(b.badge_id)) {
          // Only emit when we have a real baseline (not the first hydration).
          if (prevIds.size > 0) {
            capture('badge_earned', { badge_id: b.badge_id, badge_name: b.name })
          }
          prevIds.add(b.badge_id)
        }
      }

      setStats(next)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to load stats'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }, [user])

  // Hydrate on sign-in; clear on sign-out.
  useEffect(() => {
    void refresh()
  }, [refresh])

  return (
    <GamificationContext.Provider value={{ stats, isLoading, error, refresh }}>
      {children}
    </GamificationContext.Provider>
  )
}

export function useGamification(): GamificationContextValue {
  const ctx = useContext(GamificationContext)
  if (!ctx) {
    throw new Error('useGamification must be used inside <GamificationProvider>')
  }
  return ctx
}
