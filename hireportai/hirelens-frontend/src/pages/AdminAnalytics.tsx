import { useCallback, useEffect, useMemo, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { AlertTriangle, Loader2 } from 'lucide-react'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { useAuth } from '@/context/AuthContext'
import {
  fetchAdminAnalyticsMetrics,
  fetchAdminAnalyticsPerformance,
  type AdminAnalyticsMetricValue,
  type AdminAnalyticsMetricsResponse,
  type AdminAnalyticsPerformanceResponse,
} from '@/services/api'
import { capture } from '@/utils/posthog'

type Segment = '7d' | '30d' | '90d' | 'YTD'

/** Compute the `from` ISO date (UTC) for a given range segment relative to now. */
export function computeFromDate(segment: Segment, now: Date = new Date()): string {
  const d = new Date(now)
  switch (segment) {
    case '7d':
      d.setUTCDate(d.getUTCDate() - 7)
      break
    case '30d':
      d.setUTCDate(d.getUTCDate() - 30)
      break
    case '90d':
      d.setUTCDate(d.getUTCDate() - 90)
      break
    case 'YTD':
      return `${now.getUTCFullYear()}-01-01`
  }
  return d.toISOString().slice(0, 10)
}

const OKR_LABELS: Record<keyof Omit<AdminAnalyticsMetricsResponse, 'generated_at' | 'from_cache'>, string> = {
  registered_users: 'Registered users',
  paying_pro_users: 'Paying Pro users',
  dau_mau_ratio: 'DAU / MAU',
  avg_streak_length: 'Avg streak (days)',
  ats_to_pro_conversion: 'ATS → Pro',
  monthly_churn: 'Monthly churn',
}

function formatValue(key: string, v: number): string {
  if (key === 'dau_mau_ratio' || key === 'ats_to_pro_conversion' || key === 'monthly_churn') {
    return `${(v * 100).toFixed(1)}%`
  }
  if (key === 'avg_streak_length') return v.toFixed(1)
  return Math.round(v).toLocaleString()
}

function formatDelta(pct: number): { text: string; tone: 'up' | 'down' | 'flat' } {
  if (pct === 0) return { text: '0.0%', tone: 'flat' }
  const tone = pct > 0 ? 'up' : 'down'
  const sign = pct > 0 ? '+' : ''
  return { text: `${sign}${pct.toFixed(1)}%`, tone }
}

function MetricTile({ label, value, metric }: { label: string; value: string; metric: AdminAnalyticsMetricValue }) {
  const d7 = formatDelta(metric.delta_7d_pct)
  const d30 = formatDelta(metric.delta_30d_pct)
  const toneClass = (tone: 'up' | 'down' | 'flat') =>
    tone === 'up'
      ? 'text-accent-primary'
      : tone === 'down'
      ? 'text-text-muted'
      : 'text-text-muted'

  return (
    <div
      data-testid={`metric-tile-${label}`}
      className="bg-bg-surface/60 border border-contrast/[0.06] rounded-xl p-5"
    >
      <div className="text-xs text-text-muted uppercase tracking-wide">{label}</div>
      <div className="mt-2 text-3xl font-semibold text-text-primary">{value}</div>
      <div className="mt-3 flex gap-4 text-xs">
        <span className={toneClass(d7.tone)}>{d7.text} vs 7d</span>
        <span className={toneClass(d30.tone)}>{d30.text} vs 30d</span>
      </div>
    </div>
  )
}

function ComingSoonTile({ label, reason }: { label: string; reason: string }) {
  return (
    <div
      data-testid={`coming-soon-${label}`}
      className="bg-bg-surface/40 border border-dashed border-contrast/[0.08] rounded-xl p-5"
    >
      <div className="text-xs text-text-muted uppercase tracking-wide">{label}</div>
      <div className="mt-2 text-lg font-medium text-text-muted">Coming soon</div>
      <div className="mt-2 text-xs text-text-muted">{reason}</div>
    </div>
  )
}

function SectionHeader({ title, fromCache }: { title: string; fromCache: boolean }) {
  return (
    <div className="flex items-baseline justify-between mb-4">
      <h2 className="text-xl font-semibold text-text-primary">{title}</h2>
      {fromCache && (
        <span className="text-xs text-text-muted" data-testid={`from-cache-${title}`}>
          cached
        </span>
      )}
    </div>
  )
}

export default function AdminAnalytics() {
  const { user, isLoading: authLoading } = useAuth()
  if (authLoading) return null
  if (!user || user.role !== 'admin') return <Navigate to="/prep/analyze" replace />
  return <Dashboard />
}

function Dashboard() {
  const [segment, setSegment] = useState<Segment>('30d')
  const [metrics, setMetrics] = useState<AdminAnalyticsMetricsResponse | null>(null)
  const [perf, setPerf] = useState<AdminAnalyticsPerformanceResponse | null>(null)
  const [metricsError, setMetricsError] = useState<string | null>(null)
  const [perfError, setPerfError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const fromDate = useMemo(() => computeFromDate(segment), [segment])

  const load = useCallback(async () => {
    setLoading(true)
    setMetricsError(null)
    setPerfError(null)
    const params = { from: fromDate }
    const [m, p] = await Promise.allSettled([
      fetchAdminAnalyticsMetrics(params),
      fetchAdminAnalyticsPerformance(params),
    ])
    if (m.status === 'fulfilled') setMetrics(m.value)
    else setMetricsError('Failed to load metrics')
    if (p.status === 'fulfilled') setPerf(p.value)
    else setPerfError('Failed to load performance')
    setLoading(false)
  }, [fromDate])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    capture('admin_analytics_segment_changed', { segment })
  }, [segment])

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div className="max-w-7xl mx-auto px-4 py-10">
        <div className="flex items-center justify-between mb-8">
          <h1 className="font-display text-3xl font-bold text-text-primary">
            Admin <span className="text-accent-primary">Analytics</span>
          </h1>
          <SegmentedControl value={segment} onChange={setSegment} />
        </div>

        {loading && (
          <div className="flex items-center gap-2 text-text-muted mb-6">
            <Loader2 size={16} className="animate-spin" />
            <span>Loading…</span>
          </div>
        )}

        <section className="mb-10">
          <SectionHeader title="Metrics" fromCache={metrics?.from_cache ?? false} />
          {metricsError ? (
            <ErrorNote message={metricsError} onRetry={load} />
          ) : metrics ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="metrics-grid">
              {(Object.keys(OKR_LABELS) as (keyof typeof OKR_LABELS)[]).map((key) => (
                <MetricTile
                  key={key}
                  label={OKR_LABELS[key]}
                  value={formatValue(key, metrics[key].current)}
                  metric={metrics[key]}
                />
              ))}
            </div>
          ) : null}
        </section>

        <section>
          <SectionHeader title="Performance" fromCache={perf?.from_cache ?? false} />
          {perfError ? (
            <ErrorNote message={perfError} onRetry={load} />
          ) : perf ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="performance-grid">
              <div
                data-testid="perf-tile-llm_spend"
                className="bg-bg-surface/60 border border-contrast/[0.06] rounded-xl p-5"
              >
                <div className="text-xs text-text-muted uppercase tracking-wide">
                  LLM spend (month-to-date)
                </div>
                <div className="mt-2 text-3xl font-semibold text-text-primary">
                  ${perf.llm_spend_estimate_usd.toFixed(2)}
                </div>
                <div className="mt-2 text-xs text-text-muted">
                  Lower bound — metering gaps noted in schema
                </div>
              </div>
              <div
                data-testid="perf-tile-stripe_webhook"
                className="bg-bg-surface/60 border border-contrast/[0.06] rounded-xl p-5"
              >
                <div className="text-xs text-text-muted uppercase tracking-wide">
                  Stripe webhook success (24h)
                </div>
                <div className="mt-2 text-3xl font-semibold text-text-primary">
                  {perf.stripe_webhook_available && perf.stripe_webhook_success_24h_pct !== null
                    ? `${perf.stripe_webhook_success_24h_pct.toFixed(1)}%`
                    : '—'}
                </div>
                <div className="mt-2 text-xs text-text-muted">
                  {perf.stripe_webhook_available
                    ? 'Successful processings in last 24h'
                    : 'No webhook activity in window'}
                </div>
              </div>
              <ComingSoonTile
                label="API latency (top 10)"
                reason="Requires backend latency source — tracked as E-018b-follow."
              />
              <ComingSoonTile
                label="5xx error rate (24h)"
                reason="Requires error source — tracked as E-018b-follow-errors."
              />
            </div>
          ) : null}
        </section>
      </div>
    </PageWrapper>
  )
}

function SegmentedControl({ value, onChange }: { value: Segment; onChange: (s: Segment) => void }) {
  const options: Segment[] = ['7d', '30d', '90d', 'YTD']
  return (
    <div className="inline-flex bg-bg-surface/60 border border-contrast/[0.06] rounded-lg p-1" role="tablist">
      {options.map((opt) => (
        <button
          key={opt}
          role="tab"
          aria-selected={value === opt}
          data-testid={`segment-${opt}`}
          onClick={() => onChange(opt)}
          className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
            value === opt
              ? 'bg-bg-elevated text-text-primary'
              : 'text-text-muted hover:text-text-primary'
          }`}
        >
          {opt}
        </button>
      ))}
    </div>
  )
}

function ErrorNote({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex items-center gap-3 p-4 bg-bg-surface/40 border border-contrast/[0.08] rounded-lg">
      <AlertTriangle size={16} className="text-text-muted" />
      <span className="text-sm text-text-muted flex-1">{message}</span>
      <button
        onClick={onRetry}
        className="text-sm text-accent-primary hover:opacity-80"
      >
        Retry
      </button>
    </div>
  )
}
