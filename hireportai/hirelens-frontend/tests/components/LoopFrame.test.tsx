/**
 * Spec #64 — static loop frame on /prep/results.
 *
 * Component is presentational. Consumer (Results.tsx) wires
 * data + plan; tests mount LoopFrame directly with prop values
 * so we can assert copy / state classes / analytics without
 * standing up AnalysisContext + useHomeState.
 */
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

import { LoopFrame } from '@/components/dashboard/LoopFrame'

beforeEach(() => {
  capture.mockReset()
})

function renderFrame(overrides: Partial<React.ComponentProps<typeof LoopFrame>> = {}) {
  return render(
    <LoopFrame
      surface="results"
      currentStep={1}
      score={71}
      gapCount={5}
      interviewDate={null}
      plan="free"
      {...overrides}
    />,
  )
}

describe('LoopFrame — spec #64', () => {
  it('renders the four step labels in DOM order', () => {
    renderFrame()
    const labels = ['Scanned', 'Studying', 'Re-scan', 'Interview']
    for (const label of labels) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
    // DOM order assertion: each label appears before the next.
    const positions = labels.map((label) => screen.getByText(label).compareDocumentPosition.bind(
      screen.getByText(label),
    ))
    for (let i = 0; i < labels.length - 1; i++) {
      const earlier = screen.getByText(labels[i])
      const later = screen.getByText(labels[i + 1])
      const mask = earlier.compareDocumentPosition(later)
      expect((mask & Node.DOCUMENT_POSITION_FOLLOWING) !== 0).toBe(true)
    }
  })

  it('marks the current step with data-current=true and others false', () => {
    renderFrame({ currentStep: 1 })
    expect(screen.getByTestId('loop-step-1').getAttribute('data-current')).toBe('true')
    expect(screen.getByTestId('loop-step-2').getAttribute('data-current')).toBe('false')
    expect(screen.getByTestId('loop-step-3').getAttribute('data-current')).toBe('false')
    expect(screen.getByTestId('loop-step-4').getAttribute('data-current')).toBe('false')
  })

  it('displays the score on step 1 when provided', () => {
    renderFrame({ score: 71 })
    const step1 = screen.getByTestId('loop-step-1')
    expect(step1.textContent).toContain('71%')
  })

  it('displays the gap count on step 2 when provided', () => {
    renderFrame({ gapCount: 5 })
    const step2 = screen.getByTestId('loop-step-2')
    expect(step2.textContent).toContain('5 gaps')
  })

  it('renders "Set a date" on step 4 when interviewDate is null', () => {
    renderFrame({ interviewDate: null })
    const step4 = screen.getByTestId('loop-step-4')
    expect(step4.textContent).toContain('Set a date')
    expect(step4.textContent).not.toMatch(/\d+d/)
  })

  it('renders the day countdown on step 4 when interviewDate is provided', () => {
    // Pick a date 7 days in the future relative to "today".
    const future = new Date()
    future.setDate(future.getDate() + 7)
    const iso = future.toISOString().slice(0, 10)
    renderFrame({ interviewDate: iso })
    const step4 = screen.getByTestId('loop-step-4')
    expect(step4.textContent).toMatch(/in 7d/)
    expect(step4.textContent).not.toContain('Set a date')
  })

  it('fires loop_frame_rendered exactly once on mount with the contract payload', () => {
    renderFrame({
      currentStep: 1,
      interviewDate: '2099-01-01',
      plan: 'free',
    })
    const matching = capture.mock.calls.filter(([name]) => name === 'loop_frame_rendered')
    expect(matching).toHaveLength(1)
    expect(matching[0][1]).toEqual({
      surface: 'results',
      current_step: 1,
      has_interview_date: true,
      plan: 'free',
    })
  })

  it('payload reflects has_interview_date=false when no date passed', () => {
    renderFrame({ interviewDate: null, plan: 'pro' })
    const matching = capture.mock.calls.filter(([name]) => name === 'loop_frame_rendered')
    expect(matching).toHaveLength(1)
    expect(matching[0][1]).toMatchObject({
      surface: 'results',
      current_step: 1,
      has_interview_date: false,
      plan: 'pro',
    })
  })

  it('uses no inline color styles (R12 design-tokens compliance)', () => {
    const { container } = renderFrame()
    const inlineStyled = Array.from(container.querySelectorAll('[style]')).filter((el) => {
      const style = (el as HTMLElement).style
      return style.color || style.backgroundColor || style.borderColor
    })
    expect(inlineStyled).toHaveLength(0)
  })

  // ── Spec #66 §4.1 extensions — stepStates / onStepClick / compact ──────────

  it('§66: stepStates overrides linear currentStep derivation', () => {
    renderFrame({
      currentStep: 1,
      stepStates: { 1: 'done', 2: 'current', 3: 'locked', 4: 'alert' },
    })
    expect(screen.getByTestId('loop-step-1')).toHaveAttribute('data-state', 'done')
    expect(screen.getByTestId('loop-step-2')).toHaveAttribute('data-state', 'current')
    expect(screen.getByTestId('loop-step-3')).toHaveAttribute('data-state', 'locked')
    expect(screen.getByTestId('loop-step-4')).toHaveAttribute('data-state', 'alert')
  })

  it('§66: onStepClick renders current step as button + fires handler', async () => {
    const onClick = vi.fn()
    renderFrame({
      stepStates: { 3: 'current' },
      onStepClick: onClick,
    })
    const step3 = screen.getByTestId('loop-step-3')
    expect(step3.tagName).toBe('BUTTON')
    step3.click()
    expect(onClick).toHaveBeenCalledWith(3)
  })

  it('§66: surface=appshell suppresses loop_frame_rendered (D-4)', () => {
    renderFrame({ surface: 'appshell' })
    const matching = capture.mock.calls.filter(([name]) => name === 'loop_frame_rendered')
    expect(matching).toHaveLength(0)
  })
})
