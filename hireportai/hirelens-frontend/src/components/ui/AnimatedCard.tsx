import { motion } from 'framer-motion'
import clsx from 'clsx'
import type { ReactNode } from 'react'

export const cardVariants = {
  hidden: { opacity: 0, y: 16 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] },
  },
}

export const containerVariants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.06 },
  },
}

interface AnimatedCardProps {
  children: ReactNode
  className?: string
  glowOnHover?: boolean
  onClick?: () => void
}

export function AnimatedCard({
  children,
  className,
  glowOnHover = false,
  onClick,
}: AnimatedCardProps) {
  return (
    <motion.div
      variants={cardVariants}
      whileHover={{
        borderColor: glowOnHover ? 'var(--border-accent)' : 'var(--border)',
        y: -2,
        scale: 1.02,
        boxShadow: glowOnHover
          ? `0 8px 30px rgba(0,0,0,0.4), 0 0 20px var(--accent-glow)`
          : '0 8px 30px rgba(0,0,0,0.3)',
        transition: { duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] },
      }}
      whileTap={onClick ? { scale: 0.98, transition: { duration: 0.1 } } : undefined}
      onClick={onClick}
      className={clsx(
        'bg-bg-surface/60 border border-contrast/[0.06] rounded-2xl transition-all duration-200',
        onClick && 'cursor-pointer',
        className
      )}
    >
      {children}
    </motion.div>
  )
}
