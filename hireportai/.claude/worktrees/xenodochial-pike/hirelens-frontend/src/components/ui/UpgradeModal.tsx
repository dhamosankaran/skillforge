import { motion, AnimatePresence } from 'framer-motion'
import { X, Sparkles, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useUsage } from '@/context/UsageContext'

export function UpgradeModal() {
  const { showUpgradeModal, setShowUpgradeModal } = useUsage()

  return (
    <AnimatePresence>
      {showUpgradeModal && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowUpgradeModal(false)}
            className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
            className="fixed inset-0 z-[101] flex items-center justify-center p-4"
          >
            <div className="relative w-full max-w-md bg-bg-surface border border-white/[0.08] rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.5)] overflow-hidden">
              {/* Glow accent */}
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-40 h-px bg-gradient-to-r from-transparent via-accent-primary/50 to-transparent" />

              {/* Close */}
              <button
                onClick={() => setShowUpgradeModal(false)}
                className="absolute top-4 right-4 p-1.5 rounded-lg text-text-muted hover:text-text-secondary hover:bg-white/[0.04] transition-colors"
                aria-label="Close modal"
              >
                <X size={16} />
              </button>

              <div className="p-8 text-center">
                {/* Icon */}
                <div className="w-14 h-14 rounded-2xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center mx-auto mb-5">
                  <Sparkles size={24} className="text-accent-primary" />
                </div>

                {/* Title */}
                <h2 className="font-display text-xl font-bold text-text-primary mb-2">
                  Free scans used up
                </h2>
                <p className="text-sm text-text-secondary leading-relaxed mb-8 max-w-sm mx-auto">
                  You&apos;ve used your 3 free resume scans. Upgrade to Pro for unlimited ATS scans and full analytics.
                </p>

                {/* Actions */}
                <div className="flex flex-col gap-3">
                  <Link
                    to="/pricing"
                    onClick={() => setShowUpgradeModal(false)}
                    className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-accent-primary text-bg-base text-sm font-semibold hover:bg-accent-primary/90 transition-colors shadow-[0_0_20px_rgba(0,255,200,0.15)]"
                  >
                    Upgrade to Pro
                    <ArrowRight size={14} />
                  </Link>
                  <Link
                    to="/pricing"
                    onClick={() => setShowUpgradeModal(false)}
                    className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-text-secondary text-sm font-medium hover:bg-white/[0.06] transition-colors"
                  >
                    View Pricing
                  </Link>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
