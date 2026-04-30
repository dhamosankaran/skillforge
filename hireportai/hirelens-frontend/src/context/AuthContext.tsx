/**
 * AuthContext — backend JWT auth.
 *
 * Flow:
 *   1. Google One Tap fires → signIn(credential) POSTs to /api/v1/auth/google
 *   2. Backend returns {access_token, refresh_token, user}
 *   3. Tokens stored in localStorage; React state updated.
 *   4. On every page load, GET /api/v1/auth/me re-validates the stored token.
 *      If it returns 401 the stale tokens are cleared (no refresh attempted
 *      at hydration time — user re-signs-in next visit).
 *
 * Raw axios (not the intercepted api instance) is used here to avoid
 * circular dependency with services/api.ts.
 */
import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from 'react'
import axios from 'axios'

export type Persona = 'interview_prepper' | 'career_climber' | 'team_lead'

export interface AuthUser {
  id: string
  email: string
  name: string
  avatar_url: string | null
  role: 'user' | 'admin'
  persona: Persona | null
  onboarding_completed: boolean
  /**
   * @deprecated spec #57 — interview targets moved to per-tracker-row
   * `tracker_applications_v2.interview_date`. Read via
   * `homeState.context.next_interview` instead. Retained on the response
   * for one release while the dual-write window stays open; removed in
   * the Phase-6 cleanup slice.
   */
  interview_target_company?: string | null
  /**
   * @deprecated spec #57 — see `interview_target_company` note. Read the
   * nearest upcoming interview via `homeState.context.next_interview`.
   */
  interview_target_date?: string | null
  home_first_visit_seen_at?: string | null
}

interface AuthContextValue {
  user: AuthUser | null
  isLoading: boolean
  signIn: (credential: string) => Promise<void>
  signOut: () => Promise<void>
  updateUser: (patch: Partial<AuthUser>) => void
}

export const STORAGE_KEY_ACCESS = 'skillforge_access_token'
export const STORAGE_KEY_REFRESH = 'skillforge_refresh_token'
const STORAGE_KEY_USER = 'skillforge_user'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

function clearStorage() {
  localStorage.removeItem(STORAGE_KEY_ACCESS)
  localStorage.removeItem(STORAGE_KEY_REFRESH)
  localStorage.removeItem(STORAGE_KEY_USER)
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Hydration: re-validate stored token on every page load.
  // Uses raw axios (not the intercepted api instance) so the refresh
  // interceptor in api.ts is not triggered during initial load.
  useEffect(() => {
    const token = localStorage.getItem(STORAGE_KEY_ACCESS)
    if (!token) {
      setIsLoading(false)
      return
    }
    axios
      .get<AuthUser>(`${BASE_URL}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then((res) => {
        setUser(res.data)
        localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(res.data))
      })
      .catch(() => clearStorage())
      .finally(() => setIsLoading(false))
  }, [])

  const signIn = useCallback(async (credential: string): Promise<void> => {
    const res = await axios.post<{
      access_token: string
      refresh_token: string
      user: AuthUser
    }>(`${BASE_URL}/api/v1/auth/google`, { credential })
    const { access_token, refresh_token, user: backendUser } = res.data
    localStorage.setItem(STORAGE_KEY_ACCESS, access_token)
    localStorage.setItem(STORAGE_KEY_REFRESH, refresh_token)
    localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(backendUser))
    setUser(backendUser)
  }, [])

  const updateUser = useCallback((patch: Partial<AuthUser>) => {
    setUser((prev) => {
      if (!prev) return prev
      const updated = { ...prev, ...patch }
      localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(updated))
      return updated
    })
  }, [])

  const signOut = useCallback(async (): Promise<void> => {
    const token = localStorage.getItem(STORAGE_KEY_ACCESS)
    if (token) {
      // Best-effort — errors are swallowed; logout is always local.
      await axios
        .post(`${BASE_URL}/api/v1/auth/logout`, null, {
          headers: { Authorization: `Bearer ${token}` },
        })
        .catch(() => {})
    }
    clearStorage()
    setUser(null)
    window.location.href = '/'
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, signIn, signOut, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
