/**
 * UpgradeModal — app-root paywall bridged to UsageContext.
 *
 * Kept as a thin wrapper around <PaywallModal> so callers that open
 * the paywall via `useUsage().setShowUpgradeModal(true)` (e.g. the
 * scan-limit gate in UsageContext.checkAndPromptUpgrade) continue to
 * work without needing their own state. All paywall UI lives in
 * PaywallModal — this file is just the glue.
 */
import { PaywallModal } from '@/components/PaywallModal'
import { useUsage } from '@/context/UsageContext'

export function UpgradeModal() {
  const { showUpgradeModal, setShowUpgradeModal } = useUsage()

  return (
    <PaywallModal
      open={showUpgradeModal}
      onClose={() => setShowUpgradeModal(false)}
      trigger="scan_limit"
    />
  )
}
