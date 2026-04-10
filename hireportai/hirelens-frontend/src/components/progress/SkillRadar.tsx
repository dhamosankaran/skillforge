/**
 * SkillRadar — recharts radar/spider chart showing per-category mastery.
 *
 * Fetches /api/v1/progress/radar on mount and renders a PolarGrid radar
 * where each axis is a flashcard category and the value is mastery_pct (0-100).
 */
import { useEffect, useState } from 'react'
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import api from '@/services/api'

interface CategoryCoverage {
  category: string
  total_cards: number
  studied: number
  mastery_pct: number
}

interface RadarResponse {
  categories: CategoryCoverage[]
}

export function SkillRadar() {
  const [data, setData] = useState<CategoryCoverage[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<RadarResponse>('/api/v1/progress/radar')
      .then((r) => setData(r.data.categories))
      .catch((e) =>
        setError(e instanceof Error ? e.message : 'Failed to load radar data'),
      )
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-text-muted text-[11px]">
        Loading skill radar...
      </div>
    )
  }

  if (error || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-text-muted text-[11px]">
        {error ?? 'No categories found. Study some cards to see your radar.'}
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <RadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
        <PolarGrid stroke="rgba(255,255,255,0.08)" />
        <PolarAngleAxis
          dataKey="category"
          tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 10 }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 100]}
          tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 9 }}
          axisLine={false}
        />
        <Radar
          name="Mastery"
          dataKey="mastery_pct"
          stroke="#7c3aed"
          fill="#7c3aed"
          fillOpacity={0.25}
          strokeWidth={2}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1a1a1d',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 8,
            fontSize: 11,
          }}
          formatter={(value: number) => [`${value}%`, 'Mastery']}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}
