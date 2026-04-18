import { useCallback, useEffect, useState } from 'react'
import { DashboardWidget, type WidgetState } from '@/components/home/DashboardWidget'
import { fetchDailyQueue } from '@/services/api'
import type { Persona } from '@/context/AuthContext'

interface TodaysReviewWidgetProps {
  persona: Persona
}

export function TodaysReviewWidget({ persona }: TodaysReviewWidgetProps) {
  const [state, setState] = useState<WidgetState>('loading')
  const [totalDue, setTotalDue] = useState(0)

  const load = useCallback(() => {
    setState('loading')
    fetchDailyQueue()
      .then((res) => {
        setTotalDue(res.total_due)
        setState(res.total_due > 0 ? 'data' : 'empty')
      })
      .catch(() => setState('error'))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <DashboardWidget
      title="Today's Review"
      testid="todays-review"
      persona={persona}
      state={state}
      emptyMessage="You're all caught up — no cards due today."
      errorMessage="Couldn't load today's review."
      onRetry={load}
      action={
        state === 'data'
          ? { label: 'Start review', href: '/learn/daily' }
          : undefined
      }
    >
      <div className="text-sm text-text-secondary">
        <span className="font-display text-2xl font-semibold text-text-primary">
          {totalDue}
        </span>{' '}
        {totalDue === 1 ? 'card' : 'cards'} due today.
      </div>
    </DashboardWidget>
  )
}
