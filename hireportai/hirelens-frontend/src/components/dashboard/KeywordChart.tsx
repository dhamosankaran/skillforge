import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { KeywordChartData } from '@/types'

export type KeywordColorVar =
  | '--color-success'
  | '--color-danger'
  | '--color-accent-secondary'

export interface KeywordLegendEntry {
  id: 'matched' | 'missing' | 'in_resume'
  label: string
  cssVarName: KeywordColorVar
  alpha: number
}

// Single source of truth consumed by both the chart cells and the legend
// swatches in Results.tsx. Alphas are chart-cell-canonical per spec #21
// Option A (legend aligns to chart, not vice-versa).
export const KEYWORD_LEGEND: readonly KeywordLegendEntry[] = [
  { id: 'matched', label: 'Matched', cssVarName: '--color-success', alpha: 1 },
  { id: 'missing', label: 'Missing', cssVarName: '--color-danger', alpha: 0.25 },
  { id: 'in_resume', label: 'In resume', cssVarName: '--color-accent-secondary', alpha: 0.5 },
] as const

export function rgbaFromCssVar(name: KeywordColorVar | string, alpha: number): string {
  const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  // design-tokens.ts emits --color-* as space-separated RGB triples.
  const parts = raw.split(/\s+/).filter(Boolean)
  if (parts.length !== 3) {
    // Safe fallback: transparent if the var isn't in the expected shape.
    return `rgba(0, 0, 0, ${alpha})`
  }
  return `rgba(${parts[0]}, ${parts[1]}, ${parts[2]}, ${alpha})`
}

interface KeywordChartProps {
  data: KeywordChartData[]
}

const CustomTooltip = ({ active, payload, label }: {
  active?: boolean
  payload?: Array<{ name: string; value: number; color: string }>
  label?: string
}) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-bg-overlay border border-contrast/10 rounded-lg p-3 text-sm shadow-lg">
        <p className="font-medium text-text-primary mb-1">{label}</p>
        {payload.map((p) => (
          <p key={p.name} style={{ color: p.color }}>
            {p.name}: {p.value}
          </p>
        ))}
      </div>
    )
  }
  return null
}

export function KeywordChart({ data }: KeywordChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-text-muted text-sm">
        No keyword data available
      </div>
    )
  }

  const matchedEntry = KEYWORD_LEGEND.find((e) => e.id === 'matched')!
  const missingEntry = KEYWORD_LEGEND.find((e) => e.id === 'missing')!
  const inResumeEntry = KEYWORD_LEGEND.find((e) => e.id === 'in_resume')!

  const matchedFill = rgbaFromCssVar(matchedEntry.cssVarName, matchedEntry.alpha)
  const missingFill = rgbaFromCssVar(missingEntry.cssVarName, missingEntry.alpha)
  const inResumeFill = rgbaFromCssVar(inResumeEntry.cssVarName, inResumeEntry.alpha)

  const textMuted = getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim()

  // Show top 16 by JD count
  const chartData = [...data]
    .sort((a, b) => b.jd_count - a.jd_count)
    .slice(0, 16)

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart
        data={chartData}
        margin={{ top: 4, right: 8, left: -20, bottom: 60 }}
        barGap={2}
      >
        <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.04)" />
        <XAxis
          dataKey="keyword"
          tick={{ fill: textMuted, fontSize: 10 }}
          angle={-45}
          textAnchor="end"
          interval={0}
        />
        <YAxis tick={{ fill: textMuted, fontSize: 10 }} />
        <RechartsTooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
        <Bar dataKey="jd_count" name="In JD" radius={[3, 3, 0, 0]}>
          {chartData.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.matched ? matchedFill : missingFill}
              stroke={entry.matched ? matchedFill : missingFill}
              strokeWidth={1}
            />
          ))}
        </Bar>
        <Bar dataKey="resume_count" name="In Resume" fill={inResumeFill} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
