import { useEffect, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { motion, useScroll, useTransform, useInView, useMotionValue, useSpring } from 'framer-motion'
import { ArrowRight, CheckCircle, Zap, Target, Brain, BarChart3, FileText, Shield } from 'lucide-react'
import { PageWrapper } from '@/components/layout/PageWrapper'

// ─── Animated counter triggered on scroll into view ───
function AnimatedCounter({ end, suffix = '+', label }: { end: number; suffix?: string; label: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const numRef = useRef<HTMLSpanElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-80px' })

  useEffect(() => {
    if (!isInView) return
    const el = numRef.current
    if (!el) return
    let start = 0
    const step = Math.ceil(end / (1400 / 16))
    const timer = setInterval(() => {
      start = Math.min(start + step, end)
      el.textContent = start.toLocaleString()
      if (start >= end) clearInterval(timer)
    }, 16)
    return () => clearInterval(timer)
  }, [isInView, end])

  return (
    <div ref={ref}>
      <div className="flex items-end gap-0.5 mb-1">
        <span
          ref={numRef}
          className="font-editorial text-5xl lg:text-6xl leading-none"
          style={{
            background: 'linear-gradient(135deg, #FAFAFA 0%, #A3A3A3 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          0
        </span>
        <span
          className="font-editorial text-3xl pb-1 leading-none shimmer-text"
        >
          {suffix}
        </span>
      </div>
      <p className="text-[11px] tracking-[0.18em] uppercase text-text-muted">{label}</p>
    </div>
  )
}

// ─── Seamless marquee ───
function Marquee({ items }: { items: string[] }) {
  const doubled = [...items, ...items]
  return (
    <div className="relative overflow-hidden py-5 border-y border-white/[0.04]">
      <div className="absolute inset-y-0 left-0 w-32 z-10 pointer-events-none"
        style={{ background: 'linear-gradient(to right, #0A0A0B, transparent)' }} />
      <div className="absolute inset-y-0 right-0 w-32 z-10 pointer-events-none"
        style={{ background: 'linear-gradient(to left, #0A0A0B, transparent)' }} />
      <div className="flex animate-marquee whitespace-nowrap w-max">
        {doubled.map((item, i) => (
          <span key={i} className="mx-10 text-[11px] tracking-[0.22em] uppercase text-text-muted/60 font-medium">
            {item}
            <span className="ml-10 text-accent-primary/50">·</span>
          </span>
        ))}
      </div>
    </div>
  )
}

// ─── 3D Tilt Card ───
function TiltCard({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const rotateX = useMotionValue(0)
  const rotateY = useMotionValue(0)
  const springX = useSpring(rotateX, { stiffness: 200, damping: 20 })
  const springY = useSpring(rotateY, { stiffness: 200, damping: 20 })

  const handleMouse = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const el = ref.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width - 0.5
    const y = (e.clientY - rect.top) / rect.height - 0.5
    rotateX.set(y * -8)
    rotateY.set(x * 8)
  }, [rotateX, rotateY])

  const handleLeave = useCallback(() => {
    rotateX.set(0)
    rotateY.set(0)
  }, [rotateX, rotateY])

  return (
    <motion.div
      ref={ref}
      onMouseMove={handleMouse}
      onMouseLeave={handleLeave}
      style={{ rotateX: springX, rotateY: springY, transformPerspective: 1000 }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

// ─── Floating Orbs Background ───
function AuroraBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {/* Main aurora blobs */}
      <div
        className="aurora-blob w-[600px] h-[600px] top-[-10%] left-[-5%] opacity-[0.15]"
        style={{ background: 'radial-gradient(circle, #DC2626, transparent 65%)' }}
      />
      <div
        className="aurora-blob aurora-blob-2 w-[500px] h-[500px] top-[20%] right-[-10%] opacity-[0.08]"
        style={{ background: 'radial-gradient(circle, #7C3AED, transparent 65%)' }}
      />
      <div
        className="aurora-blob aurora-blob-3 w-[400px] h-[400px] bottom-[10%] left-[30%] opacity-[0.06]"
        style={{ background: 'radial-gradient(circle, #EF4444, transparent 65%)' }}
      />

      {/* Subtle grid */}
      <div className="absolute inset-0 grid-pattern opacity-30" />

      {/* Noise texture */}
      <div className="absolute inset-0 noise-overlay" />
    </div>
  )
}

// ─── Floating Particles ───
function Particles({ count = 20 }: { count?: number }) {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="particle"
          style={{
            left: `${Math.random() * 100}%`,
            bottom: `-${Math.random() * 10}%`,
            animationDuration: `${8 + Math.random() * 12}s`,
            animationDelay: `${Math.random() * 10}s`,
            width: `${1 + Math.random() * 2}px`,
            height: `${1 + Math.random() * 2}px`,
            opacity: 0.2 + Math.random() * 0.3,
          }}
        />
      ))}
    </div>
  )
}

// ─── Dashboard card mockup ───
function DashboardMockup() {
  const bars = [45, 72, 58, 85, 65, 90, 78, 92, 68, 88, 75, 95]
  const skills = [
    { label: 'Keywords', value: 82 },
    { label: 'Skills', value: 71 },
    { label: 'Format', value: 95 },
    { label: 'Bullets', value: 68 },
  ]

  return (
    <TiltCard>
      <motion.div
        initial={{ opacity: 0, y: 32, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ delay: 0.9, duration: 0.9, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="relative"
      >
        {/* Glow behind */}
        <div className="absolute -inset-12 rounded-3xl pointer-events-none"
          style={{ background: 'radial-gradient(ellipse at center, rgba(220,38,38,0.12) 0%, transparent 70%)' }} />

        {/* Orbiting dot */}
        <div className="absolute top-1/2 left-1/2 w-0 h-0">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
            className="absolute"
            style={{ width: 200, height: 200, marginLeft: -100, marginTop: -100 }}
          >
            <div className="absolute top-0 left-1/2 w-1.5 h-1.5 rounded-full bg-accent-primary/40 -ml-0.75" />
          </motion.div>
        </div>

        <motion.div
          animate={{ y: [0, -6, 0] }}
          transition={{ repeat: Infinity, duration: 6, ease: 'easeInOut' }}
          className="relative rounded-2xl border border-white/[0.08] p-5 shadow-depth"
          style={{ background: 'rgba(17,17,19,0.95)', backdropFilter: 'blur(24px)' }}
        >
          {/* Animated gradient top border */}
          <div className="absolute top-0 left-4 right-4 h-px rounded-full animated-gradient-line" />

          {/* Window dots */}
          <div className="flex gap-1.5 mb-4">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/50" />
            <div className="w-2.5 h-2.5 rounded-full bg-green-500/50" />
          </div>

          {/* Score + bars */}
          <div className="grid grid-cols-4 gap-2.5 mb-2.5">
            <div className="col-span-1 rounded-xl p-3 flex flex-col items-center justify-center border border-white/[0.05]"
              style={{ background: 'rgba(220,38,38,0.08)' }}>
              <motion.div
                className="font-editorial text-[38px] leading-none"
                style={{
                  background: 'linear-gradient(135deg, #EF4444, #DC2626)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
                animate={{ scale: [1, 1.03, 1] }}
                transition={{ repeat: Infinity, duration: 3, ease: 'easeInOut' }}
              >
                87
              </motion.div>
              <div className="text-[9px] text-text-muted mt-1 tracking-wider uppercase text-center">ATS Score</div>
            </div>
            <div className="col-span-3 rounded-xl p-3 border border-white/[0.05]"
              style={{ background: 'rgba(255,255,255,0.02)' }}>
              <div className="flex items-end gap-1 h-10">
                {bars.map((h, i) => (
                  <motion.div key={i} className="flex-1 rounded-sm"
                    initial={{ scaleY: 0, originY: 1 }}
                    animate={{ scaleY: 1 }}
                    transition={{ delay: 1.2 + i * 0.04, duration: 0.4 }}
                    style={{
                      height: `${h}%`,
                      background: h > 75
                        ? 'linear-gradient(to top, #DC2626, #EF4444)'
                        : h > 55
                          ? 'rgba(220,38,38,0.3)'
                          : 'rgba(255,255,255,0.05)',
                    }}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Skill bars */}
          <div className="grid grid-cols-2 gap-2">
            {skills.map(({ label, value }) => (
              <div key={label} className="rounded-xl px-3 py-2 border border-white/[0.05] glow-hover"
                style={{ background: 'rgba(255,255,255,0.02)' }}>
                <div className="flex justify-between mb-1.5">
                  <span className="text-[9px] text-text-muted uppercase tracking-wider">{label}</span>
                  <span className="text-[9px] font-mono text-text-secondary">{value}%</span>
                </div>
                <div className="h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.05)' }}>
                  <motion.div className="h-full rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${value}%` }}
                    transition={{ delay: 1.5 + Math.random() * 0.2, duration: 0.7 }}
                    style={{ background: 'linear-gradient(90deg, #DC2626, #EF4444)' }} />
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </motion.div>
    </TiltCard>
  )
}

// ─── Data ───
const MARQUEE_ITEMS = [
  'ATS Score Engine', 'Keyword Gap Analysis', 'AI Resume Rewrite',
  'Cover Letter Generator', 'Interview Prep',
  'Job Tracker', 'Bullet Optimizer', 'Skill Gap Detection', 'PDF Export',
]

const FEATURES = [
  { icon: Target, num: '01', title: 'ATS Score Engine', desc: 'Precise 0-100 score with weighted sub-scores for keywords, skills, formatting, and bullet strength.' },
  { icon: Brain, num: '02', title: 'AI Resume Rewrite', desc: 'Gemini AI rewrites your bullets for maximum ATS impact while preserving your voice and formatting.' },
  { icon: BarChart3, num: '03', title: 'Keyword Analysis', desc: 'TF-IDF matching reveals which critical terms you\'re missing and exactly how to incorporate them.' },
  { icon: FileText, num: '04', title: 'Cover Letter Generator', desc: 'Structured cover letters in three tones — confident, professional, or conversational — in seconds.' },
  { icon: Zap, num: '05', title: 'Bullet Optimizer', desc: 'Every bullet scored and rewritten using the X-Y-Z Google formula for quantifiable, compelling impact.' },
  { icon: Shield, num: '06', title: 'Privacy First', desc: 'Processed in-memory only, never stored. Complete privacy and zero data retention. No account needed.' },
]

const STEPS = [
  { step: '01', title: 'Upload Your Resume', desc: 'Drop your PDF or DOCX. Our NLP engine parses and structures it instantly.' },
  { step: '02', title: 'Paste Job Description', desc: 'Add the complete job posting. We extract every required skill and qualification.' },
  { step: '03', title: 'Get Full Intelligence', desc: 'ATS score, keyword gaps, skill analysis, and an AI-optimized rewrite in seconds.' },
]

// ─── Main Page ───
export default function Landing() {
  const heroRef = useRef<HTMLDivElement>(null)
  const spotlightRef = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: heroRef, offset: ['start start', 'end start'] })
  const heroY = useTransform(scrollYProgress, [0, 1], ['0%', '20%'])
  const heroOpacity = useTransform(scrollYProgress, [0, 0.8], [1, 0])
  const heroScale = useTransform(scrollYProgress, [0, 1], [1, 0.95])

  // Spotlight cursor effect for features section
  useEffect(() => {
    const el = spotlightRef.current
    if (!el) return
    const handleMove = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect()
      el.style.setProperty('--mouse-x', `${e.clientX - rect.left}px`)
      el.style.setProperty('--mouse-y', `${e.clientY - rect.top}px`)
    }
    el.addEventListener('mousemove', handleMove)
    return () => el.removeEventListener('mousemove', handleMove)
  }, [])

  return (
    <PageWrapper>

      {/* ═══════════════════════════════════════
          NAV
      ═══════════════════════════════════════ */}
      <motion.header
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="absolute top-0 left-0 right-0 z-50 flex items-center justify-between px-8 lg:px-14 pt-7"
      >
        <Link to="/">
          <span className="font-editorial text-[18px] tracking-[0.1em] text-text-primary">
            HIREPORT<span className="text-accent-primary">AI</span>
          </span>
        </Link>
        <div className="hidden sm:flex items-center gap-8">
          {[['Analyze', '/analyze'], ['Pricing', '/pricing'], ['Tracker', '/tracker']].map(([label, href]) => (
            <Link key={href} to={href}
              className="text-[11px] tracking-[0.18em] uppercase text-text-muted hover:text-text-secondary transition-colors duration-200">
              {label}
            </Link>
          ))}
          <Link to="/analyze"
            className="group relative flex items-center gap-2 px-5 py-2.5 text-white text-[11px] tracking-[0.15em] uppercase font-semibold transition-all duration-300 rounded-xl overflow-hidden"
            style={{ background: 'linear-gradient(135deg, #DC2626 0%, #B91C1C 100%)', boxShadow: '0 4px 20px rgba(220,38,38,0.3)' }}>
            <span className="relative z-10 flex items-center gap-2">
              Start Free
              <ArrowRight size={11} className="transition-transform group-hover:translate-x-0.5" />
            </span>
            {/* Shine sweep */}
            <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-white/20 to-transparent" />
          </Link>
        </div>
      </motion.header>

      {/* ═══════════════════════════════════════
          HERO
      ═══════════════════════════════════════ */}
      <section ref={heroRef} className="relative min-h-screen flex overflow-hidden" style={{ background: '#0A0A0B' }}>
        <AuroraBackground />
        <Particles count={25} />

        <motion.div
          style={{ y: heroY, opacity: heroOpacity, scale: heroScale }}
          className="relative z-10 max-w-7xl mx-auto w-full px-8 lg:px-14 grid grid-cols-1 lg:grid-cols-[1fr_440px] xl:grid-cols-[1fr_500px] gap-12 xl:gap-20 items-center pt-28 pb-20"
        >
          {/* Left */}
          <div>
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15, duration: 0.5 }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-white/[0.07] mb-8 text-[11px] text-text-muted tracking-wide glow-hover"
              style={{ background: 'rgba(255,255,255,0.03)' }}
            >
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-primary opacity-60" />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-accent-primary" />
              </span>
              AI-Powered Career Intelligence Platform
            </motion.div>

            {/* Headline */}
            <div className="overflow-hidden mb-2">
              <motion.h1
                initial={{ y: '100%' }}
                animate={{ y: 0 }}
                transition={{ delay: 0.25, duration: 0.8, ease: [0.76, 0, 0.24, 1] }}
                className="font-editorial leading-[0.88] text-text-primary"
                style={{ fontSize: 'clamp(64px, 8vw, 114px)' }}
              >
                BEAT THE
              </motion.h1>
            </div>
            <div className="overflow-hidden mb-2">
              <motion.h1
                initial={{ y: '100%' }}
                animate={{ y: 0 }}
                transition={{ delay: 0.38, duration: 0.8, ease: [0.76, 0, 0.24, 1] }}
                className="font-editorial leading-[0.88] shimmer-text"
                style={{ fontSize: 'clamp(64px, 8vw, 114px)' }}
              >
                ATS FILTER.
              </motion.h1>
            </div>

            {/* Subtitle */}
            <motion.p
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7, duration: 0.6 }}
              className="font-serif-display italic text-text-secondary text-lg leading-relaxed max-w-[420px] mt-7 mb-10"
            >
              Upload your resume, paste a job description — get your ATS score,
              keyword gaps, and an AI-optimized rewrite instantly.
            </motion.p>

            {/* CTAs */}
            <motion.div
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.85, duration: 0.55 }}
              className="flex flex-wrap items-center gap-3 mb-9"
            >
              <Link to="/analyze"
                className="group relative flex items-center gap-2 px-7 py-3.5 text-white text-sm font-semibold rounded-xl transition-all duration-300 overflow-hidden"
                style={{
                  background: 'linear-gradient(135deg, #DC2626 0%, #B91C1C 100%)',
                  boxShadow: '0 4px 24px rgba(220,38,38,0.3), inset 0 1px 0 rgba(255,255,255,0.1)',
                }}>
                <span className="relative z-10 flex items-center gap-2">
                  Analyze My Resume
                  <ArrowRight size={14} className="transition-transform group-hover:translate-x-1" />
                </span>
                <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-white/20 to-transparent" />
              </Link>
              <Link to="/pricing"
                className="flex items-center gap-2 px-6 py-3 text-text-secondary text-sm font-medium rounded-xl border border-white/[0.08] hover:border-white/[0.14] hover:text-text-primary transition-all duration-300 glow-hover"
                style={{ background: 'rgba(255,255,255,0.02)' }}>
                View Pricing
              </Link>
            </motion.div>

            {/* Trust */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.05, duration: 0.5 }}
              className="flex flex-wrap items-center gap-5"
            >
              {['No sign-up required', 'Privacy-first', 'Free to start'].map((t) => (
                <span key={t} className="flex items-center gap-1.5 text-[11px] text-text-muted">
                  <CheckCircle size={10} className="text-success/60" />
                  {t}
                </span>
              ))}
            </motion.div>
          </div>

          {/* Right — dashboard */}
          <div className="hidden lg:block">
            <DashboardMockup />
          </div>
        </motion.div>

        {/* Bottom gradient fade */}
        <div className="absolute bottom-0 left-0 right-0 h-32 pointer-events-none"
          style={{ background: 'linear-gradient(to top, #0A0A0B, transparent)' }} />
      </section>

      {/* ═══════════════════════════════════════
          MARQUEE
      ═══════════════════════════════════════ */}
      <Marquee items={MARQUEE_ITEMS} />

      {/* ═══════════════════════════════════════
          STATS
      ═══════════════════════════════════════ */}
      <section className="py-20 px-8 lg:px-14 relative overflow-hidden">
        {/* Ambient gradient */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="aurora-blob aurora-blob-2 w-[500px] h-[500px] top-[-20%] right-[10%] opacity-[0.06]"
            style={{ background: 'radial-gradient(circle, #DC2626, transparent 65%)' }} />
        </div>

        <div className="max-w-7xl mx-auto">
          <TiltCard>
            <div className="relative rounded-2xl p-px overflow-hidden"
              style={{ background: 'linear-gradient(135deg, rgba(220,38,38,0.2), rgba(255,255,255,0.04), rgba(220,38,38,0.1))' }}>
              <div className="rounded-2xl px-10 py-12"
                style={{ background: 'linear-gradient(135deg, rgba(17,17,19,0.98), rgba(22,22,24,0.95))' }}>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-10">
                  {[
                    { end: 50000, suffix: '+', label: 'Resumes Analyzed' },
                    { end: 94, suffix: '%', label: 'Accuracy Rate' },
                    { end: 3200, suffix: '+', label: 'Interviews Landed' },
                    { end: 8, suffix: 's', label: 'Avg. Time to Score' },
                  ].map(({ end, suffix, label }, i) => (
                    <motion.div key={label}
                      initial={{ opacity: 0, y: 20 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true }}
                      transition={{ delay: i * 0.1, duration: 0.5 }}>
                      <AnimatedCounter end={end} suffix={suffix} label={label} />
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>
          </TiltCard>
        </div>
      </section>

      {/* ═══════════════════════════════════════
          FEATURES — with spotlight cursor effect
      ═══════════════════════════════════════ */}
      <section ref={spotlightRef} className="py-24 px-8 lg:px-14 relative spotlight">
        <Particles count={10} />

        <div className="max-w-7xl mx-auto relative z-10">
          {/* Section header */}
          <div className="mb-16">
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="text-accent-primary text-[10px] tracking-[0.3em] uppercase font-medium mb-4"
            >
              / Intelligence
            </motion.p>
            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.08, duration: 0.6 }}
              className="font-display text-3xl sm:text-4xl lg:text-5xl font-bold text-text-primary leading-tight max-w-2xl"
              style={{ letterSpacing: '-0.03em' }}
            >
              Everything you need to{' '}
              <span className="shimmer-text">
                land the interview
              </span>
            </motion.h2>
          </div>

          {/* Feature cards with 3D tilt */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map(({ icon: Icon, num, title, desc }, i) => (
              <motion.div key={num}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ delay: i * 0.07, duration: 0.5 }}
              >
                <TiltCard className="h-full">
                  <div
                    className="group relative h-full rounded-2xl p-6 border border-white/[0.06] transition-all duration-300 hover:border-accent-primary/20 overflow-hidden"
                    style={{ background: 'linear-gradient(135deg, rgba(22,22,24,0.9), rgba(17,17,19,0.95))' }}
                  >
                    {/* Hover gradient glow */}
                    <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                      style={{ background: 'radial-gradient(ellipse at 50% 0%, rgba(220,38,38,0.06) 0%, transparent 70%)' }} />

                    {/* Animated top line */}
                    <div className="absolute top-0 left-4 right-4 h-px rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300 animated-gradient-line" />

                    {/* Icon */}
                    <div className="relative w-10 h-10 rounded-xl mb-4 flex items-center justify-center border border-white/[0.06] group-hover:border-accent-primary/25 transition-all duration-300 group-hover:shadow-glow"
                      style={{ background: 'rgba(255,255,255,0.03)' }}>
                      <Icon size={16} className="text-text-muted group-hover:text-accent-primary transition-colors duration-300" strokeWidth={1.8} />
                    </div>

                    {/* Number */}
                    <span className="text-[10px] tracking-[0.2em] text-text-muted/50 mb-1.5 block font-mono">{num}</span>

                    <h3 className="text-text-primary font-semibold text-[14px] mb-2 tracking-tight">{title}</h3>
                    <p className="text-text-muted text-[13px] leading-relaxed">{desc}</p>
                  </div>
                </TiltCard>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════
          HOW IT WORKS
      ═══════════════════════════════════════ */}
      <section className="py-24 px-8 lg:px-14 relative border-t border-white/[0.04] overflow-hidden">
        {/* Ambient blobs */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="aurora-blob aurora-blob-3 w-[400px] h-[400px] bottom-[-10%] right-[-5%] opacity-[0.05]"
            style={{ background: 'radial-gradient(circle, #DC2626, transparent 65%)' }} />
        </div>

        <div className="max-w-7xl mx-auto relative z-10">
          {/* Header */}
          <div className="mb-16 flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
            <div>
              <motion.p
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                className="text-accent-primary text-[10px] tracking-[0.3em] uppercase font-medium mb-4"
              >
                / Process
              </motion.p>
              <motion.h2
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.08, duration: 0.6 }}
                className="font-display text-3xl sm:text-4xl lg:text-5xl font-bold text-text-primary leading-tight"
                style={{ letterSpacing: '-0.03em' }}
              >
                Up and running{' '}
                <span className="shimmer-text">in 30 seconds</span>
              </motion.h2>
            </div>
            <motion.p
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
              className="text-text-muted text-sm max-w-xs leading-relaxed lg:text-right"
            >
              No setup, no account required. Just upload and get instant intelligence.
            </motion.p>
          </div>

          {/* Step cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {STEPS.map(({ step, title, desc }, i) => (
              <motion.div key={step}
                initial={{ opacity: 0, y: 28 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ delay: i * 0.12, duration: 0.55 }}
              >
                <TiltCard className="h-full">
                  <div
                    className="relative h-full rounded-2xl p-8 border border-white/[0.06] overflow-hidden group hover:border-accent-primary/15 transition-all duration-300"
                    style={{ background: 'linear-gradient(135deg, rgba(22,22,24,0.95), rgba(16,16,18,0.98))' }}
                  >
                    {/* Animated gradient top line */}
                    <div className="absolute top-0 left-0 right-0 h-px animated-gradient-line" />

                    {/* Ghost step number */}
                    <div className="absolute -top-4 -right-2 font-editorial text-[100px] leading-none select-none opacity-[0.03] group-hover:opacity-[0.08] transition-opacity duration-500"
                      style={{ color: '#DC2626' }}>
                      {step}
                    </div>

                    {/* Hover gradient */}
                    <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                      style={{ background: 'radial-gradient(ellipse at 30% 0%, rgba(220,38,38,0.05) 0%, transparent 60%)' }} />

                    {/* Step badge */}
                    <div className="relative w-9 h-9 rounded-lg mb-6 flex items-center justify-center text-[11px] font-bold tracking-wider group-hover:shadow-glow transition-shadow duration-300"
                      style={{
                        background: 'linear-gradient(135deg, rgba(220,38,38,0.15), rgba(220,38,38,0.05))',
                        border: '1px solid rgba(220,38,38,0.2)',
                        color: '#EF4444',
                      }}>
                      {step}
                    </div>

                    <h3 className="relative text-text-primary font-semibold text-[15px] mb-3 tracking-tight">{title}</h3>
                    <p className="relative text-text-muted text-[13px] leading-relaxed">{desc}</p>
                  </div>
                </TiltCard>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════
          CTA
      ═══════════════════════════════════════ */}
      <section className="py-28 px-8 lg:px-14 relative overflow-hidden border-t border-white/[0.04]">
        {/* Multi-layer gradient atmosphere */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="aurora-blob w-[800px] h-[800px] bottom-[-30%] left-[20%] opacity-[0.1]"
            style={{ background: 'radial-gradient(circle, #DC2626, transparent 55%)' }} />
          <div className="aurora-blob aurora-blob-2 w-[500px] h-[500px] top-[-20%] right-[10%] opacity-[0.06]"
            style={{ background: 'radial-gradient(circle, #7C3AED, transparent 55%)' }} />
        </div>
        <Particles count={15} />

        <div className="max-w-7xl mx-auto relative z-10 text-center">
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-accent-primary text-[10px] tracking-[0.3em] uppercase font-medium mb-6"
          >
            / Get Started
          </motion.p>

          <motion.h2
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.08, duration: 0.7 }}
            className="font-editorial text-[56px] sm:text-[72px] lg:text-[96px] leading-[0.9] mb-8"
          >
            <span className="text-text-primary">READY TO PASS</span>
            <br />
            <span className="shimmer-text">
              THE ATS FILTER?
            </span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="text-text-muted text-base max-w-md mx-auto mb-10"
          >
            Join 50,000+ job seekers who optimized their resumes with HirePort AI.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3, duration: 0.5 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <Link to="/analyze"
              className="group relative flex items-center gap-2.5 px-8 py-4 text-white font-semibold rounded-xl text-sm transition-all duration-300 overflow-hidden pulse-ring"
              style={{
                background: 'linear-gradient(135deg, #DC2626 0%, #B91C1C 100%)',
                boxShadow: '0 8px 32px rgba(220,38,38,0.35), inset 0 1px 0 rgba(255,255,255,0.1)',
              }}>
              <span className="relative z-10 flex items-center gap-2">
                Start Free Analysis
                <ArrowRight size={15} className="transition-transform group-hover:translate-x-1" />
              </span>
              <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-white/20 to-transparent" />
            </Link>
            <Link to="/pricing"
              className="text-text-muted text-sm hover:text-text-secondary transition-colors">
              View pricing →
            </Link>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════
          FOOTER
      ═══════════════════════════════════════ */}
      <footer className="border-t border-white/[0.05] px-8 lg:px-14 py-12 relative">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-8">
            <div>
              <Link to="/">
                <span className="font-editorial text-[17px] tracking-[0.08em] text-text-secondary hover:text-text-primary transition-colors">
                  HIREPORT<span className="text-accent-primary">AI</span>
                </span>
              </Link>
              <p className="text-[11px] text-text-muted mt-2 max-w-[220px] leading-relaxed">
                AI-powered resume intelligence. Your data stays private.
              </p>
            </div>

            <div className="flex flex-wrap gap-x-10 gap-y-3">
              {[
                ['Analyze', '/analyze'],
                ['Results', '/results'],
                ['Rewrite', '/rewrite'],
                ['Interview Prep', '/interview'],
                ['Tracker', '/tracker'],
                ['Pricing', '/pricing'],
              ].map(([label, href]) => (
                <Link key={href} to={href}
                  className="text-[11px] tracking-wide text-text-muted hover:text-text-secondary transition-colors">
                  {label}
                </Link>
              ))}
            </div>
          </div>

          <div className="mt-10 pt-6 border-t border-white/[0.04] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <p className="text-[11px] text-text-muted/60">
              © {new Date().getFullYear()} HirePort AI. All rights reserved.
            </p>
            <p className="text-[11px] text-text-muted/40">
              No data stored · No account required · Private by design
            </p>
          </div>
        </div>
      </footer>

    </PageWrapper>
  )
}
