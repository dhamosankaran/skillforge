/**
 * Profile page — full gamification + study stats view.
 *
 * Sections (top → bottom):
 *   1. User identity (avatar, name, email)
 *   2. Streak card  — current + longest, freezes available
 *   3. XPBar        — progress toward next tier
 *   4. Badges grid  — every catalog badge, locked or earned
 *   5. Study history — counts from /api/v1/study/progress
 *
 * Data is loaded from two endpoints:
 *   - GET /api/v1/gamification/stats   (via GamificationContext)
 *   - GET /api/v1/study/progress       (fetched here, lightweight)
 *
 * The badge catalog is hard-coded to mirror BADGES in
 * gamification_service.py. Locked badges show the threshold so users know
 * what to aim for; earned badges show the date and a glow.
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Flame, Lock, Trophy, BookOpen, Sparkles, Radar, CalendarDays, Settings, FileText, Copy, Check, Loader2, CreditCard, LogOut } from 'lucide-react'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { XPBar } from '@/components/profile/XPBar'
import { useGamification } from '@/context/GamificationContext'
import { useAuth } from '@/context/AuthContext'
import { useUsage } from '@/context/UsageContext'
import { capture } from '@/utils/posthog'
import api, { createBillingPortalSession, generateExperience } from '@/services/api'
import { SkillRadar } from '@/components/progress/SkillRadar'
import { ActivityHeatmap } from '@/components/progress/ActivityHeatmap'
import { EmailPreferences } from '@/components/settings/EmailPreferences'
import { ThemePicker } from '@/components/settings/ThemePicker'

// ── Badge catalog (mirror of backend BADGES tuple) ───────────────────────────

interface BadgeCatalogEntry {
  id: string
  name: string
  description: string
  hint: string
}

const BADGE_CATALOG: BadgeCatalogEntry[] = [
  { id: 'first_review', name: 'First Step',      description: 'Reviewed your first card',     hint: 'Review any card' },
  { id: 'streak_3',     name: 'On a Roll',       description: '3-day streak',                 hint: '3-day streak' },
  { id: 'streak_7',     name: 'One Week Strong', description: '7-day streak',                 hint: '7-day streak' },
  { id: 'streak_30',    name: 'Habit Formed',    description: '30-day streak',                hint: '30-day streak' },
  { id: 'streak_100',   name: 'Centurion',       description: '100-day streak',               hint: '100-day streak' },
  { id: 'xp_100',       name: 'Apprentice',      description: 'Earned 100 XP',                hint: '100 XP' },
  { id: 'xp_500',       name: 'Journeyman',      description: 'Earned 500 XP',                hint: '500 XP' },
  { id: 'xp_2000',      name: 'Expert',          description: 'Earned 2000 XP',               hint: '2 000 XP' },
  { id: 'xp_10000',     name: 'Master',          description: 'Earned 10 000 XP',             hint: '10 000 XP' },
]

// ── Study progress (separate endpoint) ───────────────────────────────────────

interface StudyProgress {
  total_reviewed: number
  by_state: Record<string, number>
  total_reps: number
  total_lapses: number
}

async function fetchStudyProgress(): Promise<StudyProgress> {
  const r = await api.get<StudyProgress>('/api/v1/study/progress')
  return r.data
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function Profile() {
  const { user, signOut } = useAuth()
  const { usage } = useUsage()
  const navigate = useNavigate()
  const { stats, isLoading, refresh } = useGamification()
  const [progress, setProgress] = useState<StudyProgress | null>(null)
  const [progressError, setProgressError] = useState<string | null>(null)
  const [experienceText, setExperienceText] = useState<string | null>(null)
  const [experienceLoading, setExperienceLoading] = useState(false)
  const [experienceCopied, setExperienceCopied] = useState(false)
  const [experienceError, setExperienceError] = useState<string | null>(null)
  const [portalLoading, setPortalLoading] = useState(false)
  const [portalError, setPortalError] = useState<string | null>(null)

  const isPro = usage.plan === 'pro'

  async function handleManageSubscription() {
    setPortalLoading(true)
    setPortalError(null)
    capture('subscription_portal_opened')
    try {
      const res = await createBillingPortalSession()
      window.location.href = res.url
    } catch {
      setPortalError("Couldn't open billing portal. Please try again.")
      setPortalLoading(false)
    }
  }

  useEffect(() => {
    capture('profile_viewed')
    void refresh()
    fetchStudyProgress()
      .then(setProgress)
      .catch((e) => setProgressError(e instanceof Error ? e.message : 'Failed to load progress'))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const earnedIds = new Set(stats?.badges.map((b) => b.badge_id) ?? [])
  const earnedAtById = new Map(stats?.badges.map((b) => [b.badge_id, b.earned_at]) ?? [])

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div className="max-w-4xl mx-auto px-4 py-10 sm:px-6 space-y-8">
        {/* ── Identity ─────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-4"
        >
          {user?.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={user.name}
              className="w-14 h-14 rounded-full border border-contrast/10 ring-2 ring-accent-primary/20"
              referrerPolicy="no-referrer"
            />
          ) : (
            <div className="w-14 h-14 rounded-full bg-accent-primary/20 border border-accent-primary/30 flex items-center justify-center text-accent-primary text-xl font-bold">
              {user?.name?.charAt(0).toUpperCase() ?? '?'}
            </div>
          )}
          <div>
            <h1 className="font-display text-2xl font-bold text-text-primary">{user?.name ?? 'Profile'}</h1>
            <p className="text-sm text-text-muted">{user?.email}</p>
          </div>
        </motion.div>

        {/* ── Streak + XP cards ────────────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Streak */}
          <div className="rounded-2xl border border-contrast/[0.08] bg-bg-surface/60 p-5">
            <div className="flex items-center gap-2 mb-3">
              <Flame size={14} className="text-orange-400" fill="currentColor" />
              <span className="text-[11px] uppercase tracking-[0.15em] text-text-secondary font-semibold">
                Streak
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-bold text-text-primary tabular-nums">
                {stats?.current_streak ?? 0}
              </span>
              <span className="text-sm text-text-muted">days</span>
            </div>
            <div className="mt-3 flex items-center gap-4 text-[11px] text-text-muted">
              <span>Longest: <span className="text-text-secondary tabular-nums">{stats?.longest_streak ?? 0}</span></span>
              <span>Freezes: <span className="text-text-secondary tabular-nums">{stats?.freezes_available ?? 0}</span></span>
            </div>
          </div>

          {/* XP */}
          <div className="rounded-2xl border border-contrast/[0.08] bg-bg-surface/60 p-5">
            <XPBar totalXp={stats?.total_xp ?? 0} />
          </div>
        </div>

        {/* ── Badges ───────────────────────────────────────────────── */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={14} className="text-accent-primary" />
            <h2 className="text-[11px] uppercase tracking-[0.15em] text-text-secondary font-semibold">
              Badges ({earnedIds.size}/{BADGE_CATALOG.length})
            </h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {BADGE_CATALOG.map((b) => {
              const earned = earnedIds.has(b.id)
              const earnedAt = earnedAtById.get(b.id)
              return (
                <motion.div
                  key={b.id}
                  whileHover={{ y: -2 }}
                  className={
                    'rounded-xl border p-3 transition-all duration-200 ' +
                    (earned
                      ? 'border-accent-primary/30 bg-accent-primary/5 shadow-glow'
                      : 'border-contrast/[0.06] bg-bg-surface/40 opacity-60')
                  }
                >
                  <div className="flex items-center gap-2 mb-1">
                    {earned ? (
                      <Trophy size={12} className="text-accent-primary" />
                    ) : (
                      <Lock size={12} className="text-text-muted" />
                    )}
                    <span className="text-[11px] font-semibold text-text-primary truncate">
                      {b.name}
                    </span>
                  </div>
                  <p className="text-[10px] text-text-muted leading-snug">
                    {earned ? b.description : `Locked — ${b.hint}`}
                  </p>
                  {earned && earnedAt && (
                    <p className="mt-1 text-[9px] text-text-muted/80 tabular-nums">
                      {new Date(earnedAt).toLocaleDateString()}
                    </p>
                  )}
                </motion.div>
              )
            })}
          </div>
        </section>

        {/* ── Study history ────────────────────────────────────────── */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <BookOpen size={14} className="text-accent-primary" />
            <h2 className="text-[11px] uppercase tracking-[0.15em] text-text-secondary font-semibold">
              Study history
            </h2>
          </div>
          {progressError ? (
            <p className="text-[11px] text-text-muted">Couldn't load study history.</p>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Stat label="Reviewed" value={progress?.total_reviewed ?? 0} />
              <Stat label="Reps"     value={progress?.total_reps ?? 0} />
              <Stat label="Lapses"   value={progress?.total_lapses ?? 0} />
              <Stat label="In review" value={progress?.by_state?.review ?? 0} />
            </div>
          )}
        </section>

        {/* ── Experience generator ─────────────────────────────────── */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <FileText size={14} className="text-accent-primary" />
            <h2 className="text-[11px] uppercase tracking-[0.15em] text-text-secondary font-semibold">
              My Experience
            </h2>
          </div>
          <div className="rounded-2xl border border-contrast/[0.08] bg-bg-surface/60 p-5">
            {experienceText ? (
              <div className="space-y-3">
                <p className="text-sm text-text-secondary leading-relaxed">{experienceText}</p>
                <button
                  onClick={() => {
                    void navigator.clipboard.writeText(experienceText)
                    setExperienceCopied(true)
                    setTimeout(() => setExperienceCopied(false), 2000)
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-contrast/[0.08] text-[11px] text-text-muted hover:text-text-secondary hover:border-contrast/[0.15] transition-colors"
                >
                  {experienceCopied ? <Check size={12} /> : <Copy size={12} />}
                  {experienceCopied ? 'Copied!' : 'Copy to clipboard'}
                </button>
                <button
                  onClick={() => { setExperienceText(null); setExperienceError(null) }}
                  className="ml-2 text-[11px] text-text-muted hover:text-text-secondary transition-colors"
                >
                  Regenerate
                </button>
              </div>
            ) : progress !== null && progress.total_reviewed === 0 ? (
              <p className="text-xs text-text-muted text-center py-4">
                Study some cards first to generate your experience summary.
              </p>
            ) : (
              <div className="flex flex-col items-center gap-3 py-2">
                <p className="text-xs text-text-muted text-center max-w-sm">
                  Generate a resume-ready bullet point from your study history, powered by AI.
                </p>
                {experienceError && (
                  <p className="text-xs text-red-400 text-center">{experienceError}</p>
                )}
                <button
                  onClick={async () => {
                    setExperienceLoading(true)
                    setExperienceError(null)
                    try {
                      const res = await generateExperience({})
                      setExperienceText(res.experience_text)
                      capture('experience_generated', { topic: '', cards_studied_count: res.cards_studied })
                    } catch {
                      setExperienceError('Failed to generate experience. Please try again.')
                    } finally {
                      setExperienceLoading(false)
                    }
                  }}
                  disabled={experienceLoading}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-primary/10 border border-accent-primary/25 text-accent-primary text-sm font-semibold hover:bg-accent-primary/18 transition-colors disabled:opacity-40"
                >
                  {experienceLoading ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles size={14} />
                      Generate My Experience
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </section>

        {/* ── Skill radar ──────────────────────────────────────────── */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <Radar size={14} className="text-accent-primary" />
            <h2 className="text-[11px] uppercase tracking-[0.15em] text-text-secondary font-semibold">
              Skill coverage
            </h2>
          </div>
          <div className="rounded-2xl border border-contrast/[0.08] bg-bg-surface/60 p-5">
            <SkillRadar />
          </div>
        </section>

        {/* ── Activity heatmap ────────────────────────────────────── */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <CalendarDays size={14} className="text-accent-primary" />
            <h2 className="text-[11px] uppercase tracking-[0.15em] text-text-secondary font-semibold">
              Activity
            </h2>
          </div>
          <div className="rounded-2xl border border-contrast/[0.08] bg-bg-surface/60 p-5 overflow-x-auto">
            <ActivityHeatmap />
          </div>
        </section>

        {/* ── Theme ─────────────────────────────────────────────── */}
        <section>
          <ThemePicker />
        </section>

        {/* ── Subscription ──────────────────────────────────────── */}
        <section data-testid="subscription-section">
          <div className="flex items-center gap-2 mb-3">
            <CreditCard size={14} className="text-accent-primary" />
            <h2 className="text-[11px] uppercase tracking-[0.15em] text-text-secondary font-semibold">
              Subscription
            </h2>
          </div>
          <div className="rounded-2xl border border-contrast/[0.08] bg-bg-surface/60 p-5">
            {isPro ? (
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold text-text-primary">Pro plan</p>
                  <p className="text-[11px] text-text-muted mt-1">Active</p>
                </div>
                <div className="flex flex-col items-start sm:items-end gap-1">
                  <button
                    onClick={handleManageSubscription}
                    disabled={portalLoading}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-primary/10 border border-accent-primary/25 text-accent-primary text-sm font-semibold hover:bg-accent-primary/18 transition-colors disabled:opacity-40"
                  >
                    {portalLoading ? (
                      <>
                        <Loader2 size={14} className="animate-spin" />
                        Opening…
                      </>
                    ) : (
                      'Manage subscription'
                    )}
                  </button>
                  {portalError && (
                    <p className="text-[11px] text-danger">{portalError}</p>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold text-text-primary">Free plan</p>
                  <p className="text-[11px] text-text-muted mt-1">
                    Unlock Pro for full library access and unlimited scans.
                  </p>
                </div>
                <button
                  onClick={() => navigate('/pricing')}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-primary/10 border border-accent-primary/25 text-accent-primary text-sm font-semibold hover:bg-accent-primary/18 transition-colors"
                >
                  Upgrade to Pro
                </button>
              </div>
            )}
          </div>
        </section>

        {/* ── Settings ──────────────────────────────────────────── */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <Settings size={14} className="text-accent-primary" />
            <h2 className="text-[11px] uppercase tracking-[0.15em] text-text-secondary font-semibold">
              Settings
            </h2>
          </div>
          <EmailPreferences />
        </section>

        {/* ── Account ──────────────────────────────────────────── */}
        <section data-testid="account-section">
          <div className="flex items-center gap-2 mb-3">
            <LogOut size={14} className="text-accent-primary" />
            <h2 className="text-[11px] uppercase tracking-[0.15em] text-text-secondary font-semibold">
              Account
            </h2>
          </div>
          <div className="rounded-2xl border border-contrast/[0.08] bg-bg-surface/60 p-5">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-text-primary">Sign out</p>
                <p className="text-[11px] text-text-muted mt-1">
                  End your session on this device.
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  capture('sign_out_clicked', { source: 'profile_page' })
                  void signOut()
                }}
                data-testid="profile-signout"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-contrast/[0.12] text-sm font-semibold text-text-secondary hover:text-danger hover:border-danger/40 transition-colors"
              >
                <LogOut size={14} />
                Sign out
              </button>
            </div>
          </div>
        </section>

        {isLoading && (
          <p className="text-center text-[11px] text-text-muted">Refreshing…</p>
        )}
      </div>
    </PageWrapper>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-contrast/[0.06] bg-bg-surface/40 p-4">
      <p className="text-[10px] uppercase tracking-[0.15em] text-text-muted mb-1">{label}</p>
      <p className="text-xl font-semibold text-text-primary tabular-nums">{value}</p>
    </div>
  )
}
