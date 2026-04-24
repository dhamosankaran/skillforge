import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import type { ReactNode } from 'react'
import toast from 'react-hot-toast'
import { fetchUsage, type UsageResponse } from '@/services/api'

export type PlanType = 'free' | 'pro' | 'enterprise'

interface UsageState {
  plan: PlanType
  scansUsed: number
  /** -1 sentinel = unlimited (Pro / Enterprise / admin). */
  maxScans: number
  /** Role flag — orthogonal to plan. Admin with plan=free has isAdmin=true. */
  isAdmin: boolean
}

interface UsageContextValue {
  usage: UsageState
  canScan: boolean
  /** True when the user has Pro-tier access (Pro plan or admin role). */
  canUsePro: boolean
  canUsePremium: boolean
  refreshUsage: () => Promise<void>
  upgradePlan: (plan: PlanType) => void
  showUpgradeModal: boolean
  setShowUpgradeModal: (show: boolean) => void
  checkAndPromptUpgrade: () => boolean
}

// Display-cache storage key (non-authoritative per spec #56 LD-2). Clearing
// this never grants an extra scan — the BE /payments/usage response is the
// source of truth and overwrites whatever is in localStorage on every fetch.
const STORAGE_KEY = 'skillforge_usage'

const PLAN_LABELS: Record<PlanType, string> = {
  free: 'Free',
  pro: 'Pro',
  enterprise: 'Enterprise',
}

const DEFAULT_STATE: UsageState = {
  plan: 'free',
  scansUsed: 0,
  maxScans: 1,  // spec #56 LD-1 — 1 lifetime scan for free; BE overwrites on hydrate
  isAdmin: false,
}

function loadDisplayCache(): UsageState {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      return {
        plan: parsed.plan ?? 'free',
        scansUsed: parsed.scansUsed ?? 0,
        maxScans: parsed.maxScans ?? 1,
        isAdmin: parsed.isAdmin ?? false,
      }
    }
  } catch {
    // ignore malformed cache
  }
  return DEFAULT_STATE
}

function writeDisplayCache(usage: UsageState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(usage))
  } catch {
    // localStorage can throw in private mode; non-fatal.
  }
}

function fromResponse(r: UsageResponse): UsageState {
  return {
    plan: r.plan,
    scansUsed: r.scans_used,
    maxScans: r.max_scans,
    isAdmin: r.is_admin,
  }
}

const UsageContext = createContext<UsageContextValue | null>(null)

export function UsageProvider({ children }: { children: ReactNode }) {
  const [usage, setUsage] = useState<UsageState>(loadDisplayCache)
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)

  // Pro + admin bypass the scan cap. `maxScans === -1` is the unlimited
  // sentinel from spec #56 §4.3; the admin flag is checked separately so an
  // admin-on-free-plan still reads as unlimited.
  const canUsePro = usage.plan === 'pro' || usage.plan === 'enterprise' || usage.isAdmin
  const canUsePremium = canUsePro
  const canScan = canUsePro || usage.maxScans === -1 || usage.scansUsed < usage.maxScans

  const refreshUsage = useCallback(async () => {
    try {
      const data = await fetchUsage()
      const next = fromResponse(data)
      setUsage(next)
      writeDisplayCache(next)
    } catch {
      // BE unreachable → keep whatever the display cache loaded. Safe
      // because the BE is still authoritative on the next analyze call
      // (the 402 is the hard gate).
    }
  }, [])

  useEffect(() => {
    void refreshUsage()
  }, [refreshUsage])

  const upgradePlan = useCallback((plan: PlanType) => {
    // Optimistic FE update; the real source of truth is the Stripe webhook +
    // BE response on next refreshUsage(). Called after a successful checkout
    // return so the UI reflects Pro immediately.
    setUsage((prev) => {
      const next: UsageState = {
        ...prev,
        plan,
        maxScans: plan === 'free' ? 1 : -1,
      }
      writeDisplayCache(next)
      return next
    })
    toast.success(`Upgraded to ${PLAN_LABELS[plan]}! 🎉`, { duration: 3000 })
    void refreshUsage()
  }, [refreshUsage])

  const checkAndPromptUpgrade = useCallback((): boolean => {
    if (!canScan) {
      setShowUpgradeModal(true)
      return false
    }
    return true
  }, [canScan])

  return (
    <UsageContext.Provider
      value={{
        usage,
        canScan,
        canUsePro,
        canUsePremium,
        refreshUsage,
        upgradePlan,
        showUpgradeModal,
        setShowUpgradeModal,
        checkAndPromptUpgrade,
      }}
    >
      {children}
    </UsageContext.Provider>
  )
}

export function useUsage(): UsageContextValue {
  const ctx = useContext(UsageContext)
  if (!ctx) throw new Error('useUsage must be used within UsageProvider')
  return ctx
}
