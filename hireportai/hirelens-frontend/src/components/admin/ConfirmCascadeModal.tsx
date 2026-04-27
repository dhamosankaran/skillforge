import { AlertTriangle } from 'lucide-react'

interface ConfirmCascadeModalProps {
  open: boolean
  onConfirm: () => void
  onCancel: () => void
  /** Number of active quiz_items that would be retired by this substantive edit. */
  activeQuizItemCount: number
  /** Optional: post-PATCH results count when the modal is reused as the result surface. */
  retiredCount?: number
}

// Phase 6 slice 6.4b — fires before a substantive lesson PATCH to warn the
// admin that all active quiz_items on the lesson will be retired in the same
// DB transaction. Admin confirms → PATCH fires → BE returns
// LessonUpdateResponse.quiz_items_retired_count for the post-hoc results
// surface.
export function ConfirmCascadeModal({
  open,
  onConfirm,
  onCancel,
  activeQuizItemCount,
  retiredCount,
}: ConfirmCascadeModalProps) {
  if (!open) return null

  const isResultsView = retiredCount !== undefined

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-cascade-title"
      data-testid="confirm-cascade-modal"
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
            id="confirm-cascade-title"
            className="font-display text-lg font-semibold text-text-primary"
          >
            {isResultsView
              ? 'Substantive edit applied'
              : 'Substantive edit will retire quiz items'}
          </h2>
        </div>

        <div className="text-sm text-text-secondary space-y-3 mb-6">
          {isResultsView ? (
            <p data-testid="confirm-cascade-results">
              {retiredCount} active quiz_item{retiredCount === 1 ? '' : 's'}{' '}
              retired in the same transaction. Existing FSRS progress on those
              items is preserved per the slice 6.1 §4.3 retirement semantic.
            </p>
          ) : (
            <>
              <p>
                You are about to make a <strong>substantive</strong> edit to
                this lesson. All {activeQuizItemCount} active quiz_item
                {activeQuizItemCount === 1 ? '' : 's'} on this lesson will be
                retired in the same database transaction.
              </p>
              <p>
                Existing learner FSRS progress on those quiz_items is preserved
                (rows are kept; only `retired_at` is set). After save, you will
                need to author replacement quiz_items manually.
              </p>
              <p className="text-text-muted">
                A minor edit instead? Cancel and toggle the classification —
                the server will reject classification mismatches.
              </p>
            </>
          )}
        </div>

        <div className="flex justify-end gap-2">
          {isResultsView ? (
            <button
              type="button"
              onClick={onConfirm}
              className="px-4 py-2 bg-accent-primary text-bg-base text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
              data-testid="confirm-cascade-dismiss"
            >
              Got it
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2 bg-bg-surface text-text-primary text-sm font-medium rounded-lg border border-contrast/[0.08] hover:bg-contrast/[0.04] transition-colors"
                data-testid="confirm-cascade-cancel"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={onConfirm}
                className="px-4 py-2 bg-warning text-bg-base text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
                data-testid="confirm-cascade-confirm"
              >
                Confirm substantive edit
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
