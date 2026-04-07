import { motion } from 'framer-motion'
import clsx from 'clsx'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

interface GlowButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  children: ReactNode
}

export function GlowButton({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  children,
  className,
  disabled,
  ...props
}: GlowButtonProps) {
  const sizeClasses = {
    sm: 'px-3.5 py-1.5 text-[13px]',
    md: 'px-5 py-2.5 text-sm',
    lg: 'px-6 py-2.5 text-sm',
  }

  const variantClasses = {
    primary:
      'bg-accent-primary text-bg-base font-semibold hover:bg-accent-primary/90',
    secondary:
      'bg-accent-secondary/10 border border-accent-secondary/20 text-accent-secondary hover:bg-accent-secondary/18',
    ghost:
      'bg-white/[0.04] border border-white/[0.08] text-text-secondary hover:bg-white/[0.06] hover:text-text-primary',
  }

  return (
    <motion.button
      whileHover={{ scale: 1.015 }}
      whileTap={{ scale: 0.98 }}
      className={clsx(
        'relative rounded-xl font-body font-medium transition-all duration-200',
        'disabled:opacity-40 disabled:cursor-not-allowed',
        'overflow-hidden select-none',
        sizeClasses[size],
        variantClasses[variant],
        className
      )}
      disabled={disabled || isLoading}
      {...(props as Record<string, unknown>)}
    >
      {isLoading && variant === 'primary' && (
        <span className="absolute inset-0 overflow-hidden" aria-hidden="true">
          <span className="absolute top-0 h-full w-1/2 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-scan-line" />
        </span>
      )}
      <span className={clsx('relative flex items-center justify-center gap-2', isLoading && 'opacity-80')}>
        {isLoading && (
          <svg
            className="animate-spin h-3.5 w-3.5"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        )}
        {children}
      </span>
    </motion.button>
  )
}
