/**
 * AuthContext — Google Sign-In via @react-oauth/google
 *
 * Usage: wrap app with <AuthProvider> (inside <GoogleOAuthProvider>)
 * then call useAuth() in any component.
 *
 * The Google client ID comes from VITE_GOOGLE_CLIENT_ID in .env.
 * If the key is missing the provider still renders; the sign-in button
 * will fail gracefully with a console warning.
 */
import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from 'react'

export interface AuthUser {
  name: string
  email: string
  picture: string
  googleId: string
}

interface AuthContextValue {
  user: AuthUser | null
  signIn: (credential: string) => void
  signOut: () => void
}

const STORAGE_KEY = 'hireport_user'

function loadUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as AuthUser) : null
  } catch {
    return null
  }
}

/** Decode the JWT credential returned by Google One Tap / Sign-In button */
function decodeGoogleJwt(token: string): AuthUser | null {
  try {
    const payload = token.split('.')[1]
    const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')))
    return {
      name: decoded.name || decoded.email,
      email: decoded.email,
      picture: decoded.picture || '',
      googleId: decoded.sub,
    }
  } catch {
    return null
  }
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(loadUser)

  const signIn = useCallback((credential: string) => {
    const decoded = decodeGoogleJwt(credential)
    if (!decoded) return
    setUser(decoded)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(decoded))
  }, [])

  const signOut = useCallback(() => {
    setUser(null)
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  return (
    <AuthContext.Provider value={{ user, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
