import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ShieldAlert } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'

// Spec #54 / E-040. Frontend counterpart to the backend `require_admin`
// dependency. Wraps the /admin route element so non-admins see a 403 view
// instead of downloading the AdminPanel lazy chunk past the in-component
// check. Returns null while auth is loading to avoid a flicker.
export function AdminGate({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) return null

  if (user?.role !== 'admin') {
    return (
      <div
        className="min-h-screen bg-bg-base flex items-center justify-center px-4"
        data-testid="admin-gate-forbidden"
      >
        <div className="max-w-md w-full text-center space-y-4">
          <ShieldAlert size={40} className="mx-auto text-danger" />
          <h1 className="font-display text-2xl font-bold text-text-primary">
            Admin access required.
          </h1>
          <p className="text-sm text-text-muted">
            You don't have permission to view this page.
          </p>
          <Link
            to="/home"
            className="inline-block text-sm text-accent-primary hover:text-accent-secondary transition-colors"
          >
            ← Back to home
          </Link>
        </div>
      </div>
    )
  }

  return <>{children}</>
}

export default AdminGate
