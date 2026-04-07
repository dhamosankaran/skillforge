import { motion } from 'framer-motion'
// Icons available for future use
import type { SkillGap } from '@/types'

interface ImprovementSuggestionsProps {
  missingKeywords: string[]
  skillGaps: SkillGap[]
}

export function ImprovementSuggestions({
  missingKeywords,
  skillGaps,
}: ImprovementSuggestionsProps) {
  const criticalSkills = skillGaps.filter((g) => g.importance === 'critical')

  const suggestions = [
    ...(criticalSkills.length > 0
      ? [
          {
            title: 'Add critical missing skills',
            description: `Incorporate these skills naturally into your experience bullets or skills section: ${criticalSkills
              .slice(0, 5)
              .map((s) => s.skill)
              .join(', ')}`,
            priority: 'high',
          },
        ]
      : []),
    ...(missingKeywords.length > 0
      ? [
          {
            title: 'Boost keyword density',
            description: `Include these missing JD keywords in your resume: ${missingKeywords.slice(0, 6).join(', ')}`,
            priority: 'high',
          },
        ]
      : []),
    {
      title: 'Quantify your achievements',
      description:
        'Add specific metrics to your bullet points — percentages, dollar amounts, team sizes, or timeframes demonstrate real impact.',
      priority: 'medium',
    },
    {
      title: 'Optimize section headers',
      description:
        'Use standard section headers (Experience, Education, Skills) to ensure ATS systems parse your resume correctly.',
      priority: 'medium',
    },
    {
      title: 'Use strong action verbs',
      description:
        'Start each bullet with an impact verb like Led, Built, Increased, Deployed, or Architected to communicate ownership.',
      priority: 'low',
    },
  ]

  const priorityColors = {
    high: '#f85149',
    medium: '#f0a500',
    low: '#8b949e',
  }

  return (
    <div className="space-y-3">
      {suggestions.map((suggestion, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.07 }}
          className="flex gap-3 p-4 rounded-xl bg-bg-elevated border border-white/[0.06]"
        >
          <div
            className="w-1 flex-shrink-0 rounded-full"
            style={{ background: priorityColors[suggestion.priority as keyof typeof priorityColors] }}
          />
          <div>
            <p className="text-sm font-medium text-text-primary mb-1">{suggestion.title}</p>
            <p className="text-xs text-text-secondary leading-relaxed">{suggestion.description}</p>
          </div>
        </motion.div>
      ))}
    </div>
  )
}
