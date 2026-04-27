import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownEditorProps {
  id?: string
  label: string
  value: string
  onChange: (next: string) => void
  rows?: number
  placeholder?: string
  required?: boolean
  testId?: string
}

export function MarkdownEditor({
  id,
  label,
  value,
  onChange,
  rows = 10,
  placeholder,
  required,
  testId,
}: MarkdownEditorProps) {
  const [tab, setTab] = useState<'edit' | 'preview'>('edit')

  return (
    <div className="space-y-2" data-testid={testId}>
      <div className="flex items-center justify-between">
        <label
          htmlFor={id}
          className="text-sm font-medium text-text-primary"
        >
          {label}
          {required ? <span className="text-danger ml-1">*</span> : null}
        </label>
        <div
          role="tablist"
          aria-label={`${label} editor mode`}
          className="flex gap-1 p-0.5 bg-bg-surface/60 border border-contrast/[0.06] rounded-md"
        >
          {(['edit', 'preview'] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              role="tab"
              aria-selected={tab === mode}
              onClick={() => setTab(mode)}
              className={`px-2.5 py-1 text-xs font-medium rounded transition-colors ${
                tab === mode
                  ? 'bg-accent-primary text-bg-base'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              {mode === 'edit' ? 'Edit' : 'Preview'}
            </button>
          ))}
        </div>
      </div>

      {tab === 'edit' ? (
        <textarea
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={rows}
          placeholder={placeholder}
          className="w-full px-3 py-2 bg-bg-surface border border-contrast/[0.08] rounded-lg text-sm text-text-primary placeholder:text-text-muted font-mono focus:outline-none focus:border-accent-primary"
          data-testid={testId ? `${testId}-textarea` : undefined}
        />
      ) : (
        <div
          className="prose prose-sm max-w-none px-3 py-2 bg-bg-surface border border-contrast/[0.08] rounded-lg text-text-primary min-h-[120px]"
          data-testid={testId ? `${testId}-preview` : undefined}
        >
          {value.trim() ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{value}</ReactMarkdown>
          ) : (
            <span className="text-text-muted italic">Nothing to preview yet.</span>
          )}
        </div>
      )}
    </div>
  )
}
