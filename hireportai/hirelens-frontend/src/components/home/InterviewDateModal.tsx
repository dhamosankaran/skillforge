import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Calendar, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '@/context/AuthContext'
import { updatePersona } from '@/services/api'
import { capture } from '@/utils/posthog'

interface InterviewDateModalProps {
  open: boolean
  onClose: () => void
  /** Surface property for the existing `interview_target_date_added`
   * PostHog event (spec #53 catalog). The home Countdown widget uses
   * `'home_countdown'`; reserved for future surfaces that mount this
   * modal too. */
  surface: 'home_countdown'
}

export function InterviewDateModal({ open, onClose, surface }: InterviewDateModalProps) {
  const { user, updateUser } = useAuth()
  const [date, setDate] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open) setDate('')
  }, [open])

  async function handleSave() {
    if (!date || submitting || !user || !user.persona) return
    setSubmitting(true)
    try {
      // PATCH /users/me/persona is currently a full-replace endpoint, not
      // partial-update. We MUST send persona + company alongside the new
      // date or we'll null them. See B-038 (filed) for the proper fix —
      // a partial-update endpoint or a dedicated date-only route.
      const updated = await updatePersona({
        persona: user.persona,
        interview_target_date: date,
        interview_target_company: user.interview_target_company ?? null,
      })
      updateUser(updated)
      capture('interview_target_date_added', {
        source: 'persona_edit',
        surface,
      })
      onClose()
    } catch (err) {
      console.error('updatePersona failed', err)
      toast.error('Could not save your interview date. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={submitting ? undefined : onClose}
            className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
            className="fixed inset-0 z-[101] flex items-center justify-center p-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby="interview-date-modal-title"
            data-testid="interview-date-modal"
          >
            <div className="relative w-full max-w-md bg-bg-surface border border-contrast/[0.08] rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.5)] overflow-hidden">
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-40 h-px bg-gradient-to-r from-transparent via-accent-primary/50 to-transparent" />
              <button
                onClick={onClose}
                disabled={submitting}
                className="absolute top-4 right-4 p-1.5 rounded-lg text-text-muted hover:text-text-secondary hover:bg-contrast/[0.04] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                aria-label="Close"
              >
                <X size={16} />
              </button>
              <div className="p-8">
                <div className="w-14 h-14 rounded-2xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center mx-auto mb-5">
                  <Calendar size={24} className="text-accent-primary" />
                </div>
                <h2
                  id="interview-date-modal-title"
                  className="font-display text-xl font-bold text-text-primary mb-2 text-center"
                >
                  Add your interview date
                </h2>
                <p className="text-sm text-text-secondary leading-relaxed mb-6 max-w-sm mx-auto text-center">
                  Set your target date for a personalized countdown on your home dashboard.
                </p>
                <label className="block text-[11px] uppercase tracking-widest text-text-muted font-semibold mb-2">
                  Interview Date
                </label>
                <input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  data-testid="interview-date-input"
                  className="w-full px-4 py-2.5 rounded-xl bg-bg-elevated border border-contrast/[0.08] text-sm text-text-primary focus:outline-none focus:border-accent-primary/40 transition-colors mb-6"
                />
                <div className="flex flex-col gap-3">
                  <button
                    onClick={handleSave}
                    disabled={submitting || !date}
                    data-testid="interview-date-save"
                    className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-accent-primary text-bg-base text-sm font-semibold hover:bg-accent-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {submitting ? (
                      <>
                        <Loader2 size={14} className="animate-spin" />
                        Saving…
                      </>
                    ) : (
                      'Save'
                    )}
                  </button>
                  <button
                    onClick={onClose}
                    disabled={submitting}
                    className="w-full py-2 text-sm text-text-muted hover:text-text-secondary transition-colors disabled:opacity-40"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
