import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Target, Flame, Users } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { completeOnboarding } from '@/services/api'
import { capture } from '@/utils/posthog'

type Persona = 'interview' | 'climber' | 'team'

const personas = [
  {
    id: 'interview' as Persona,
    icon: Target,
    title: 'I have an interview coming up',
    desc: 'Get a personalized study plan with a countdown to your target date.',
    color: 'var(--sf-accent-primary)',
  },
  {
    id: 'climber' as Persona,
    icon: Flame,
    title: 'I want to stay sharp',
    desc: 'Build a daily review habit with spaced repetition.',
    color: 'var(--sf-accent-secondary)',
  },
  {
    id: 'team' as Persona,
    icon: Users,
    title: "I'm exploring for my team",
    desc: 'Browse all categories and see what SkillForge offers.',
    color: 'var(--sf-accent-warm)',
  },
] as const

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
}

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
}

export default function PersonaPicker() {
  const { updateUser } = useAuth()
  const navigate = useNavigate()
  const [selected, setSelected] = useState<Persona | null>(null)
  const [targetCompany, setTargetCompany] = useState('')
  const [targetDate, setTargetDate] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit() {
    if (!selected || submitting) return
    setSubmitting(true)

    try {
      const res = await completeOnboarding({
        persona: selected,
        ...(selected === 'interview' && targetCompany ? { target_company: targetCompany } : {}),
        ...(selected === 'interview' && targetDate ? { target_date: targetDate } : {}),
      })

      capture('onboarding_persona_selected', { persona: selected })
      updateUser({ persona: res.persona as Persona, onboarding_completed: true })

      if (selected === 'interview') {
        const params = new URLSearchParams()
        if (targetCompany) params.set('company', targetCompany)
        if (targetDate) params.set('date', targetDate)
        const qs = params.toString()
        navigate(`/mission${qs ? `?${qs}` : ''}`, { replace: true })
      } else if (selected === 'climber') {
        navigate('/study/daily', { replace: true })
      } else {
        navigate('/study', { replace: true })
      }
    } catch {
      setSubmitting(false)
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 200,
        background: 'var(--sf-bg-primary)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <motion.div
        initial="hidden"
        animate="visible"
        variants={stagger}
        style={{ maxWidth: 520, width: '100%' }}
      >
        <motion.div variants={fadeUp} style={{ textAlign: 'center', marginBottom: 40 }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 12,
              background: 'var(--sf-gradient-cta)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 18,
              fontWeight: 700,
              color: 'var(--sf-text-on-accent)',
              marginBottom: 20,
            }}
          >
            S
          </div>
          <h1
            style={{
              fontSize: 'clamp(24px, 4vw, 32px)',
              fontWeight: 800,
              fontFamily: 'var(--sf-font-display)',
              letterSpacing: '-0.03em',
              margin: '0 0 8px',
            }}
          >
            What brings you here?
          </h1>
          <p style={{ color: 'var(--sf-text-secondary)', fontSize: 15 }}>
            We'll tailor your experience based on your goal.
          </p>
        </motion.div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {personas.map((p) => {
            const Icon = p.icon
            const isSelected = selected === p.id
            return (
              <motion.button
                key={p.id}
                variants={fadeUp}
                onClick={() => setSelected(p.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 16,
                  padding: '20px 20px',
                  borderRadius: 'var(--sf-radius-lg)',
                  border: `2px solid ${isSelected ? p.color : 'var(--sf-border-subtle)'}`,
                  background: isSelected ? `${p.color}10` : 'var(--sf-bg-tertiary)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 200ms ease',
                  width: '100%',
                  color: 'inherit',
                  fontFamily: 'inherit',
                }}
              >
                <div
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: 'var(--sf-radius-md)',
                    background: `${p.color}15`,
                    border: `1px solid ${p.color}30`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: p.color,
                    flexShrink: 0,
                  }}
                >
                  <Icon size={22} />
                </div>
                <div>
                  <div
                    style={{
                      fontWeight: 700,
                      fontSize: 15,
                      fontFamily: 'var(--sf-font-display)',
                      marginBottom: 2,
                    }}
                  >
                    {p.title}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--sf-text-secondary)' }}>
                    {p.desc}
                  </div>
                </div>
              </motion.button>
            )
          })}
        </div>

        {/* Interview extras — shown only when "interview" is selected */}
        {selected === 'interview' && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            transition={{ duration: 0.3 }}
            style={{
              marginTop: 16,
              padding: '20px',
              borderRadius: 'var(--sf-radius-lg)',
              border: '1px solid var(--sf-border-subtle)',
              background: 'var(--sf-bg-tertiary)',
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            <div>
              <label
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: 'var(--sf-text-secondary)',
                  display: 'block',
                  marginBottom: 6,
                }}
              >
                Target company (optional)
              </label>
              <input
                type="text"
                placeholder="e.g. Google"
                value={targetCompany}
                onChange={(e) => setTargetCompany(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 'var(--sf-radius-md)',
                  border: '1px solid var(--sf-border-subtle)',
                  background: 'var(--sf-bg-primary)',
                  color: 'var(--sf-text-primary)',
                  fontSize: 14,
                  fontFamily: 'inherit',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>
            <div>
              <label
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: 'var(--sf-text-secondary)',
                  display: 'block',
                  marginBottom: 6,
                }}
              >
                Interview date (optional)
              </label>
              <input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 'var(--sf-radius-md)',
                  border: '1px solid var(--sf-border-subtle)',
                  background: 'var(--sf-bg-primary)',
                  color: 'var(--sf-text-primary)',
                  fontSize: 14,
                  fontFamily: 'inherit',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>
          </motion.div>
        )}

        <motion.div variants={fadeUp} style={{ marginTop: 24 }}>
          <button
            onClick={handleSubmit}
            disabled={!selected || submitting}
            className="sf-btn-primary"
            style={{
              width: '100%',
              padding: '14px 24px',
              fontSize: 15,
              cursor: selected && !submitting ? 'pointer' : 'not-allowed',
              opacity: selected && !submitting ? 1 : 0.5,
            }}
          >
            {submitting ? 'Setting up...' : 'Continue'}
          </button>
        </motion.div>
      </motion.div>
    </div>
  )
}
