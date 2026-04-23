import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { LogOut, User as UserIcon } from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '@/context/AuthContext'
import { capture } from '@/utils/posthog'

// B-028. Avatar + dropdown menu in the TopNav right edge. AuthContext
// already exposes `signOut()`; this component is the first UI surface
// that actually invokes it.
export function UserMenu() {
  const { user, signOut } = useAuth()
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const triggerRef = useRef<HTMLButtonElement | null>(null)

  useEffect(() => {
    if (!open) return
    const onDocClick = (e: MouseEvent) => {
      if (!containerRef.current) return
      if (!containerRef.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false)
        triggerRef.current?.focus()
      }
    }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  if (!user) return null

  const initial = user.name?.trim().charAt(0).toUpperCase() || '?'

  const handleSignOut = async () => {
    capture('sign_out_clicked', { source: 'topnav_avatar' })
    setOpen(false)
    await signOut()
  }

  return (
    <div ref={containerRef} className="relative" data-testid="user-menu">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Open user menu"
        data-testid="user-menu-trigger"
        className="flex items-center justify-center w-9 h-9 rounded-full border border-contrast/10 bg-bg-surface hover:border-accent-primary/40 transition-colors overflow-hidden"
      >
        {user.avatar_url ? (
          <img
            src={user.avatar_url}
            alt={user.name}
            referrerPolicy="no-referrer"
            className="w-full h-full object-cover"
          />
        ) : (
          <span className="text-sm font-semibold text-accent-primary">{initial}</span>
        )}
      </button>

      {open && (
        <div
          role="menu"
          aria-label="User menu"
          data-testid="user-menu-dropdown"
          className={clsx(
            'absolute right-0 mt-2 w-56 rounded-xl border border-contrast/[0.08] bg-bg-surface shadow-xl z-50 overflow-hidden',
          )}
        >
          <div className="px-3 py-2 border-b border-contrast/[0.06]">
            <p className="text-sm font-semibold text-text-primary truncate">{user.name}</p>
            <p className="text-[11px] text-text-muted truncate">{user.email}</p>
          </div>

          <Link
            to="/profile"
            role="menuitem"
            data-testid="user-menu-profile"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-contrast/[0.04] transition-colors"
          >
            <UserIcon size={14} />
            Profile
          </Link>

          <button
            type="button"
            role="menuitem"
            data-testid="user-menu-signout"
            onClick={handleSignOut}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:text-danger hover:bg-contrast/[0.04] transition-colors text-left border-t border-contrast/[0.06]"
          >
            <LogOut size={14} />
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}

export default UserMenu
