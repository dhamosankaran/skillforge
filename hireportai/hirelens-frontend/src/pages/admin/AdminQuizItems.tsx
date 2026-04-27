import { useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { ArrowLeft, Plus, Loader2 } from 'lucide-react'
import { capture } from '@/utils/posthog'
import { useAdminQuizItems } from '@/hooks/useAdminQuizItems'
import type {
  AdminQuizItemStatusFilter,
  QuestionType,
  QuizDifficulty,
  QuizItemCreateRequest,
} from '@/types'

const STATUS_OPTIONS: AdminQuizItemStatusFilter[] = ['active', 'retired', 'all']

export default function AdminQuizItems() {
  const params = useParams<{ lessonId: string }>()
  const location = useLocation() as { state?: { deckId?: string } }
  const lessonId = params.lessonId
  const deckId = location.state?.deckId

  const {
    items,
    loading,
    error,
    status,
    setStatus,
    createQuizItem,
    retireQuizItem,
  } = useAdminQuizItems(lessonId)

  const [showCreate, setShowCreate] = useState(false)
  const form = useForm<QuizItemCreateRequest>({
    defaultValues: {
      question: '',
      answer: '',
      question_type: 'free_text',
      difficulty: 'medium',
      display_order: 0,
    },
  })

  const onCreate = async (data: QuizItemCreateRequest) => {
    if (!lessonId) return
    const next = await createQuizItem(data)
    capture('admin_quiz_item_created', {
      quiz_item_id: next.id,
      lesson_id: next.lesson_id,
      question_type: next.question_type,
      difficulty: next.difficulty,
      internal: true,
    })
    form.reset()
    setShowCreate(false)
  }

  const onRetire = async (quizItemId: string) => {
    const next = await retireQuizItem(quizItemId)
    capture('admin_quiz_item_retired', {
      quiz_item_id: next.id,
      lesson_id: next.lesson_id,
      superseded_by_id: next.superseded_by_id,
      prior_version: next.version,
      retire_reason: 'direct',
      internal: true,
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link
          to={
            deckId
              ? `/admin/lessons/${lessonId}`
              : `/admin/decks`
          }
          state={{ deckId }}
          className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft size={14} /> Back to lesson
        </Link>
        <button
          type="button"
          onClick={() => setShowCreate((s) => !s)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-accent-primary text-bg-base text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
          data-testid="admin-quiz-items-toggle-create"
        >
          <Plus size={14} />
          {showCreate ? 'Cancel' : 'New quiz item'}
        </button>
      </div>

      <div
        role="tablist"
        aria-label="Quiz item status filter"
        className="flex gap-1 p-0.5 bg-bg-surface/60 border border-contrast/[0.06] rounded-md w-fit"
      >
        {STATUS_OPTIONS.map((opt) => (
          <button
            key={opt}
            type="button"
            role="tab"
            aria-selected={status === opt}
            onClick={() => setStatus(opt)}
            className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
              status === opt
                ? 'bg-accent-primary text-bg-base'
                : 'text-text-secondary hover:text-text-primary'
            }`}
            data-testid={`admin-quiz-items-filter-${opt}`}
          >
            {opt}
          </button>
        ))}
      </div>

      {showCreate ? (
        <form
          onSubmit={form.handleSubmit(onCreate)}
          className="bg-bg-surface/60 border border-contrast/[0.06] rounded-xl p-4 space-y-3"
          data-testid="admin-quiz-items-create-form"
        >
          <label className="space-y-1 block">
            <span className="text-sm font-medium text-text-primary">
              Question *
            </span>
            <textarea
              {...form.register('question', { required: true })}
              rows={3}
              className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm text-text-primary"
            />
          </label>
          <label className="space-y-1 block">
            <span className="text-sm font-medium text-text-primary">
              Answer *
            </span>
            <textarea
              {...form.register('answer', { required: true })}
              rows={3}
              className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm text-text-primary"
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="space-y-1">
              <span className="text-sm font-medium text-text-primary">
                Type
              </span>
              <select
                {...form.register('question_type')}
                className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm text-text-primary"
              >
                {(['mcq', 'free_text', 'code_completion'] as QuestionType[]).map(
                  (t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ),
                )}
              </select>
            </label>
            <label className="space-y-1">
              <span className="text-sm font-medium text-text-primary">
                Difficulty
              </span>
              <select
                {...form.register('difficulty')}
                className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm text-text-primary"
              >
                {(['easy', 'medium', 'hard'] as QuizDifficulty[]).map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-accent-primary text-bg-base text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
            data-testid="admin-quiz-items-submit-create"
          >
            Create quiz item
          </button>
        </form>
      ) : null}

      {loading ? (
        <div className="flex items-center justify-center py-12 text-text-muted">
          <Loader2 size={20} className="animate-spin" />
        </div>
      ) : error ? (
        <p className="text-sm text-danger" role="alert">
          {error}
        </p>
      ) : items.length === 0 ? (
        <p className="text-sm text-text-muted">
          No quiz items for this filter.
        </p>
      ) : (
        <ul
          className="divide-y divide-contrast/[0.06] border border-contrast/[0.06] rounded-xl overflow-hidden bg-bg-surface/60"
          data-testid="admin-quiz-items-list"
        >
          {items.map((item) => (
            <li
              key={item.id}
              className="p-3 flex items-start justify-between gap-3"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm text-text-primary line-clamp-2">
                  {item.question}
                </p>
                <span className="text-xs text-text-muted">
                  v{item.version} · {item.question_type} · {item.difficulty}
                  {item.retired_at ? ' · retired' : ''}
                </span>
              </div>
              {!item.retired_at ? (
                <button
                  type="button"
                  onClick={() => void onRetire(item.id)}
                  className="px-2.5 py-1 text-xs font-medium rounded text-danger hover:bg-danger/10 transition-colors"
                  data-testid={`admin-quiz-items-retire-${item.id}`}
                >
                  Retire
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
