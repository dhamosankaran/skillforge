import { useEffect, useState } from 'react'
import { motion, animate } from 'framer-motion'
import { getGradeColor, getScoreColor } from '@/utils/formatters'

interface ATSScoreGaugeProps {
  score: number
  grade: string
}

export function ATSScoreGauge({ score, grade }: ATSScoreGaugeProps) {
  const [displayScore, setDisplayScore] = useState(0)
  const color = getScoreColor(score)

  // Animate score counter
  useEffect(() => {
    const controls = animate(0, score, {
      duration: 1.2,
      ease: 'easeOut',
      onUpdate: (v) => setDisplayScore(Math.round(v)),
    })
    return controls.stop
  }, [score])

  // SVG arc params
  const size = 200
  const cx = size / 2
  const cy = size / 2
  const r = 80
  const strokeWidth = 12
  const startAngle = 210 // degrees
  const totalSweep = 300

  function polarToCartesian(angle: number) {
    const rad = ((angle - 90) * Math.PI) / 180
    return {
      x: cx + r * Math.cos(rad),
      y: cy + r * Math.sin(rad),
    }
  }

  function describeArc(startDeg: number, sweepDeg: number) {
    const start = polarToCartesian(startDeg)
    const end = polarToCartesian(startDeg + sweepDeg)
    const largeArc = sweepDeg > 180 ? 1 : 0
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`
  }

  const bgArcPath = describeArc(startAngle, totalSweep)
  const scoreSweep = (score / 100) * totalSweep
  const scoreArcPath = describeArc(startAngle, scoreSweep)

  // Needle angle
  const needleAngle = startAngle + (score / 100) * totalSweep

  const needleRad = ((needleAngle - 90) * Math.PI) / 180
  const needleLen = r - 15
  const needleX = cx + needleLen * Math.cos(needleRad)
  const needleY = cy + needleLen * Math.sin(needleRad)

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} aria-label={`ATS Score: ${score} out of 100`}>
          {/* Glow filter */}
          <defs>
            <filter id="glow">
              <feGaussianBlur stdDeviation="4" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Background arc */}
          <path
            d={bgArcPath}
            fill="none"
            stroke="var(--border)"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* Score arc */}
          <motion.path
            d={scoreArcPath}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            filter="url(#glow)"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.2, ease: 'easeOut' }}
            style={{ strokeDasharray: 1, strokeDashoffset: 0 }}
          />

          {/* Needle */}
          <motion.line
            x1={cx}
            y1={cy}
            x2={needleX}
            y2={needleY}
            stroke={color}
            strokeWidth={2}
            strokeLinecap="round"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
          />
          <circle cx={cx} cy={cy} r={5} fill={color} />

          {/* Score text */}
          <text
            x={cx}
            y={cy + 20}
            textAnchor="middle"
            fill={color}
            fontSize="32"
            fontFamily="JetBrains Mono"
            fontWeight="600"
          >
            {displayScore}
          </text>
          <text
            x={cx}
            y={cy + 38}
            textAnchor="middle"
            fill="var(--text-muted)"
            fontSize="11"
            fontFamily="DM Sans"
          >
            out of 100
          </text>
        </svg>
      </div>

      {/* Grade badge */}
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.9 }}
        className="mt-2 flex flex-col items-center gap-1"
      >
        <span
          className="font-display text-4xl font-bold"
          style={{ color: getGradeColor(grade) }}
        >
          {grade}
        </span>
        <span className="text-xs text-text-muted uppercase tracking-widest">ATS Grade</span>
      </motion.div>
    </div>
  )
}
