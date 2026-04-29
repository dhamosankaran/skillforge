import { Flame, Trophy, Snowflake } from 'lucide-react'
import type { StreakSection } from '@/types'

interface StreakProps {
  data: StreakSection | undefined
  coldStart: boolean
}

// Spec #09 §12 D-13 — per-section cold-start copy.
const COLD_START_COPY = "Start a streak today — review one card to begin."

export function Streak({ data, coldStart }: StreakProps) {
  if (!data) {
    return null
  }

  if (coldStart && data.current_streak === 0 && data.total_xp === 0) {
    return (
      <section
        data-testid="dashboard-streak"
        className="rounded-lg border border-border-subtle bg-bg-surface p-6"
      >
        <div className="flex items-center gap-3">
          <Flame size={22} className="text-text-muted" aria-hidden />
          <h2 className="font-display text-lg font-semibold text-text-primary">
            Streak & progress
          </h2>
        </div>
        <p data-testid="dashboard-streak-empty" className="mt-3 text-sm text-text-muted">
          {COLD_START_COPY}
        </p>
      </section>
    )
  }

  return (
    <section
      data-testid="dashboard-streak"
      className="rounded-lg border border-border-subtle bg-bg-surface p-6"
    >
      <div className="flex items-center gap-3">
        <Flame size={22} className="text-text-accent" aria-hidden />
        <h2 className="font-display text-lg font-semibold text-text-primary">
          Streak & progress
        </h2>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StreakStat
          icon={<Flame size={18} className="text-text-accent" aria-hidden />}
          label="Current streak"
          value={`${data.current_streak} day${data.current_streak === 1 ? '' : 's'}`}
          testid="dashboard-streak-current"
        />
        <StreakStat
          icon={<Trophy size={18} className="text-text-accent" aria-hidden />}
          label="Longest"
          value={`${data.longest_streak} day${data.longest_streak === 1 ? '' : 's'}`}
          testid="dashboard-streak-longest"
        />
        <StreakStat
          icon={<Snowflake size={18} className="text-text-accent" aria-hidden />}
          label="Freezes"
          value={String(data.freezes_available)}
          testid="dashboard-streak-freezes"
        />
        <StreakStat
          label="Total XP"
          value={data.total_xp.toLocaleString()}
          testid="dashboard-streak-xp"
        />
      </div>
    </section>
  )
}

function StreakStat({
  icon,
  label,
  value,
  testid,
}: {
  icon?: React.ReactNode
  label: string
  value: string
  testid: string
}) {
  return (
    <div data-testid={testid} className="space-y-1">
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-xs uppercase tracking-wide text-text-muted">{label}</span>
      </div>
      <div className="text-xl font-semibold text-text-primary">{value}</div>
    </div>
  )
}
