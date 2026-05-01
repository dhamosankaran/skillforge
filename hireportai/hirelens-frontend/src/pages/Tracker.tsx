import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { LayoutGrid, Plus, X } from 'lucide-react'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { GlowButton } from '@/components/ui/GlowButton'
import { KanbanBoard } from '@/components/tracker/KanbanBoard'
import { ScoreDeltaWidget } from '@/components/tracker/ScoreDeltaWidget'
import { useTracker } from '@/hooks/useTracker'
import { capture } from '@/utils/posthog'
import type { ApplicationStatus } from '@/types'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function maxDateIso(): string {
  // Spec #57 AC-2 / AC-3: interview_date must be ≤ today + 365 days.
  const d = new Date()
  d.setDate(d.getDate() + 365)
  return d.toISOString().slice(0, 10)
}

export default function Tracker() {
  const { applications, isLoading, add, update, remove, moveStatus } = useTracker()
  const [searchParams, setSearchParams] = useSearchParams()
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    company: '',
    role: '',
    date_applied: todayIso(),
    ats_score: 0,
    status: 'Applied' as ApplicationStatus,
    interview_date: '' as string,
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  // Spec #57 §6.3 — `?new=1` opens the create form; `?focus={tracker_id}`
  // requests an inline edit affordance for that row.
  const newParam = searchParams.get('new')
  const focusId = searchParams.get('focus')
  const [focusEditId, setFocusEditId] = useState<string | null>(focusId)
  const handledNewRef = useRef(false)

  useEffect(() => {
    if (newParam !== '1' || handledNewRef.current) return
    handledNewRef.current = true
    setShowForm(true)
    // Strip the param so a refresh / back-nav doesn't re-trigger the form.
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.delete('new')
      return next
    }, { replace: true })
  }, [newParam, setSearchParams])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.company.trim() || !formData.role.trim()) return
    setIsSubmitting(true)
    try {
      const payload = {
        company: formData.company,
        role: formData.role,
        date_applied: formData.date_applied,
        ats_score: formData.ats_score,
        status: formData.status,
        ...(formData.interview_date
          ? { interview_date: formData.interview_date }
          : {}),
      }
      const created = await add(payload)
      if (formData.interview_date) {
        capture('tracker_interview_date_set', {
          tracker_id: created.id,
          days_until: Math.max(
            0,
            Math.ceil(
              (new Date(`${formData.interview_date}T00:00:00`).getTime() -
                new Date(new Date().setHours(0, 0, 0, 0)).getTime()) /
                86_400_000,
            ),
          ),
          source: 'create',
        })
      }
      setFormData({
        company: '',
        role: '',
        date_applied: todayIso(),
        ats_score: 0,
        status: 'Applied',
        interview_date: '',
      })
      setShowForm(false)
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleFocusedDateChange(trackerId: string, value: string) {
    const newValue = value || null
    const before = applications.find((a) => a.id === trackerId)
    const previous = before?.interview_date ?? null
    if (previous === newValue) return
    const updated = await update(trackerId, { interview_date: newValue })
    if (newValue == null) {
      capture('tracker_interview_date_cleared', { tracker_id: trackerId })
    } else {
      capture('tracker_interview_date_set', {
        tracker_id: trackerId,
        days_until: Math.max(
          0,
          Math.ceil(
            (new Date(`${newValue}T00:00:00`).getTime() -
              new Date(new Date().setHours(0, 0, 0, 0)).getTime()) /
              86_400_000,
          ),
        ),
        source: 'edit',
      })
    }
    return updated
  }

  // Resolve `focus={tracker_id}` once data lands — if the row was deleted
  // between navigation and load, drop the focus state silently. Spec #57
  // §6.3 toast intentionally not shown to keep this surgical; future
  // polish can wire it.
  useEffect(() => {
    if (!focusEditId) return
    if (isLoading) return
    if (!applications.some((a) => a.id === focusEditId)) {
      setFocusEditId(null)
    }
  }, [focusEditId, isLoading, applications])

  const focusedRow = focusEditId
    ? applications.find((a) => a.id === focusEditId) ?? null
    : null

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div data-testid="page-tracker" className="max-w-7xl mx-auto px-4 py-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8"
        >
          <div>
            <h1 className="font-display text-3xl font-bold text-text-primary">
              Application <span className="text-accent-primary">Tracker</span>
            </h1>
            <p className="text-text-secondary text-sm mt-1">
              Track your job applications and their status.
            </p>
          </div>
          <GlowButton size="sm" onClick={() => setShowForm(!showForm)}>
            {showForm ? <X size={13} /> : <Plus size={13} />}
            {showForm ? 'Cancel' : 'Add Application'}
          </GlowButton>
        </motion.div>

        {/* Focused row interview-date editor (spec #57 §6.3 ?focus={id}) */}
        {focusedRow && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-5 bg-bg-surface border border-accent-primary/20 rounded-xl"
            data-testid="tracker-focused-editor"
          >
            <div className="flex flex-col sm:flex-row sm:items-end gap-4">
              <div className="flex-1">
                <p className="text-[11px] uppercase tracking-widest text-text-muted font-semibold mb-1">
                  Interview Date
                </p>
                <p className="text-sm text-text-secondary">
                  {focusedRow.company} — {focusedRow.role}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="date"
                  data-testid="tracker-focused-date-input"
                  min={todayIso()}
                  max={maxDateIso()}
                  value={focusedRow.interview_date ?? ''}
                  onChange={(e) =>
                    handleFocusedDateChange(focusedRow.id, e.target.value)
                  }
                  className="px-3 py-2 rounded-md border border-border bg-bg-base text-sm text-text-primary focus:outline-none focus:border-border-accent"
                />
                <button
                  type="button"
                  data-testid="tracker-focused-close"
                  onClick={() => setFocusEditId(null)}
                  className="text-xs text-text-muted hover:text-text-secondary"
                >
                  Done
                </button>
              </div>
            </div>
            {/* Spec #63 (E-043) §8.6 — score-delta inline-expand mount per D-4. */}
            <div className="mt-5">
              <ScoreDeltaWidget trackerApplicationId={focusedRow.id} />
            </div>
          </motion.div>
        )}

        {/* Add form */}
        <AnimatePresence>
          {showForm && (
            <motion.form
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              onSubmit={handleSubmit}
              className="mb-8 p-6 bg-bg-surface border border-contrast/[0.06] rounded-xl overflow-hidden"
            >
              <h3 className="font-display font-semibold text-text-primary mb-4">
                New Application
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs text-text-muted mb-1.5">Company</label>
                  <input
                    type="text"
                    value={formData.company}
                    onChange={(e) => setFormData((p) => ({ ...p, company: e.target.value }))}
                    className="w-full px-3 py-2.5 bg-bg-elevated border border-contrast/[0.06] rounded-lg text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-primary/30 transition-colors"
                    placeholder="e.g. Google"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs text-text-muted mb-1.5">Role</label>
                  <input
                    type="text"
                    value={formData.role}
                    onChange={(e) => setFormData((p) => ({ ...p, role: e.target.value }))}
                    className="w-full px-3 py-2.5 bg-bg-elevated border border-contrast/[0.06] rounded-lg text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-primary/30 transition-colors"
                    placeholder="e.g. Senior SWE"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs text-text-muted mb-1.5">Date Applied</label>
                  <input
                    type="date"
                    value={formData.date_applied}
                    onChange={(e) => setFormData((p) => ({ ...p, date_applied: e.target.value }))}
                    className="w-full px-3 py-2.5 bg-bg-elevated border border-contrast/[0.06] rounded-lg text-sm text-text-primary focus:outline-none focus:border-accent-primary/30 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs text-text-muted mb-1.5">ATS Score</label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={formData.ats_score}
                    onChange={(e) => setFormData((p) => ({ ...p, ats_score: parseInt(e.target.value) || 0 }))}
                    className="w-full px-3 py-2.5 bg-bg-elevated border border-contrast/[0.06] rounded-lg text-sm text-text-primary focus:outline-none focus:border-accent-primary/30 transition-colors"
                  />
                </div>
                <div className="sm:col-span-2 lg:col-span-2">
                  <label className="block text-xs text-text-muted mb-1.5">
                    Interview Date
                  </label>
                  <input
                    type="date"
                    data-testid="tracker-form-interview-date"
                    min={todayIso()}
                    max={maxDateIso()}
                    value={formData.interview_date}
                    onChange={(e) =>
                      setFormData((p) => ({ ...p, interview_date: e.target.value }))
                    }
                    className="w-full px-3 py-2.5 bg-bg-elevated border border-contrast/[0.06] rounded-lg text-sm text-text-primary focus:outline-none focus:border-accent-primary/30 transition-colors"
                  />
                  <p className="mt-1 text-xs text-text-muted">
                    Optional — add when the interview is scheduled.
                  </p>
                </div>
              </div>
              <div className="flex justify-end mt-4">
                <GlowButton type="submit" size="sm" isLoading={isSubmitting}>
                  Save Application
                </GlowButton>
              </div>
            </motion.form>
          )}
        </AnimatePresence>

        {/* Loading state */}
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="space-y-3">
                <div className="h-5 w-24 rounded-full bg-bg-elevated animate-pulse" />
                {[...Array(3)].map((__, j) => (
                  <div key={j} className="rounded-xl border border-contrast/[0.04] bg-bg-surface/40 p-4 space-y-2.5 animate-pulse">
                    <div className="h-4 w-3/4 rounded-full bg-bg-elevated" />
                    <div className="h-3 w-1/2 rounded-full bg-bg-elevated" />
                    <div className="h-3 w-1/3 rounded-full bg-bg-elevated" />
                  </div>
                ))}
              </div>
            ))}
          </div>
        ) : applications.length === 0 && !showForm ? (
          /* Empty state */
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center py-24 text-center"
          >
            <LayoutGrid size={48} className="text-text-muted mb-4" />
            <h2 className="font-display text-2xl font-bold mb-2 text-text-primary">
              No Applications Yet
            </h2>
            <p className="text-text-secondary mb-8 max-w-md">
              Start tracking your job applications. Add your first application to see it on the board.
            </p>
            <GlowButton onClick={() => setShowForm(true)}>
              <Plus size={14} />
              Add First Application
            </GlowButton>
          </motion.div>
        ) : (
          /* Kanban Board */
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <KanbanBoard
              applications={applications}
              onMoveStatus={moveStatus}
              onDelete={remove}
            />
          </motion.div>
        )}
      </div>
    </PageWrapper>
  )
}
