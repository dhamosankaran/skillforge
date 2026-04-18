import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'

const EXEMPT = ['/', '/login', '/onboarding/persona']

export function PersonaGate({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const { pathname } = useLocation()
  if (!user) return <>{children}</>
  if (user.persona !== null) return <>{children}</>
  if (EXEMPT.includes(pathname)) return <>{children}</>
  return <Navigate to="/onboarding/persona" replace />
}

export default PersonaGate
