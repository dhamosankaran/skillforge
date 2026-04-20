import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  Info,
  Star,
  ExternalLink,
  BookOpen,
  LogIn,
} from 'lucide-react'
import { getImportanceBg, getImportanceColor } from '@/utils/formatters'
import { getSkillResource } from '@/utils/skillResources'
import { capture } from '@/utils/posthog'
import type { SkillGap, GapMapping } from '@/types'
import { containerVariants, cardVariants } from '@/components/ui/AnimatedCard'

export type MissingSkillsPlan = 'anonymous' | 'free' | 'pro'

interface MissingSkillsPanelProps {
  skillGaps: SkillGap[]
  gapMappings?: GapMapping[]
  /** Three-state plan derived by the consumer from useAuth + useUsage. */
  plan: MissingSkillsPlan
  /** Current URL scan_id, used to build the anonymous `return_to` param.
   *  Source is the URL — not `result.scan_id` — per spec #22 AC-8. */
  scanId?: string | null
  /** Accepted for backwards-compat with consumers that still hold an
   *  upgrade-modal callback for other Results surfaces. Not invoked by
   *  this component — the Missing Skills CTA routes, never paywalls
   *  (spec #22 AC-5). */
  onUpgradeClick?: () => void
}

const IMPORTANCE_ICONS = {
  critical: AlertCircle,
  recommended: Star,
  'nice-to-have': Info,
}

interface CtaCopy {
  label: string
  aria: string
  Icon: typeof BookOpen
}

function ctaCopyFor(plan: MissingSkillsPlan, skill: string): CtaCopy {
  switch (plan) {
    case 'anonymous':
      return {
        label: 'Sign in to study',
        aria: `Sign in to study cards for ${skill}`,
        Icon: LogIn,
      }
    case 'pro':
      return {
        label: 'Study these cards',
        aria: `Study cards for ${skill}`,
        Icon: BookOpen,
      }
    case 'free':
    default:
      return {
        label: 'Study these cards — free preview',
        aria: `Study cards for ${skill}, free-tier preview`,
        Icon: BookOpen,
      }
  }
}

function signInReturnToUrl(scanId: string | null | undefined): string {
  const target = scanId ? `/prep/results?scan_id=${scanId}` : '/prep/results'
  return `/login?return_to=${encodeURIComponent(target)}`
}

export function MissingSkillsPanel({
  skillGaps,
  gapMappings = [],
  plan,
  scanId = null,
  onUpgradeClick: _onUpgradeClick,
}: MissingSkillsPanelProps) {
  void _onUpgradeClick // Prop retained for back-compat; CTA routes, never paywalls.
  const navigate = useNavigate()

  if (skillGaps.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <div className="w-12 h-12 rounded-full bg-success/10 border border-success/30 flex items-center justify-center mb-3">
          <Star size={20} className="text-success" />
        </div>
        <p className="text-text-primary font-medium">No skill gaps detected!</p>
        <p className="text-sm text-text-muted mt-1">Your resume covers the key requirements.</p>
      </div>
    )
  }

  // Build a lookup from gap name (lowercased) to its first matching category.
  // AC-4: only entries whose match_type !== 'none' count as matched.
  const gapCategoryMap = new Map<string, { categoryId: string; categoryName: string }>()
  for (const mapping of gapMappings) {
    if (mapping.match_type !== 'none' && mapping.matching_categories.length > 0) {
      const cat = mapping.matching_categories[0]
      gapCategoryMap.set(mapping.gap.toLowerCase(), {
        categoryId: cat.category_id,
        categoryName: cat.name,
      })
    }
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="grid grid-cols-1 sm:grid-cols-2 gap-3"
    >
      {skillGaps.map((gap) => {
        const ImportanceIcon = IMPORTANCE_ICONS[gap.importance]
        const color = getImportanceColor(gap.importance)
        const bg = getImportanceBg(gap.importance)
        const match = gapCategoryMap.get(gap.skill.toLowerCase())
        const copy = ctaCopyFor(plan, gap.skill)
        const categoryId = match ? match.categoryId : null
        const disabled = categoryId === null

        function handleClick() {
          if (disabled) return
          capture('missing_skills_cta_clicked', {
            plan,
            skill: gap.skill,
            category_id: categoryId,
          })
          if (plan === 'anonymous') {
            navigate(signInReturnToUrl(scanId))
          } else {
            navigate(`/learn?category=${categoryId}`)
          }
        }

        return (
          <motion.div
            key={gap.skill}
            variants={cardVariants}
            className="flex items-start gap-3 p-3 rounded-lg border"
            style={{
              background: bg,
              borderColor: `${color}25`,
            }}
          >
            <ImportanceIcon size={14} style={{ color, marginTop: 2, flexShrink: 0 }} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-text-primary truncate">{gap.skill}</p>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <span
                  className="text-xs px-1.5 py-0.5 rounded"
                  style={{ color, background: `${color}15` }}
                >
                  {gap.importance}
                </span>
                <span className="text-xs text-text-muted">{gap.category}</span>
                {(() => {
                  const resource = getSkillResource(gap.skill)
                  return resource ? (
                    <a
                      href={resource.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-0.5 text-xs text-accent-primary/70 hover:text-accent-primary transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <ExternalLink size={10} />
                      {resource.label}
                    </a>
                  ) : null
                })()}
              </div>
              <div className="mt-2">
                <button
                  type="button"
                  onClick={handleClick}
                  disabled={disabled}
                  aria-label={disabled ? `${gap.skill} — no matching study content yet` : copy.aria}
                  title={disabled ? 'No matching study content yet' : undefined}
                  className="flex items-center gap-1 text-xs font-medium text-accent-primary hover:text-accent-primary/80 transition-colors disabled:text-text-muted disabled:cursor-not-allowed disabled:hover:text-text-muted"
                >
                  <copy.Icon size={10} />
                  {copy.label}
                </button>
              </div>
            </div>
          </motion.div>
        )
      })}
    </motion.div>
  )
}
