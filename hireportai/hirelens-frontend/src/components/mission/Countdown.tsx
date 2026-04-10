/**
 * Countdown — circular progress ring with "N days left" display.
 *
 * Shows a SVG ring that fills as mission progress increases,
 * the number of days remaining, and the mission title.
 */
import { motion } from 'framer-motion'

interface CountdownProps {
  title: string
  daysRemaining: number
  totalDays: number
  progressPct: number
}

const RING_SIZE = 120
const STROKE_WIDTH = 6
const RADIUS = (RING_SIZE - STROKE_WIDTH) / 2
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

export function Countdown({ title, daysRemaining, totalDays, progressPct }: CountdownProps) {
  const strokeDashoffset = CIRCUMFERENCE - (progressPct / 100) * CIRCUMFERENCE

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="flex flex-col items-center gap-4"
    >
      {/* Ring */}
      <div className="relative" style={{ width: RING_SIZE, height: RING_SIZE }}>
        <svg
          width={RING_SIZE}
          height={RING_SIZE}
          className="transform -rotate-90"
        >
          {/* Background track */}
          <circle
            cx={RING_SIZE / 2}
            cy={RING_SIZE / 2}
            r={RADIUS}
            fill="none"
            stroke="var(--border)"
            strokeWidth={STROKE_WIDTH}
          />
          {/* Progress arc */}
          <motion.circle
            cx={RING_SIZE / 2}
            cy={RING_SIZE / 2}
            r={RADIUS}
            fill="none"
            stroke="url(#mission-gradient)"
            strokeWidth={STROKE_WIDTH}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            initial={{ strokeDashoffset: CIRCUMFERENCE }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 1.2, ease: 'easeOut' }}
          />
          <defs>
            <linearGradient id="mission-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="var(--accent-primary)" />
              <stop offset="100%" stopColor="var(--accent-secondary)" />
            </linearGradient>
          </defs>
        </svg>

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span
            key={daysRemaining}
            initial={{ scale: 1.2, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: 'spring', bounce: 0.3 }}
            className="font-display text-3xl font-bold text-text-primary leading-none"
          >
            {daysRemaining}
          </motion.span>
          <span className="text-[10px] uppercase tracking-widest text-text-muted mt-0.5">
            {daysRemaining === 1 ? 'day left' : 'days left'}
          </span>
        </div>
      </div>

      {/* Title + progress */}
      <div className="text-center">
        <h3 className="font-display text-lg font-semibold text-text-primary">{title}</h3>
        <p className="text-xs text-text-muted mt-1">
          Day {totalDays - daysRemaining + 1} of {totalDays}
          <span className="mx-1.5 text-white/20">|</span>
          {Math.round(progressPct)}% complete
        </p>
      </div>
    </motion.div>
  )
}
