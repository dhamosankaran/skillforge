import { AlertTriangle } from 'lucide-react'
import type { PersonaVisibility } from '@/types'

interface ConfirmPersonaNarrowingModalProps {
  open: boolean
  onConfirm: () => void
  onCancel: () => void
  /** Personas removed from `decks.persona_visibility` by the pending PATCH. */
  removedPersonas: string[]
  /** The narrowed-to value being submitted (used to render the human-readable summary). */
  newVisibility?: PersonaVisibility
}

// Phase 6 slice 6.4b — D-19 (amended `de1e9a9`). Modal copy is locked
// verbatim per the spec §12 footnote — narrowing visibility refers to the
// persona-array delta, NOT a learner N count.
export function ConfirmPersonaNarrowingModal({
  open,
  onConfirm,
  onCancel,
  removedPersonas,
}: ConfirmPersonaNarrowingModalProps) {
  if (!open) return null

  const personaList = removedPersonas.join(', ')

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-persona-narrow-title"
      data-testid="confirm-persona-narrow-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
      onClick={onCancel}
    >
      <div
        className="bg-bg-elevated border border-contrast/[0.08] rounded-xl shadow-modal max-w-md w-full p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-3 mb-4">
          <AlertTriangle size={20} className="text-warning shrink-0 mt-0.5" />
          <h2
            id="confirm-persona-narrow-title"
            className="font-display text-lg font-semibold text-text-primary"
          >
            Narrow persona visibility?
          </h2>
        </div>

        <p
          className="text-sm text-text-secondary mb-6"
          data-testid="confirm-persona-narrow-copy"
        >
          Narrowing persona visibility will hide this deck from learners
          currently in personas {personaList}. Their existing FSRS progress on
          quiz_items in this deck is preserved but they will no longer see the
          deck in /learn surfaces. Continue?
        </p>

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 bg-bg-surface text-text-primary text-sm font-medium rounded-lg border border-contrast/[0.08] hover:bg-contrast/[0.04] transition-colors"
            data-testid="confirm-persona-narrow-cancel"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="px-4 py-2 bg-warning text-bg-base text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
            data-testid="confirm-persona-narrow-confirm"
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  )
}

/**
 * Compute the persona-array delta between current visibility and a proposed
 * new visibility value. Returns the list of personas being removed by the
 * change. Empty list → not a narrowing edit (no modal needed).
 */
export function computeRemovedPersonas(
  before: PersonaVisibility,
  after: PersonaVisibility,
): string[] {
  if (before === after) return []
  const personasOf = (v: PersonaVisibility): string[] =>
    v === 'both' ? ['climber', 'interview_prepper'] : [v]
  const beforeSet = new Set(personasOf(before))
  const afterSet = new Set(personasOf(after))
  return Array.from(beforeSet).filter((p) => !afterSet.has(p))
}
