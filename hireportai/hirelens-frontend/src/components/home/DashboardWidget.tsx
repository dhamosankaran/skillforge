import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { AnimatedCard } from '@/components/ui/AnimatedCard'
import { SkeletonCard } from '@/components/ui/SkeletonLoader'
import type { Persona } from '@/context/AuthContext'

export type WidgetState = 'loading' | 'data' | 'empty' | 'error'

export interface DashboardWidgetAction {
  label: string
  href?: string
  onClick?: () => void
}

export interface DashboardWidgetProps {
  title: string
  testid: string
  persona: Persona
  state: WidgetState
  emptyMessage?: string
  errorMessage?: string
  onRetry?: () => void
  action?: DashboardWidgetAction
  children?: ReactNode
}

export function DashboardWidget({
  title,
  testid,
  persona: _persona,
  state,
  emptyMessage,
  errorMessage,
  onRetry,
  action,
  children,
}: DashboardWidgetProps) {
  if (state === 'loading') {
    return (
      <div data-testid={`widget-${testid}`}>
        <SkeletonCard lines={3} />
      </div>
    )
  }

  const fallbackEmpty = 'No data yet.'
  const resolvedEmpty = emptyMessage ?? fallbackEmpty

  if (state === 'empty' && emptyMessage === undefined && import.meta.env.DEV) {
    console.warn(
      `DashboardWidget "${testid}": state="empty" without emptyMessage — falling back to "${fallbackEmpty}".`,
    )
  }

  return (
    <AnimatedCard className="p-6 h-full flex flex-col">
      <div data-testid={`widget-${testid}`} className="flex flex-col h-full">
        <h3 className="font-display text-base font-semibold text-text-primary mb-3">
          {title}
        </h3>
        <div className="flex-1 flex flex-col">
          {state === 'data' && <div className="flex-1">{children}</div>}
          {state === 'empty' && (
            <div className="flex-1 text-sm text-text-muted">{resolvedEmpty}</div>
          )}
          {state === 'error' && (
            <div className="flex-1 flex flex-col gap-3">
              <div className="text-sm text-text-muted">
                {errorMessage ?? 'Something went wrong.'}
              </div>
              {onRetry && (
                <button
                  type="button"
                  onClick={onRetry}
                  className="self-start text-xs font-medium text-accent-primary hover:underline"
                >
                  Try again
                </button>
              )}
            </div>
          )}
        </div>
        {action && state !== 'error' && (
          <div className="pt-4 mt-auto">
            {action.href ? (
              <Link
                to={action.href}
                onClick={action.onClick}
                className="text-sm font-medium text-accent-primary hover:underline"
              >
                {action.label}
              </Link>
            ) : (
              <button
                type="button"
                onClick={action.onClick}
                className="text-sm font-medium text-accent-primary hover:underline"
              >
                {action.label}
              </button>
            )}
          </div>
        )}
      </div>
    </AnimatedCard>
  )
}
