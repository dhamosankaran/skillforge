/**
 * FlipCard — 3-D flip card with a question front and arbitrary back content.
 *
 * Implementation notes:
 * - A fixed `perspective` wrapper creates the 3D stage.
 * - Two absolutely-positioned faces share the same grid cell.
 * - Each face has `backfaceVisibility: 'hidden'` so only the facing side renders.
 * - The back face starts pre-rotated 180° and animates to 0° when flipped.
 * - Framer Motion drives the rotateY values so the spring physics match the
 *   rest of the app's animation language.
 */
import { type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { RotateCcw } from 'lucide-react'
import clsx from 'clsx'

interface FlipCardProps {
  question: string
  isFlipped: boolean
  onFlip: () => void
  backContent: ReactNode
  /** Optional Tailwind gradient classes for the front accent bar */
  accentColor?: string
}

const SPRING = { type: 'spring' as const, stiffness: 260, damping: 28 }

export function FlipCard({
  question,
  isFlipped,
  onFlip,
  backContent,
  accentColor = 'from-accent-primary to-accent-secondary',
}: FlipCardProps) {
  return (
    /* 3D stage — perspective must be on the *parent*, not the rotating element */
    <div style={{ perspective: '1200px' }} className="w-full" data-tour="flip-card">
      <div className="relative w-full" style={{ minHeight: '420px' }}>

        {/* ── Front face ─────────────────────────────────────────────── */}
        <motion.div
          animate={{ rotateY: isFlipped ? -180 : 0 }}
          transition={SPRING}
          style={{ backfaceVisibility: 'hidden', transformStyle: 'preserve-3d' }}
          className={clsx(
            'absolute inset-0 flex flex-col rounded-2xl border border-white/[0.07]',
            'bg-bg-surface/70 overflow-hidden',
            !isFlipped && 'cursor-pointer'
          )}
          onClick={!isFlipped ? onFlip : undefined}
          role={!isFlipped ? 'button' : undefined}
          aria-label={!isFlipped ? 'Flip card to reveal answer' : undefined}
        >
          {/* Top accent bar */}
          <div className={`h-1 w-full bg-gradient-to-r ${accentColor}`} />

          {/* Question */}
          <div className="flex-1 flex flex-col items-center justify-center px-8 py-10 text-center">
            <p className="text-[11px] uppercase tracking-widest font-semibold text-text-muted mb-6 font-body">
              Question
            </p>
            <p className="font-display text-xl sm:text-2xl font-semibold text-text-primary leading-relaxed">
              {question}
            </p>
          </div>

          {/* Flip hint */}
          <div className="flex justify-center pb-6">
            <span className="flex items-center gap-1.5 text-xs text-text-muted">
              <RotateCcw size={12} />
              Click to flip
            </span>
          </div>
        </motion.div>

        {/* ── Back face ──────────────────────────────────────────────── */}
        <motion.div
          animate={{ rotateY: isFlipped ? 0 : 180 }}
          transition={SPRING}
          style={{ backfaceVisibility: 'hidden', transformStyle: 'preserve-3d' }}
          className={clsx(
            'absolute inset-0 flex flex-col rounded-2xl border border-white/[0.07]',
            'bg-bg-surface/70 overflow-hidden'
          )}
        >
          {/* Top accent bar */}
          <div className={`h-1 w-full bg-gradient-to-r ${accentColor}`} />

          {/* Back content (tabs + body injected from parent) */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {backContent}
          </div>

          {/* Flip back */}
          <div className="flex justify-center pb-4 shrink-0">
            <button
              onClick={onFlip}
              className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors"
            >
              <RotateCcw size={12} />
              Flip back
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
