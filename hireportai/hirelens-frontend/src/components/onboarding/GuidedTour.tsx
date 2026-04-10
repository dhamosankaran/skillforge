import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ChevronRight } from 'lucide-react'
import { capture } from '@/utils/posthog'

export interface TourStep {
  /** CSS selector for the element to highlight. */
  target: string
  /** Tooltip message. */
  message: string
}

const DEFAULT_STEPS: TourStep[] = [
  {
    target: '[data-tour="category-grid"]',
    message: 'This is your study dashboard — pick a category to start.',
  },
  {
    target: '[data-tour="flip-card"]',
    message: 'Flip cards to learn, then test yourself with the quiz.',
  },
  {
    target: '[data-tour="daily-review"]',
    message: 'Your Daily 5 uses spaced repetition — come back tomorrow for the best results.',
  },
  {
    target: '[data-tour="streak-badge"]',
    message: 'Track your progress here.',
  },
]

interface Props {
  steps?: TourStep[]
  onComplete: () => void
}

export default function GuidedTour({ steps = DEFAULT_STEPS, onComplete }: Props) {
  const [currentStep, setCurrentStep] = useState(0)
  const [position, setPosition] = useState<{ top: number; left: number; width: number; height: number } | null>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)

  const step = steps[currentStep]
  const isLast = currentStep === steps.length - 1

  const measureTarget = useCallback(() => {
    if (!step) return
    const el = document.querySelector(step.target)
    if (el) {
      const rect = el.getBoundingClientRect()
      setPosition({ top: rect.top, left: rect.left, width: rect.width, height: rect.height })
    } else {
      setPosition(null)
    }
  }, [step])

  useEffect(() => {
    measureTarget()
    window.addEventListener('resize', measureTarget)
    window.addEventListener('scroll', measureTarget, true)
    return () => {
      window.removeEventListener('resize', measureTarget)
      window.removeEventListener('scroll', measureTarget, true)
    }
  }, [measureTarget])

  function handleNext() {
    if (isLast) {
      capture('onboarding_tour_completed')
      onComplete()
    } else {
      setCurrentStep((s) => s + 1)
    }
  }

  function handleSkip() {
    capture('onboarding_tour_skipped')
    onComplete()
  }

  // Compute tooltip position: prefer below the target, fall back to above
  const tooltipStyle = (() => {
    if (!position) {
      // No target found — center on screen
      return {
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
      } as const
    }
    const below = position.top + position.height + 12
    const centerX = position.left + position.width / 2
    return {
      top: below,
      left: Math.max(16, Math.min(centerX - 160, window.innerWidth - 336)),
    } as const
  })()

  return (
    <>
      {/* Overlay */}
      <div
        onClick={handleNext}
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 300,
          background: 'rgba(0,0,0,0.6)',
          cursor: 'pointer',
        }}
      />

      {/* Highlight cutout */}
      {position && (
        <div
          style={{
            position: 'fixed',
            top: position.top - 4,
            left: position.left - 4,
            width: position.width + 8,
            height: position.height + 8,
            borderRadius: 8,
            border: '2px solid var(--sf-accent-primary)',
            boxShadow: '0 0 0 9999px rgba(0,0,0,0.6)',
            zIndex: 301,
            pointerEvents: 'none',
          }}
        />
      )}

      {/* Tooltip */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep}
          ref={tooltipRef}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
          style={{
            position: 'fixed',
            ...tooltipStyle,
            zIndex: 302,
            width: 320,
            padding: '16px 18px',
            borderRadius: 'var(--sf-radius-lg)',
            background: 'var(--sf-bg-tertiary)',
            border: '1px solid var(--sf-border-subtle)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
            <p style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--sf-text-primary)', margin: 0 }}>
              {step?.message}
            </p>
            <button
              onClick={handleSkip}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--sf-text-tertiary)',
                cursor: 'pointer',
                padding: 2,
                flexShrink: 0,
              }}
              aria-label="Skip tour"
            >
              <X size={16} />
            </button>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 14 }}>
            <span style={{ fontSize: 12, color: 'var(--sf-text-tertiary)' }}>
              {currentStep + 1} / {steps.length}
            </span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={handleSkip}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--sf-text-secondary)',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontWeight: 500,
                  padding: '4px 8px',
                  fontFamily: 'inherit',
                }}
              >
                Skip tour
              </button>
              <button
                onClick={handleNext}
                className="sf-btn-primary"
                style={{
                  padding: '6px 14px',
                  fontSize: 13,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                {isLast ? 'Done' : 'Next'}
                {!isLast && <ChevronRight size={14} />}
              </button>
            </div>
          </div>
        </motion.div>
      </AnimatePresence>
    </>
  )
}
