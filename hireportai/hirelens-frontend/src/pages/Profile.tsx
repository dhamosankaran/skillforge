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
import { motion } from 'framer-motion'
import { Flame, Lock, Trophy, BookOpen, Sparkles, Radar, CalendarDays, Settings } from 'lucide-react'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { XPBar } from '@/components/profile/XPBar'
import { useGamification } from '@/context/GamificationContext'
import { useAuth } from '@/context/AuthContext'
import { capture } from '@/utils/posthog'
import api from '@/services/api'
import { SkillRadar } from '@/components/progress/SkillRadar'
import { ActivityHeatmap } from '@/components/progress/ActivityHeatmap'
import { EmailPreferences } from '@/components/settings/EmailPreferences'

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
  const { user } = useAuth()
  const { stats, isLoading, refresh } = useGamification()
  const [progress, setProgress] = useState<StudyProgress | null>(null)
  const [progressError, setProgressError] = useState<string | null>(null)

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
              className="w-14 h-14 rounded-full border border-white/10 ring-2 ring-accent-primary/20"
              referrerPolicy="no-referrer"
            />
          ) : (
            <div className="w-14 h-14 rounded-full bg-accent-primary/20 border border-accent-primary/30 flex items-center justify-center text-accent-primary text-xl font-bold">
              {user?.name?.charAt(0).toUpperCase() ?? '?'}
            </div>
          )}
          <div>
            <h1 className="text-2xl font-semibold text-text-primary">{user?.name ?? 'Profile'}</h1>
            <p className="text-sm text-text-muted">{user?.email}</p>
          </div>
        </motion.div>

        {/* ── Streak + XP cards ────────────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Streak */}
          <div className="rounded-2xl border border-white/[0.08] bg-bg-surface/60 p-5">
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
          <div className="rounded-2xl border border-white/[0.08] bg-bg-surface/60 p-5">
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
                      ? 'border-accent-primary/30 bg-accent-primary/5 shadow-[0_0_24px_rgba(220,38,38,0.08)]'
                      : 'border-white/[0.06] bg-bg-surface/40 opacity-60')
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

        {/* ── Skill radar ──────────────────────────────────────────── */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <Radar size={14} className="text-accent-primary" />
            <h2 className="text-[11px] uppercase tracking-[0.15em] text-text-secondary font-semibold">
              Skill coverage
            </h2>
          </div>
          <div className="rounded-2xl border border-white/[0.08] bg-bg-surface/60 p-5">
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
          <div className="rounded-2xl border border-white/[0.08] bg-bg-surface/60 p-5 overflow-x-auto">
            <ActivityHeatmap />
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

        {isLoading && (
          <p className="text-center text-[11px] text-text-muted">Refreshing…</p>
        )}
      </div>
    </PageWrapper>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-bg-surface/40 p-4">
      <p className="text-[10px] uppercase tracking-[0.15em] text-text-muted mb-1">{label}</p>
      <p className="text-xl font-semibold text-text-primary tabular-nums">{value}</p>
    </div>
  )
}
