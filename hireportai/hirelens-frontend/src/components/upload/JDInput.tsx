import { motion } from 'framer-motion'
import { Briefcase } from 'lucide-react'

interface JDInputProps {
  value: string
  onChange: (value: string) => void
}

export function JDInput({ value, onChange }: JDInputProps) {
  const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <span className="w-6 h-6 rounded-full bg-accent-secondary/10 border border-accent-secondary/30 flex items-center justify-center text-accent-secondary text-xs font-bold">
          2
        </span>
        <h2 className="font-display font-semibold text-text-primary">Paste Job Description</h2>
      </div>

      <div className="flex-1 relative flex flex-col">
        <motion.textarea
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Paste the full job description here...

Include the complete posting — responsibilities, requirements, preferred qualifications, and company description. The more context you provide, the more accurate the analysis."
          className="flex-1 min-h-[280px] w-full bg-bg-elevated border border-contrast/[0.06] rounded-xl p-4 text-text-primary placeholder-text-muted text-sm leading-relaxed resize-none transition-all duration-200 focus:outline-none focus:border-accent-primary/40 focus:shadow-glow font-body"
          aria-label="Job description text"
        />
        <div className="flex items-center justify-between mt-2 px-1">
          <div className="flex items-center gap-1.5 text-xs text-text-muted">
            <Briefcase size={11} />
            <span>Job description</span>
          </div>
          <span
            className={`text-xs font-mono ${
              wordCount > 50 ? 'text-success' : 'text-text-muted'
            }`}
          >
            {wordCount} words {wordCount < 50 && '(add more for better results)'}
          </span>
        </div>
      </div>
    </div>
  )
}
