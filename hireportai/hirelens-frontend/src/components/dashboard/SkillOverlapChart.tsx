import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  Legend,
  Tooltip as RechartsTooltip,
} from 'recharts'
import type { SkillOverlapData } from '@/types'

interface SkillOverlapChartProps {
  data: SkillOverlapData[]
}

export function SkillOverlapChart({ data }: SkillOverlapChartProps) {
  const s = getComputedStyle(document.documentElement)
  const textMuted = s.getPropertyValue('--text-muted').trim()
  const bgElevated = s.getPropertyValue('--bg-elevated').trim()
  const textPrimary = s.getPropertyValue('--text-primary').trim()
  const accent = s.getPropertyValue('--accent-primary').trim()
  const success = s.getPropertyValue('--success').trim()

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-text-muted text-sm">
        No skill overlap data available
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
        <PolarGrid stroke="rgba(255,255,255,0.06)" />
        <PolarAngleAxis
          dataKey="subject"
          tick={{ fill: textMuted, fontSize: 11 }}
        />
        <RechartsTooltip
          contentStyle={{
            background: bgElevated,
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '8px',
            color: textPrimary,
            fontSize: '12px',
          }}
        />
        <Radar
          name="Job Description"
          dataKey="jd"
          stroke={accent}
          fill={accent}
          fillOpacity={0.15}
          strokeWidth={2}
        />
        <Radar
          name="Your Resume"
          dataKey="resume"
          stroke={success}
          fill={success}
          fillOpacity={0.2}
          strokeWidth={2}
        />
        <Legend
          iconType="circle"
          wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}
