import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ConfirmCascadeModal } from '@/components/admin/ConfirmCascadeModal'

describe('ConfirmCascadeModal (Phase 6 slice 6.4b)', () => {
  it('renders pre-PATCH copy with active quiz_item count and fires callbacks', () => {
    const onConfirm = vi.fn()
    const onCancel = vi.fn()
    render(
      <ConfirmCascadeModal
        open
        onConfirm={onConfirm}
        onCancel={onCancel}
        activeQuizItemCount={3}
      />,
    )

    expect(screen.getByTestId('confirm-cascade-modal')).toBeInTheDocument()
    expect(
      screen.getByText(/All 3 active quiz_items/i),
    ).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('confirm-cascade-confirm'))
    expect(onConfirm).toHaveBeenCalledOnce()

    fireEvent.click(screen.getByTestId('confirm-cascade-cancel'))
    expect(onCancel).toHaveBeenCalledOnce()
  })

  it('renders results-view copy when retiredCount is provided', () => {
    render(
      <ConfirmCascadeModal
        open
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        activeQuizItemCount={0}
        retiredCount={5}
      />,
    )
    expect(screen.getByTestId('confirm-cascade-results')).toHaveTextContent(
      /5 active quiz_items retired/,
    )
  })
})
