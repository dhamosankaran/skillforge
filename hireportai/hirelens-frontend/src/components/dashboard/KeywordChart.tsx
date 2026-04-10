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
  const s = getComputedStyle(document.documentElement)
  const textMuted = s.getPropertyValue('--text-muted').trim()
  const success = s.getPropertyValue('--success').trim()
  const danger = s.getPropertyValue('--danger').trim()

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-text-muted text-sm">
        No keyword data available
      </div>
    )
  }

  // Show top 20 by JD count
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
              fill={entry.matched ? success : `${danger}40`}
              stroke={entry.matched ? `${success}80` : `${danger}60`}
              strokeWidth={1}
            />
          ))}
        </Bar>
        <Bar dataKey="resume_count" name="In Resume" fill="rgba(124,58,237,0.5)" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
