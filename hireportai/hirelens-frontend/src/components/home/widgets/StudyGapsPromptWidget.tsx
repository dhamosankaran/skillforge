import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { useUsage } from '@/context/UsageContext'
import { fetchActiveMission, fetchUserApplications } from '@/services/api'
import { capture } from '@/utils/posthog'
import type { TrackerApplication } from '@/types'

/**
 * Spec #61 §4 — free-tier scan→study/upgrade surface.
 *
 * Renders for `plan === 'free' && !isAdmin && has_recent_scan && !has_active_mission`.
 * Closes audit findings #3 (LastScan buried), #4 (no on-home study CTA),
 * #5 (no upgrade-to-study CTA). When this widget renders, HomeDashboard
 * suppresses LastScanWidget from the static persona grid (spec §4.1) —
 * scan content is rolled into this widget's body.
 *
 * Primary CTA: free-path study entry. Secondary CTA: subordinate upgrade
 * link per LD-1 (premature conversion pressure on a user who hasn't
 * experienced Forge yet is the wrong moment).
 */

const PRIMARY_CTA_TARGET = '/learn?source=last_scan'

interface StudyGapsPromptWidgetProps {
  /**
   * When true, the widget renders synchronously into a hidden state and
   * does not run its async predicate fetches. HomeDashboard sets this
   * when an upstream gate (e.g., active state-slot widget) makes the
   * prompt irrelevant. Default false.
   */
  suppressed?: boolean
}

export function StudyGapsPromptWidget({
  suppressed = false,
}: StudyGapsPromptWidgetProps) {
  const { user } = useAuth()
  const { usage, setShowUpgradeModal } = useUsage()
  const plan = usage.plan
  const isAdmin = usage.isAdmin
  const [hasRecentScan, setHasRecentScan] = useState<boolean | null>(null)
  const [hasActiveMission, setHasActiveMission] = useState<boolean | null>(null)
  const [latest, setLatest] = useState<TrackerApplication | null>(null)
  const shownRef = useRef(false)

  // Eligibility predicates per spec §4.1. Free + non-admin gate is sync
  // (from context); recent-scan + no-active-mission gates are async.
  const planEligible = plan === 'free' && !isAdmin

  useEffect(() => {
    if (suppressed || !planEligible) return
    let cancelled = false
    fetchUserApplications()
      .then((apps) => {
        if (cancelled) return
        if (apps.length === 0) {
          setHasRecentScan(false)
          setLatest(null)
          return
        }
        const sorted = [...apps].sort((a, b) =>
          (b.created_at ?? '').localeCompare(a.created_at ?? ''),
        )
        setLatest(sorted[0])
        setHasRecentScan(true)
      })
      .catch(() => {
        if (cancelled) return
        setHasRecentScan(false)
      })
    return () => {
      cancelled = true
    }
  }, [suppressed, planEligible])

  useEffect(() => {
    if (suppressed || !planEligible) return
    let cancelled = false
    fetchActiveMission()
      .then((m) => {
        if (cancelled) return
        setHasActiveMission(m?.status === 'active')
      })
      .catch(() => {
        if (cancelled) return
        setHasActiveMission(false)
      })
    return () => {
      cancelled = true
    }
  }, [suppressed, planEligible])

  const eligible =
    !suppressed &&
    planEligible &&
    hasRecentScan === true &&
    hasActiveMission === false

  // Fire shown event once per mount when eligibility resolves true.
  useEffect(() => {
    if (!eligible) return
    if (shownRef.current) return
    shownRef.current = true
    capture('home_study_gaps_prompt_shown', {
      plan,
      persona: user?.persona ?? null,
    })
  }, [eligible, plan, user?.persona])

  if (!eligible) return null

  const company = latest?.company ?? 'your last role'
  const skillsMissing = latest?.skills_missing ?? null
  const gapCount = Array.isArray(skillsMissing) && skillsMissing.length > 0
    ? skillsMissing.length
    : null
  const body =
    gapCount !== null
      ? `Your last scan against ${company} found ${gapCount} skill gap${gapCount === 1 ? '' : 's'}. Study them in 5 minutes a day.`
      : `Pick up your last scan against ${company} and study the gaps in 5 minutes a day.`

  function handlePrimaryClick() {
    capture('home_study_gaps_clicked', {
      plan,
      persona: user?.persona ?? null,
      cta: 'primary',
    })
  }

  function handleSecondaryClick(e: React.MouseEvent<HTMLAnchorElement>) {
    e.preventDefault()
    capture('home_study_gaps_clicked', {
      plan,
      persona: user?.persona ?? null,
      cta: 'secondary_upgrade',
    })
    setShowUpgradeModal(true)
  }

  return (
    <section
      data-testid="study-gaps-prompt"
      className="mb-6 rounded-xl border border-border-accent bg-bg-surface p-6 shadow-sm"
    >
      <h2 className="font-display text-lg font-semibold text-text-primary mb-2">
        Pick up where you left off
      </h2>
      <p className="text-sm text-text-secondary mb-4">{body}</p>
      <div className="flex flex-col gap-2 items-start">
        <Link
          to={PRIMARY_CTA_TARGET}
          onClick={handlePrimaryClick}
          data-testid="study-gaps-prompt-primary"
          className="inline-flex items-center px-4 py-2 rounded-md bg-accent-primary text-white text-sm font-medium hover:bg-accent-primary/90 transition-colors"
        >
          Study the gaps from your last scan
        </Link>
        <a
          href="#upgrade"
          onClick={handleSecondaryClick}
          data-testid="study-gaps-prompt-secondary"
          data-emphasis="secondary"
          className="text-xs text-text-secondary underline-offset-2 hover:underline"
        >
          Or upgrade to unlock unlimited study + Pro features
        </a>
      </div>
    </section>
  )
}
