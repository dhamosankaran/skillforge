/**
 * ActivityHeatmap — GitHub-style contribution heatmap for study sessions.
 *
 * Fetches /api/v1/progress/heatmap?days=90 on mount and renders a CSS grid
 * with 7 rows (Mon–Sun) and ~13 columns (weeks). Cell intensity reflects
 * the number of card reviews on that day.
 */
import { useEffect, useState } from 'react'
import api from '@/services/api'

interface HeatmapDay {
  date: string
  review_count: number
}

interface HeatmapResponse {
  days: HeatmapDay[]
}

const INTENSITY_CLASSES = [
  'bg-white/[0.04]',                     // 0 reviews
  'bg-violet-500/30',                     // 1–2
  'bg-violet-500/50',                     // 3–4
  'bg-violet-500/70',                     // 5–7
  'bg-violet-500',                        // 8+
]

function getIntensity(count: number): string {
  if (count === 0) return INTENSITY_CLASSES[0]
  if (count <= 2) return INTENSITY_CLASSES[1]
  if (count <= 4) return INTENSITY_CLASSES[2]
  if (count <= 7) return INTENSITY_CLASSES[3]
  return INTENSITY_CLASSES[4]
}

const DAY_LABELS = ['Mon', '', 'Wed', '', 'Fri', '', 'Sun']

export function ActivityHeatmap() {
  const [data, setData] = useState<HeatmapDay[]>([])
  const [loading, setLoading] = useState(true)
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null)

  useEffect(() => {
    api
      .get<HeatmapResponse>('/api/v1/progress/heatmap', { params: { days: 90 } })
      .then((r) => setData(r.data.days))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32 text-text-muted text-[11px]">
        Loading activity...
      </div>
    )
  }

  // Reverse so oldest is first (data comes most-recent-first from API)
  const sorted = [...data].reverse()

  // Pad the start so the first date aligns to its correct weekday row
  const firstDate = sorted.length > 0 ? new Date(sorted[0].date) : new Date()
  // getDay: 0=Sun → we want 0=Mon, so (getDay()+6)%7
  const startDow = (firstDate.getDay() + 6) % 7
  const padded: (HeatmapDay | null)[] = [
    ...Array.from<null>({ length: startDow }).fill(null),
    ...sorted,
  ]

  const weeks = Math.ceil(padded.length / 7)

  return (
    <div className="relative">
      <div className="flex gap-[3px]">
        {/* Day labels column */}
        <div className="flex flex-col gap-[3px] mr-1">
          {DAY_LABELS.map((label, i) => (
            <div
              key={i}
              className="w-6 h-[13px] text-[9px] text-text-muted flex items-center justify-end pr-1"
            >
              {label}
            </div>
          ))}
        </div>

        {/* Grid of cells */}
        {Array.from({ length: weeks }, (_, weekIdx) => (
          <div key={weekIdx} className="flex flex-col gap-[3px]">
            {Array.from({ length: 7 }, (_, dayIdx) => {
              const idx = weekIdx * 7 + dayIdx
              const entry = padded[idx]
              if (!entry) {
                return <div key={dayIdx} className="w-[13px] h-[13px]" />
              }
              return (
                <div
                  key={dayIdx}
                  className={`w-[13px] h-[13px] rounded-[2px] cursor-default transition-colors ${getIntensity(entry.review_count)}`}
                  onMouseEnter={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect()
                    setTooltip({
                      x: rect.left + rect.width / 2,
                      y: rect.top - 8,
                      text: `${entry.review_count} review${entry.review_count !== 1 ? 's' : ''} on ${entry.date}`,
                    })
                  }}
                  onMouseLeave={() => setTooltip(null)}
                />
              )
            })}
          </div>
        ))}
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 px-2 py-1 rounded bg-bg-surface border border-white/10 text-[10px] text-text-secondary pointer-events-none -translate-x-1/2 -translate-y-full"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          {tooltip.text}
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center justify-end gap-1 mt-2 text-[9px] text-text-muted">
        <span>Less</span>
        {INTENSITY_CLASSES.map((cls, i) => (
          <div key={i} className={`w-[11px] h-[11px] rounded-[2px] ${cls}`} />
        ))}
        <span>More</span>
      </div>
    </div>
  )
}
