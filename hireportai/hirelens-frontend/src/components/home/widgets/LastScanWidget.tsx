import { useCallback, useEffect, useState } from 'react'
import { DashboardWidget, type WidgetState } from '@/components/home/DashboardWidget'
import { getApplications } from '@/services/api'
import type { Persona } from '@/context/AuthContext'
import type { TrackerApplication } from '@/types'

interface LastScanWidgetProps {
  persona: Persona
}

export function LastScanWidget({ persona }: LastScanWidgetProps) {
  const [state, setState] = useState<WidgetState>('loading')
  const [latest, setLatest] = useState<TrackerApplication | null>(null)

  const load = useCallback(() => {
    setState('loading')
    getApplications()
      .then((apps) => {
        if (apps.length === 0) {
          setLatest(null)
          setState('empty')
          return
        }
        const sorted = [...apps].sort((a, b) =>
          (b.created_at ?? '').localeCompare(a.created_at ?? ''),
        )
        setLatest(sorted[0])
        setState('data')
      })
      .catch(() => setState('error'))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const action =
    state === 'data' && latest
      ? {
          label: 'View results',
          href: latest.scan_id
            ? `/prep/results?scan_id=${latest.scan_id}`
            : '/prep/tracker',
        }
      : state === 'empty'
        ? { label: 'Scan a resume', href: '/prep/analyze' }
        : undefined

  return (
    <DashboardWidget
      title="Last Scan"
      testid="last-scan"
      persona={persona}
      state={state}
      emptyMessage="Run your first scan to see results here."
      errorMessage="Couldn't load your last scan."
      onRetry={load}
      action={action}
    >
      {latest && (
        <div className="flex flex-col gap-1">
          <div className="font-display text-base font-semibold text-text-primary">
            {latest.company}
          </div>
          <div className="text-sm text-text-secondary">{latest.role}</div>
          <div className="text-xs text-text-muted mt-1">
            ATS score:{' '}
            <span className="font-medium text-text-primary">
              {latest.ats_score}%
            </span>
          </div>
        </div>
      )}
    </DashboardWidget>
  )
}
