import { createContext, useContext, useState, useCallback } from 'react'
import type { ReactNode } from 'react'
import toast from 'react-hot-toast'
import { capture } from '@/utils/posthog'

export type PlanType = 'free' | 'pro'

interface UsageState {
  plan: PlanType
  scansUsed: number
  maxScans: number  // 3 for free, Infinity for pro
}

interface UsageContextValue {
  usage: UsageState
  canScan: boolean
  canUsePro: boolean       // true for pro
  canUsePremium: boolean   // alias for canUsePro (pro includes all features)
  incrementScan: () => void
  upgradePlan: (plan: PlanType) => void
  showUpgradeModal: boolean
  setShowUpgradeModal: (show: boolean) => void
  checkAndPromptUpgrade: () => boolean
}

const STORAGE_KEY = 'skillforge_usage'

const PLAN_LABELS: Record<PlanType, string> = {
  free: 'Free',
  pro: 'Pro',
}

function loadUsage(): UsageState {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      return {
        plan: parsed.plan || 'free',
        scansUsed: parsed.scansUsed || 0,
        maxScans: parsed.plan === 'free' ? 3 : Infinity,
      }
    }
  } catch {
    // ignore
  }
  return { plan: 'free', scansUsed: 0, maxScans: 3 }
}

function saveUsage(usage: UsageState) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    plan: usage.plan,
    scansUsed: usage.scansUsed,
  }))
}

const UsageContext = createContext<UsageContextValue | null>(null)

export function UsageProvider({ children }: { children: ReactNode }) {
  const [usage, setUsage] = useState<UsageState>(loadUsage)
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)

  const canScan = usage.plan !== 'free' || usage.scansUsed < usage.maxScans
  const canUsePro = usage.plan === 'pro'
  const canUsePremium = canUsePro  // pro tier includes all features

  const incrementScan = useCallback(() => {
    setUsage((prev) => {
      const next = { ...prev, scansUsed: prev.scansUsed + 1 }
      saveUsage(next)
      return next
    })
  }, [])

  const upgradePlan = useCallback((plan: PlanType) => {
    setUsage((prev) => {
      const next: UsageState = {
        plan,
        scansUsed: prev.scansUsed,
        maxScans: plan === 'pro' ? Infinity : 3,
      }
      saveUsage(next)
      return next
    })
    toast.success(`Upgraded to ${PLAN_LABELS[plan]}! 🎉`, { duration: 3000 })
  }, [])

  const checkAndPromptUpgrade = useCallback((): boolean => {
    if (!canScan) {
      setShowUpgradeModal(true)
      capture('paywall_hit', {
        trigger: 'scan_limit',
        scans_used: usage.scansUsed,
        plan: usage.plan,
      })
      return false
    }
    return true
  }, [canScan, usage.scansUsed, usage.plan])

  return (
    <UsageContext.Provider
      value={{
        usage,
        canScan,
        canUsePro,
        canUsePremium,
        incrementScan,
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
