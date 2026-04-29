import { TrendingUp } from 'lucide-react'
import type { RetentionSection } from '@/types'

interface RetentionCurveProps {
  data: RetentionSection | undefined
  coldStart: boolean
}

// Spec #09 §12 D-13 — per-section cold-start copy.
const COLD_START_COPY =
  "Review some cards to see your retention curve over time."

// Spec #09 §12 D-4 — hand-rolled SVG; no chart library dep.
const CHART_WIDTH = 600
const CHART_HEIGHT = 160
const PADDING_X = 32
const PADDING_Y = 16

export function RetentionCurve({ data, coldStart }: RetentionCurveProps) {
  if (!data || coldStart || data.sample_size === 0) {
    return (
      <section
        data-testid="dashboard-retention"
        className="rounded-lg border border-border-subtle bg-bg-surface p-6"
      >
        <div className="flex items-center gap-3">
          <TrendingUp size={22} className="text-text-muted" aria-hidden />
          <h2 className="font-display text-lg font-semibold text-text-primary">
            Retention
          </h2>
        </div>
        <p data-testid="dashboard-retention-empty" className="mt-3 text-sm text-text-muted">
          {COLD_START_COPY}
        </p>
      </section>
    )
  }

  const points = data.daily_retention
  const width = CHART_WIDTH
  const height = CHART_HEIGHT
  const innerW = width - PADDING_X * 2
  const innerH = height - PADDING_Y * 2

  // x position per index, y from recall_rate (null → no point on the line).
  const xFor = (i: number) =>
    points.length <= 1 ? PADDING_X : PADDING_X + (i / (points.length - 1)) * innerW
  const yFor = (rate: number) => PADDING_Y + (1 - rate) * innerH

  // Build the line path skipping null sample-zero days (move-to on the
  // next sampled day so gaps don't visually interpolate).
  let pathParts: string[] = []
  let needMove = true
  points.forEach((p, i) => {
    if (p.recall_rate === null) {
      needMove = true
      return
    }
    const x = xFor(i)
    const y = yFor(p.recall_rate)
    pathParts.push(`${needMove ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`)
    needMove = false
  })
  const path = pathParts.join(' ')

  return (
    <section
      data-testid="dashboard-retention"
      className="rounded-lg border border-border-subtle bg-bg-surface p-6"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <TrendingUp size={22} className="text-text-accent" aria-hidden />
          <h2 className="font-display text-lg font-semibold text-text-primary">
            Retention
          </h2>
        </div>
        <div data-testid="dashboard-retention-summary" className="text-sm text-text-muted">
          <span className="font-semibold text-text-primary">
            {Math.round(data.overall_recall_rate * 100)}%
          </span>{' '}
          recall · {data.sample_size} review{data.sample_size === 1 ? '' : 's'}
        </div>
      </div>
      <svg
        data-testid="dashboard-retention-chart"
        viewBox={`0 0 ${width} ${height}`}
        className="mt-4 w-full"
        role="img"
        aria-label="Daily retention curve"
      >
        {/* Baselines: 50% and 100% */}
        <line
          x1={PADDING_X}
          x2={width - PADDING_X}
          y1={yFor(0.5)}
          y2={yFor(0.5)}
          className="stroke-border-subtle"
          strokeDasharray="3 3"
        />
        <line
          x1={PADDING_X}
          x2={width - PADDING_X}
          y1={yFor(1)}
          y2={yFor(1)}
          className="stroke-border-subtle"
        />
        {/* Sample-zero day markers */}
        {points.map((p, i) =>
          p.recall_rate === null ? (
            <circle
              key={`zero-${i}`}
              cx={xFor(i)}
              cy={yFor(0)}
              r={1.5}
              className="fill-border-subtle"
            />
          ) : null,
        )}
        {/* Recall path */}
        {path && (
          <path
            d={path}
            fill="none"
            className="stroke-text-accent"
            strokeWidth={2}
          />
        )}
        {/* Sampled dots */}
        {points.map((p, i) =>
          p.recall_rate !== null ? (
            <circle
              key={`pt-${i}`}
              cx={xFor(i)}
              cy={yFor(p.recall_rate)}
              r={3}
              className="fill-text-accent"
            />
          ) : null,
        )}
      </svg>
    </section>
  )
}
