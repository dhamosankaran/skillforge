import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { LayoutGrid, Plus, X } from 'lucide-react'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { GlowButton } from '@/components/ui/GlowButton'
import { KanbanBoard } from '@/components/tracker/KanbanBoard'
import { useTracker } from '@/hooks/useTracker'
import type { ApplicationStatus } from '@/types'

export default function Tracker() {
  const { applications, isLoading, add, remove, moveStatus } = useTracker()
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    company: '',
    role: '',
    date_applied: new Date().toISOString().slice(0, 10),
    ats_score: 0,
    status: 'Applied' as ApplicationStatus,
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.company.trim() || !formData.role.trim()) return
    setIsSubmitting(true)
    try {
      await add(formData)
      setFormData({
        company: '',
        role: '',
        date_applied: new Date().toISOString().slice(0, 10),
        ats_score: 0,
        status: 'Applied',
      })
      setShowForm(false)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div className="max-w-7xl mx-auto px-4 py-10">
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
