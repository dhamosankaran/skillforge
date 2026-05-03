import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Target, BarChart3, GitMerge, AlertTriangle, Zap,
  MessageSquare, TrendingUp, RefreshCw, FileText,
  Brain, CheckCircle2, Clock
} from 'lucide-react'
import toast from 'react-hot-toast'
import axios from 'axios'
import { fetchOnboardingRecommendations, fetchScanById } from '@/services/api'
import { PaywallModal, type PaywallTrigger } from '@/components/PaywallModal'
import { useAuth } from '@/context/AuthContext'
import { useUsage } from '@/context/UsageContext'
import type { MissingSkillsPlan } from '@/components/dashboard/MissingSkillsPanel'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { ATSScoreGauge } from '@/components/dashboard/ATSScoreGauge'
import { ScoreBreakdown } from '@/components/dashboard/ScoreBreakdown'
import { KeywordChart, KEYWORD_LEGEND, rgbaFromCssVar } from '@/components/dashboard/KeywordChart'
import { SkillOverlapChart } from '@/components/dashboard/SkillOverlapChart'
import { MissingSkillsPanel } from '@/components/dashboard/MissingSkillsPanel'
import { BulletAnalyzer } from '@/components/dashboard/BulletAnalyzer'
import { FormattingIssues } from '@/components/dashboard/FormattingIssues'
import { JobFitExplanation } from '@/components/dashboard/JobFitExplanation'
import { ImprovementSuggestions } from '@/components/dashboard/ImprovementSuggestions'
import { PanelSection } from '@/components/dashboard/PanelSection'
import { LoopFrame } from '@/components/dashboard/LoopFrame'
import { AnimatedCard, containerVariants, cardVariants } from '@/components/ui/AnimatedCard'
import { GlowButton } from '@/components/ui/GlowButton'
import { SkeletonDashboard } from '@/components/ui/SkeletonLoader'
import { useAnalysisContext } from '@/context/AnalysisContext'
import { useHomeState } from '@/hooks/useHomeState'
import { capture } from '@/utils/posthog'

/** Quick navigation anchors for the left sidebar */
const NAV_ITEMS = [
  { id: 'job-fit', label: 'Job Fit', icon: MessageSquare },
  { id: 'keywords', label: 'Keywords', icon: BarChart3 },
  { id: 'skills', label: 'Skills Radar', icon: GitMerge },
  { id: 'bullets', label: 'Bullets', icon: Zap },
]

/** Spec #59 — three-way empty-state signal for Results. `idle` is "no
 *  URL scan_id, nothing to hydrate." `fetching` drives the skeleton.
 *  `success` means AnalysisContext is now populated (the render path
 *  drops out of the empty-state branch). `legacy` / `not_found` /
 *  `error` select distinct empty-state copy. */
type HydrateStatus =
  | 'idle'
  | 'fetching'
  | 'success'
  | 'legacy'
  | 'not_found'
  | 'error'

export default function Results() {
  const { state, dispatch } = useAnalysisContext()
  const navigate = useNavigate()
  const { canUsePro } = useUsage()
  const { user } = useAuth()
  const homeState = useHomeState()
  const [searchParams] = useSearchParams()
  const { result, isLoading } = state
  const toastShownRef = useRef<string | null>(null)
  const jobFitViewedRef = useRef(false)
  const [showPaywall, setShowPaywall] = useState(false)
  const [paywallTrigger, setPaywallTrigger] = useState<PaywallTrigger>('scan_limit')
  const [gapMappings, setGapMappings] = useState<import('@/types').GapMapping[]>([])
  const [hydrateStatus, setHydrateStatus] = useState<HydrateStatus>('idle')

  // Spec #55 — gate Re-analyze on plan. Free users hit the existing
  // PaywallModal with `scan_limit` trigger; Pro users flow through to
  // /prep/analyze. `re_analyze_clicked` fires regardless so both
  // branches are measurable.
  const handleReanalyzeClick = () => {
    capture('re_analyze_clicked', { plan: canUsePro ? 'pro' : 'free' })
    if (!canUsePro) {
      setPaywallTrigger('scan_limit')
      setShowPaywall(true)
      return
    }
    navigate('/prep/analyze')
  }

  // B-032 — gate Optimize / AI Rewrite on plan. Mirrors handleReanalyzeClick
  // shape. Both the header "Optimize" button and the sidebar "AI Rewrite"
  // CTA wire to this single handler so their behavior cannot diverge.
  const handleOptimizeClick = () => {
    capture('optimize_clicked', { plan: canUsePro ? 'pro' : 'free' })
    if (!canUsePro) {
      setPaywallTrigger('rewrite_limit')
      setShowPaywall(true)
      return
    }
    navigate('/prep/rewrite')
  }

  // Three-state plan for the Missing Skills CTA (spec #22 §Plan Detection).
  // Composed from the two live plan-surfaces — `AuthContext.user` signals
  // anonymity, `UsageContext.canUsePro` signals pro. `AuthUser` has no
  // `subscription` field on the frontend, so the spec's `user.subscription?.plan`
  // wording is satisfied via the existing `canUsePro` derivation.
  const missingSkillsPlan: MissingSkillsPlan =
    user === null ? 'anonymous' : canUsePro ? 'pro' : 'free'
  // AC-8: `return_to` is derived from the URL's scan_id, not from result state.
  const urlScanId = searchParams.get('scan_id')

  // Spec #59 — hydrate AnalysisContext from URL scan_id when the page
  // is reached on a fresh session (result === null). Fires once per
  // URL via the `hydrateStatus !== 'idle'` idempotency guard. Three
  // distinct empty-state branches key off the final status:
  //   success  → dispatch populates result; dashboard renders
  //   legacy   → 410; scan pre-dates persistence
  //   not_found → 404; unknown / non-owner (LD-4 no-leak)
  //   error    → network / 5xx; retryable
  useEffect(() => {
    if (result || !urlScanId || hydrateStatus !== 'idle') return
    setHydrateStatus('fetching')
    fetchScanById(urlScanId)
      .then((payload) => {
        dispatch({ type: 'SET_RESULT', payload })
        setHydrateStatus('success')
        capture('scan_rehydrated', { scan_id: urlScanId })
      })
      .catch((err) => {
        const status = axios.isAxiosError(err) ? err.response?.status : undefined
        const next: HydrateStatus =
          status === 410 ? 'legacy'
            : status === 404 ? 'not_found'
              : 'error'
        setHydrateStatus(next)
        capture('scan_rehydrate_failed', {
          scan_id: urlScanId,
          reason: next,
          http_status: status ?? 0,
        })
      })
  }, [result, urlScanId, hydrateStatus, dispatch])

  // Fetch gap-to-category mappings when results load
  useEffect(() => {
    if (!result?.skill_gaps?.length) return
    const gaps = result.skill_gaps.map((g) => g.skill)
    fetchOnboardingRecommendations(gaps, result.scan_id)
      .then((res) => setGapMappings(res.results))
      .catch(() => {})
  }, [result?.skill_gaps, result?.scan_id])

  // Fire job-fit-viewed once per mount. Matches home_dashboard_viewed /
  // first_action_viewed convention — useRef idempotency guard so Strict Mode
  // double-invoke captures once. view_position distinguishes this from a
  // future below-fold or scroll-triggered variant.
  useEffect(() => {
    if (!result || jobFitViewedRef.current) return
    jobFitViewedRef.current = true
    capture('job_fit_explanation_viewed', { view_position: 'above_fold' })
  }, [result])

  // Show toast when scan results load (auto-created tracker entry)
  useEffect(() => {
    if (!result?.scan_id || toastShownRef.current === result.scan_id) return
    toastShownRef.current = result.scan_id
    toast.success(
      (t) => (
        <span className="flex items-center gap-2 text-sm">
          <CheckCircle2 size={14} className="text-green-400 shrink-0" />
          Added to your Job Tracker
          <button
            onClick={() => { toast.dismiss(t.id); navigate('/prep/tracker') }}
            className="ml-1 underline text-accent-primary hover:text-accent-primary/80"
          >
            View
          </button>
        </span>
      ),
      { duration: 5000 },
    )
  }, [result?.scan_id, navigate])

  if (isLoading || hydrateStatus === 'fetching') {
    return (
      <PageWrapper className="min-h-screen bg-bg-base">
        <div className="max-w-7xl mx-auto px-4 py-12">
          <SkeletonDashboard />
        </div>
      </PageWrapper>
    )
  }

  if (!result) {
    // Spec #59 — three-way empty-state copy switch. `legacy` is a scan
    // that exists but predates payload persistence; `not_found` is the
    // generic "no scan / wrong user" case (LD-4 — no existence leak);
    // `error` is a retryable network / 5xx.
    const emptyCopy =
      hydrateStatus === 'legacy'
        ? {
            icon: Clock,
            heading: 'Results Not Available',
            body: 'This scan is from before we stored full results — re-scan to view.',
            cta: 'Re-scan resume',
            onCta: () => navigate('/prep/analyze'),
          }
        : hydrateStatus === 'error'
          ? {
              icon: AlertTriangle,
              heading: "Couldn't Load Results",
              body: 'We hit a snag fetching your scan. Try again in a moment.',
              cta: 'Retry',
              onCta: () => setHydrateStatus('idle'),
            }
          : {
              // 'not_found' and 'idle' (no scan_id at all) share the same copy —
              // both point the user at starting a new analysis.
              icon: Target,
              heading: 'No Analysis Yet',
              body: 'Upload your resume to see your results.',
              cta: 'Start Analysis',
              onCta: () => navigate('/prep/analyze'),
            }
    const Icon = emptyCopy.icon
    return (
      <PageWrapper className="min-h-screen bg-bg-base">
        <div
          data-testid={`results-empty-${hydrateStatus}`}
          className="max-w-6xl mx-auto px-4 py-24 text-center"
        >
          <Icon size={48} className="text-text-muted mx-auto mb-4" />
          <h2 className="font-display text-2xl font-bold mb-2 text-text-primary">
            {emptyCopy.heading}
          </h2>
          <p className="text-text-secondary mb-8">{emptyCopy.body}</p>
          <GlowButton onClick={emptyCopy.onCta}>
            <Zap size={14} />
            {emptyCopy.cta}
          </GlowButton>
        </div>
      </PageWrapper>
    )
  }

  const scoreColor =
    result.ats_score >= 75 ? 'var(--success)' :
    result.ats_score >= 60 ? 'var(--warning)' : 'var(--danger)'

  const hasKeywordData = (result.keyword_chart_data?.length ?? 0) > 0

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div data-testid="page-results" className="max-w-7xl mx-auto px-4 py-8">

        {/* Page header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6"
        >
          <div>
            <h1 className="font-display text-2xl font-bold text-text-primary">Analysis Results</h1>
            <p className="text-text-secondary text-sm mt-0.5">
              Scored{' '}
              <span className="font-mono font-semibold" style={{ color: scoreColor }}>
                {result.ats_score}/100 · {result.grade}
              </span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <GlowButton variant="ghost" size="sm" onClick={handleReanalyzeClick}>
              <RefreshCw size={12} />
              Re-analyze
            </GlowButton>
            <GlowButton size="sm" onClick={handleOptimizeClick}>
              <FileText size={12} />
              Optimize
            </GlowButton>
          </div>
        </motion.div>

        {/* Spec #64 — static loop frame visualizing the closed loop
            (Scanned → Studying → Re-scan → Interview). Mounted ABOVE the
            dashboard grid (not as a 12th grid child) to avoid cascading
            row-start shifts on the spec #21 / E-009 11-child placement
            map; outcome ("frame above missing skills") is identical and
            spec #21 / spec #22 regression set stays untouched. */}
        {result.ats_score != null && (
          <LoopFrame
            surface="results"
            currentStep={1}
            score={result.ats_score}
            gapCount={result.skill_gaps?.length ?? 0}
            interviewDate={homeState.data?.context.next_interview?.date ?? null}
            plan={missingSkillsPlan}
          />
        )}

        {/* Flattened grid: DOM order IS the mobile / tab order.
            Desktop layout reconstructed via explicit col-start / row-start.
            - base (<lg):  1-col, DOM order = visual order
            - lg (2-col):  [sidebar 240px | main 1fr], right-panel rows span both cols below
            - xl (3-col):  [sidebar 240px | main 1fr | right 280px] */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="grid grid-cols-1 lg:grid-cols-[240px_1fr] xl:grid-cols-[240px_1fr_280px] gap-5 items-start"
        >

          {/* 1. ATS Score — mobile 1st · lg/xl col-1 row-1 */}
          <motion.div
            variants={cardVariants}
            id="ats-score"
            className="lg:col-start-1 lg:row-start-1"
          >
            <PanelSection
              title="ATS Score"
              icon={Target}
              section="ats_score"
              tooltip={{
                what: 'Estimated resume-to-JD match strength, 0–100.',
                how: 'Aim for 75+ before applying; under 60 needs rewrite.',
                why: 'Filters auto-reject below a recruiter-set cutoff, often 70.',
              }}
            >
              <div className="flex justify-center overflow-hidden">
                <ATSScoreGauge score={result.ats_score} grade={result.grade} />
              </div>
            </PanelSection>
          </motion.div>

          {/* 2. Job Fit — mobile 2nd · lg/xl col-2 row-1 HERO */}
          <motion.div
            variants={cardVariants}
            id="job-fit"
            className="min-w-0 lg:col-start-2 lg:row-start-1"
          >
            <PanelSection
              title="Job Fit Explanation"
              icon={MessageSquare}
              section="job_fit"
              tooltip={{
                what: 'AI summary of how your experience maps to the role.',
                how: 'Read the gaps list; reframe bullets to cover them.',
                why: 'Recruiters skim this exact framing in their first 10 seconds.',
              }}
            >
              <JobFitExplanation
                explanation={result.job_fit_explanation}
                topStrengths={result.top_strengths}
                topGaps={result.top_gaps}
              />
            </PanelSection>
          </motion.div>

          {/* 3. Missing Skills — mobile 3rd · lg spans both cols at row-5 · xl col-3 row-1 */}
          <motion.div
            variants={cardVariants}
            id="missing-skills"
            className="lg:col-span-2 lg:col-start-1 lg:row-start-5 xl:col-start-3 xl:col-span-1 xl:row-start-1"
          >
            <PanelSection
              title="Missing Skills"
              icon={TrendingUp}
              section="missing_skills"
              tooltip={{
                what: 'JD skills not found in your resume.',
                how: 'Either add if you have them, or study via flashcards.',
                why: 'Unaddressed gaps are the fastest reason to skip an application.',
              }}
            >
              <MissingSkillsPanel
                skillGaps={result.skill_gaps}
                gapMappings={gapMappings}
                plan={missingSkillsPlan}
                scanId={urlScanId}
              />
            </PanelSection>
          </motion.div>

          {/* 4. Keywords — mobile 4th · lg/xl col-2 row-2 */}
          <motion.div
            variants={cardVariants}
            id="keywords"
            className="min-w-0 lg:col-start-2 lg:row-start-2"
          >
            <PanelSection
              title="Keyword Frequency Analysis"
              icon={BarChart3}
              section="keywords"
              tooltip={{
                what: 'Which JD keywords appear in your resume vs. don\'t.',
                how: 'Add missing keywords where the evidence supports it.',
                why: 'ATS keyword-match drives the biggest single score component.',
              }}
            >
              {hasKeywordData && (
                <div className="mb-3 flex items-center gap-4 text-xs text-text-muted">
                  {KEYWORD_LEGEND.map((entry) => (
                    <span key={entry.id} className="flex items-center gap-1.5">
                      <span
                        data-testid={`legend-swatch-${entry.id}`}
                        className="w-2 h-2 rounded-sm"
                        style={{ backgroundColor: rgbaFromCssVar(entry.cssVarName, entry.alpha) }}
                      />
                      {entry.label}
                    </span>
                  ))}
                </div>
              )}
              <KeywordChart data={result.keyword_chart_data} />
            </PanelSection>
          </motion.div>

          {/* 5. Score Breakdown — mobile 5th · lg/xl col-1 row-2 */}
          <motion.div
            variants={cardVariants}
            id="score-breakdown"
            className="lg:col-start-1 lg:row-start-2"
          >
            <PanelSection
              title="Score Breakdown"
              icon={BarChart3}
              section="score_breakdown"
              tooltip={{
                what: 'Which dimensions (keywords, skills, format) drove your score.',
                how: 'Target the lowest bar first; biggest score gain per edit.',
                why: 'Shows why your score is what it is, not just the number.',
              }}
            >
              <ScoreBreakdown breakdown={result.score_breakdown} />
            </PanelSection>
          </motion.div>

          {/* 6. Skills Radar — mobile 6th · lg/xl col-2 row-3 */}
          <motion.div
            variants={cardVariants}
            id="skills"
            className="min-w-0 lg:col-start-2 lg:row-start-3"
          >
            <PanelSection
              title="Skills Coverage Radar"
              icon={GitMerge}
              section="skills_radar"
              tooltip={{
                what: 'Visual overlap between your skills and JD requirements.',
                how: 'Close gaps on axes where JD demand is high.',
                why: 'Spots category-level holes that bullet-level edits miss.',
              }}
            >
              <SkillOverlapChart data={result.skills_overlap_data} />
            </PanelSection>
          </motion.div>

          {/* 7. Bullets — mobile 7th · lg/xl col-2 row-4 */}
          <motion.div
            variants={cardVariants}
            id="bullets"
            className="min-w-0 lg:col-start-2 lg:row-start-4"
          >
            <PanelSection
              title="Bullet Point Analysis"
              icon={Zap}
              section="bullets"
              tooltip={{
                what: 'Which bullets are weak (no metrics, weak verbs).',
                how: 'Rewrite flagged bullets with numbers and outcome verbs.',
                why: 'Strong bullets are the #1 driver of human screener yes/no.',
              }}
            >
              <BulletAnalyzer bullets={result.bullet_analysis} />
            </PanelSection>
          </motion.div>

          {/* 8. Formatting — mobile 8th · lg spans both cols at row-6 · xl col-3 row-2 */}
          <motion.div
            variants={cardVariants}
            id="formatting"
            className="lg:col-span-2 lg:col-start-1 lg:row-start-6 xl:col-start-3 xl:col-span-1 xl:row-start-2"
          >
            <PanelSection
              title="ATS Formatting Issues"
              icon={AlertTriangle}
              section="formatting"
              tooltip={{
                what: 'Structural problems (tables, images, headers).',
                how: 'Fix before re-scanning; some ATSes drop formatted content entirely.',
                why: 'One table can cost you the whole scan, not just a section.',
              }}
            >
              <FormattingIssues issues={result.formatting_issues} />
            </PanelSection>
          </motion.div>

          {/* 9. Improvements — mobile 9th · lg spans both cols at row-7 · xl col-3 rows 3-4.
              B-055: spans 2 grid-rows at xl so its height (3-5 stacked recommendation
              cards) distributes across rows 3-4 of col-3 instead of inflating row-3
              alone — without this, row-3's auto height = max(Jump-nav, Skills Radar,
              Improvements) = Improvements, leaving a void below Skills Radar and
              Jump-nav before row-4 (Bullets / CTAs) starts. */}
          <motion.div
            variants={cardVariants}
            id="improvements"
            className="lg:col-span-2 lg:col-start-1 lg:row-start-7 xl:col-start-3 xl:col-span-1 xl:row-start-3 xl:row-end-5"
          >
            <PanelSection
              title="Improvement Suggestions"
              icon={TrendingUp}
              section="improvements"
              tooltip={{
                what: 'Prioritized concrete edits to lift your score.',
                how: 'Work top-to-bottom; highest-leverage first.',
                why: 'Saves you guessing what to fix next.',
              }}
            >
              <ImprovementSuggestions
                missingKeywords={result.missing_keywords}
                skillGaps={result.skill_gaps}
              />
            </PanelSection>
          </motion.div>

          {/* Jump-to-section nav — mobile 10th · lg/xl col-1 row-3 */}
          <motion.div variants={cardVariants} className="lg:col-start-1 lg:row-start-3">
            <AnimatedCard className="p-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted px-2 mb-2">
                Jump to section
              </p>
              {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })}
                  className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[13px] text-text-muted hover:text-text-primary hover:bg-contrast/[0.04] transition-all text-left"
                >
                  <Icon size={12} />
                  {label}
                </button>
              ))}
            </AnimatedCard>
          </motion.div>

          {/* CTAs — mobile 11th · lg/xl col-1 row-4 */}
          <motion.div
            variants={cardVariants}
            className="space-y-2 lg:col-start-1 lg:row-start-4"
          >
            <GlowButton
              size="sm"
              onClick={handleOptimizeClick}
              className="w-full justify-center"
            >
              <Brain size={12} />
              AI Rewrite
            </GlowButton>
            <GlowButton
              variant="ghost"
              size="sm"
              onClick={() => navigate('/prep/interview')}
              className="w-full justify-center"
            >
              <MessageSquare size={12} />
              Interview Prep
            </GlowButton>
            <GlowButton
              variant="ghost"
              size="sm"
              onClick={() => navigate('/prep/tracker')}
              className="w-full justify-center"
            >
              {result.scan_id ? (
                <>
                  <CheckCircle2 size={12} className="text-green-400" />
                  In Tracker — View
                </>
              ) : (
                'Save to Tracker'
              )}
            </GlowButton>
          </motion.div>
        </motion.div>
      </div>

      <PaywallModal
        open={showPaywall}
        onClose={() => setShowPaywall(false)}
        trigger={paywallTrigger}
      />
    </PageWrapper>
  )
}
