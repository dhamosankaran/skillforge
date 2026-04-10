import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Target, BarChart3, GitMerge, AlertTriangle, Zap,
  MessageSquare, TrendingUp, RefreshCw, FileText,
  Brain
} from 'lucide-react'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { ATSScoreGauge } from '@/components/dashboard/ATSScoreGauge'
import { ScoreBreakdown } from '@/components/dashboard/ScoreBreakdown'
import { KeywordChart } from '@/components/dashboard/KeywordChart'
import { SkillOverlapChart } from '@/components/dashboard/SkillOverlapChart'
import { MissingSkillsPanel } from '@/components/dashboard/MissingSkillsPanel'
import { BulletAnalyzer } from '@/components/dashboard/BulletAnalyzer'
import { FormattingIssues } from '@/components/dashboard/FormattingIssues'
import { JobFitExplanation } from '@/components/dashboard/JobFitExplanation'
import { ImprovementSuggestions } from '@/components/dashboard/ImprovementSuggestions'
import { AnimatedCard, containerVariants, cardVariants } from '@/components/ui/AnimatedCard'
import { GlowButton } from '@/components/ui/GlowButton'
import { SkeletonDashboard } from '@/components/ui/SkeletonLoader'
import { useAnalysisContext } from '@/context/AnalysisContext'
import clsx from 'clsx'

interface PanelSectionProps {
  title: string
  icon: React.ElementType
  children: React.ReactNode
  className?: string
}

function PanelSection({ title, icon: Icon, children, className }: PanelSectionProps) {
  return (
    <AnimatedCard className={clsx('p-5', className)}>
      <div className="flex items-center gap-2 mb-4">
        <Icon size={14} className="text-accent-primary flex-shrink-0" />
        <h2 className="font-display font-semibold text-sm text-text-primary">{title}</h2>
      </div>
      {children}
    </AnimatedCard>
  )
}

/** Quick navigation anchors for the left sidebar */
const NAV_ITEMS = [
  { id: 'keywords', label: 'Keywords', icon: BarChart3 },
  { id: 'skills', label: 'Skills Radar', icon: GitMerge },
  { id: 'job-fit', label: 'Job Fit', icon: MessageSquare },
  { id: 'bullets', label: 'Bullets', icon: Zap },
]

export default function Results() {
  const { state } = useAnalysisContext()
  const navigate = useNavigate()
  const { result, isLoading } = state

  if (isLoading) {
    return (
      <PageWrapper className="min-h-screen bg-bg-base">
        <div className="max-w-7xl mx-auto px-4 py-12">
          <SkeletonDashboard />
        </div>
      </PageWrapper>
    )
  }

  if (!result) {
    return (
      <PageWrapper className="min-h-screen bg-bg-base">
        <div className="max-w-6xl mx-auto px-4 py-24 text-center">
          <Target size={48} className="text-text-muted mx-auto mb-4" />
          <h2 className="font-display text-2xl font-bold mb-2 text-text-primary">No Analysis Yet</h2>
          <p className="text-text-secondary mb-8">Upload your resume to see your results.</p>
          <GlowButton onClick={() => navigate('/analyze')}>
            <Zap size={14} />
            Start Analysis
          </GlowButton>
        </div>
      </PageWrapper>
    )
  }

  const scoreColor =
    result.ats_score >= 75 ? 'var(--success)' :
    result.ats_score >= 60 ? 'var(--warning)' : 'var(--danger)'

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div className="max-w-7xl mx-auto px-4 py-8">

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
            <GlowButton variant="ghost" size="sm" onClick={() => navigate('/analyze')}>
              <RefreshCw size={12} />
              Re-analyze
            </GlowButton>
<GlowButton size="sm" onClick={() => navigate('/rewrite')}>
              <FileText size={12} />
              Optimize
            </GlowButton>
          </div>
        </motion.div>

        {/* ── Three-column grid ───────────────────────────────────────── */}
        {/* xl: 3 cols | lg: 2 cols (left+main) | base: single stack */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="grid grid-cols-1 lg:grid-cols-[240px_1fr] xl:grid-cols-[240px_1fr_280px] gap-5 items-start"
        >

          {/* ── LEFT SIDEBAR ──────────────────────────────────────────── */}
          <div className="lg:sticky lg:top-20 space-y-4 z-10">
            {/* ATS Score Gauge */}
            <motion.div variants={cardVariants}>
              <AnimatedCard className="p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Target size={14} className="text-accent-primary" />
                  <h2 className="font-display font-semibold text-sm text-text-primary">ATS Score</h2>
                </div>
                <div className="flex justify-center overflow-hidden">
                  <ATSScoreGauge score={result.ats_score} grade={result.grade} />
                </div>
              </AnimatedCard>
            </motion.div>

            {/* Score breakdown */}
            <motion.div variants={cardVariants}>
              <AnimatedCard className="p-5">
                <div className="flex items-center gap-2 mb-4">
                  <BarChart3 size={14} className="text-accent-primary" />
                  <h2 className="font-display font-semibold text-sm text-text-primary">Score Breakdown</h2>
                </div>
                <ScoreBreakdown breakdown={result.score_breakdown} />
              </AnimatedCard>
            </motion.div>

            {/* Quick nav */}
            <motion.div variants={cardVariants}>
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

            {/* CTA */}
            <motion.div variants={cardVariants} className="space-y-2">
              <GlowButton
                size="sm"
                onClick={() => navigate('/rewrite')}
                className="w-full justify-center"
              >
                <Brain size={12} />
                AI Rewrite
              </GlowButton>
              <GlowButton
                variant="ghost"
                size="sm"
                onClick={() => navigate('/interview')}
                className="w-full justify-center"
              >
                <MessageSquare size={12} />
                Interview Prep
              </GlowButton>
              <GlowButton
                variant="ghost"
                size="sm"
                onClick={() => navigate('/tracker')}
                className="w-full justify-center"
              >
                Save to Tracker
              </GlowButton>
            </motion.div>
          </div>

          {/* ── MAIN PANEL ────────────────────────────────────────────── */}
          <div className="space-y-5 min-w-0">

            {/* Keywords */}
            <div id="keywords">
              <PanelSection title="Keyword Frequency Analysis" icon={BarChart3}>
                <div className="mb-3 flex items-center gap-4 text-xs text-text-muted">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-sm bg-accent-primary/70" />Matched
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-sm bg-danger/40" />Missing
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-sm bg-accent-secondary/50" />In resume
                  </span>
                </div>
                <KeywordChart data={result.keyword_chart_data} />
              </PanelSection>
            </div>

            {/* Skills radar */}
            <div id="skills">
              <PanelSection title="Skills Coverage Radar" icon={GitMerge}>
                <SkillOverlapChart data={result.skills_overlap_data} />
              </PanelSection>
            </div>

            {/* Job fit */}
            <div id="job-fit">
              <PanelSection title="Job Fit Explanation" icon={MessageSquare}>
                <JobFitExplanation
                  explanation={result.job_fit_explanation}
                  topStrengths={result.top_strengths}
                  topGaps={result.top_gaps}
                />
              </PanelSection>
            </div>

            {/* Bullet analysis */}
            <div id="bullets">
              <PanelSection title="Bullet Point Analysis" icon={Zap}>
                <BulletAnalyzer bullets={result.bullet_analysis} />
              </PanelSection>
            </div>
          </div>

          {/* ── RIGHT PANEL ───────────────────────────────────────────── */}
          {/* Shown inline below main on lg, pinned to right column on xl */}
          <div className="xl:sticky xl:top-20 space-y-4 lg:col-span-2 xl:col-span-1 z-10">

            {/* Missing skills */}
            <PanelSection title="Missing Skills" icon={TrendingUp}>
              <MissingSkillsPanel skillGaps={result.skill_gaps} />
            </PanelSection>

            {/* Formatting issues */}
            <PanelSection title="ATS Formatting Issues" icon={AlertTriangle}>
              <FormattingIssues issues={result.formatting_issues} />
            </PanelSection>

            {/* Improvement suggestions */}
            <PanelSection title="Improvement Suggestions" icon={TrendingUp}>
              <ImprovementSuggestions
                missingKeywords={result.missing_keywords}
                skillGaps={result.skill_gaps}
              />
            </PanelSection>

          </div>
        </motion.div>
      </div>
    </PageWrapper>
  )
}
