/**
 * MissionSetup — form to create a new mission.
 *
 * User selects categories, picks a target date, enters a title,
 * and submits. Validates:
 *  - At least one category selected
 *  - Target date is in the future
 *  - Title is non-empty
 */
import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Target, Calendar, CheckCircle } from 'lucide-react'
import clsx from 'clsx'
import { GlowButton } from '@/components/ui/GlowButton'
import type { Category, MissionCreateRequest } from '@/types'

interface MissionSetupProps {
  categories: Category[]
  onCreate: (req: MissionCreateRequest) => Promise<unknown>
}

export function MissionSetup({ categories, onCreate }: MissionSetupProps) {
  const [title, setTitle] = useState('')
  const [targetDate, setTargetDate] = useState('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const minDate = useMemo(() => {
    const tomorrow = new Date()
    tomorrow.setDate(tomorrow.getDate() + 1)
    return tomorrow.toISOString().split('T')[0]
  }, [])

  function toggleCategory(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (!title.trim()) {
      setError('Give your mission a name')
      return
    }
    if (selectedIds.size === 0) {
      setError('Select at least one category')
      return
    }
    if (!targetDate) {
      setError('Pick a target date')
      return
    }

    setIsSubmitting(true)
    try {
      await onCreate({
        title: title.trim(),
        target_date: targetDate,
        category_ids: Array.from(selectedIds),
      })
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      setError(detail || 'Failed to create mission')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="max-w-lg mx-auto"
    >
      {/* Header */}
      <div className="text-center mb-8">
        <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center">
          <Target size={24} className="text-accent-primary" />
        </div>
        <h2 className="font-display text-2xl font-bold text-text-primary mb-2">
          Start a Mission
        </h2>
        <p className="text-sm text-text-secondary max-w-xs mx-auto leading-relaxed">
          Set a deadline and pick categories. We'll pace your study with daily targets.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Title */}
        <div>
          <label className="block text-[11px] uppercase tracking-widest text-text-muted font-semibold mb-2">
            Mission Name
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Google SDE-2 Prep"
            maxLength={200}
            className="w-full px-4 py-2.5 rounded-xl bg-bg-elevated border border-white/[0.08] text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-primary/40 transition-colors"
          />
        </div>

        {/* Target date */}
        <div>
          <label className="block text-[11px] uppercase tracking-widest text-text-muted font-semibold mb-2">
            <Calendar size={11} className="inline mr-1.5 -mt-0.5" />
            Target Date
          </label>
          <input
            type="date"
            value={targetDate}
            onChange={(e) => setTargetDate(e.target.value)}
            min={minDate}
            className="w-full px-4 py-2.5 rounded-xl bg-bg-elevated border border-white/[0.08] text-sm text-text-primary focus:outline-none focus:border-accent-primary/40 transition-colors"
          />
        </div>

        {/* Category picker */}
        <div>
          <label className="block text-[11px] uppercase tracking-widest text-text-muted font-semibold mb-3">
            Categories
          </label>
          <div className="grid grid-cols-2 gap-2">
            {categories.map((cat, i) => {
              const selected = selectedIds.has(cat.id)
              return (
                <motion.button
                  key={cat.id}
                  type="button"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04, duration: 0.3 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={() => toggleCategory(cat.id)}
                  className={clsx(
                    'flex items-center gap-2.5 px-3.5 py-3 rounded-xl border text-left transition-all duration-150',
                    selected
                      ? 'bg-accent-primary/10 border-accent-primary/30 text-text-primary'
                      : 'bg-bg-surface/50 border-white/[0.06] text-text-secondary hover:border-white/[0.12]'
                  )}
                >
                  <span className="text-base">{cat.icon}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium truncate">{cat.name}</p>
                    <p className="text-[10px] text-text-muted">
                      {cat.card_count} card{cat.card_count !== 1 ? 's' : ''}
                    </p>
                  </div>
                  {selected && (
                    <CheckCircle size={14} className="text-accent-primary shrink-0" />
                  )}
                </motion.button>
              )
            })}
          </div>
        </div>

        {/* Error */}
        {error && (
          <motion.p
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-xs text-red-400 text-center"
          >
            {error}
          </motion.p>
        )}

        {/* Submit */}
        <GlowButton
          type="submit"
          size="lg"
          isLoading={isSubmitting}
          disabled={isSubmitting}
          className="w-full"
        >
          <Target size={14} />
          Launch Mission
        </GlowButton>
      </form>
    </motion.div>
  )
}
