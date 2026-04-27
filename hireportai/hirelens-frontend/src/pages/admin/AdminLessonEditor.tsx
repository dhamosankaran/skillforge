import { useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { capture } from '@/utils/posthog'
import { useAdminLessonEditor } from '@/hooks/useAdminLessonEditor'
import { MarkdownEditor } from '@/components/admin/MarkdownEditor'
import { ConfirmCascadeModal } from '@/components/admin/ConfirmCascadeModal'
import {
  classifyLessonEdit,
  SUBSTANTIVE_EDIT_THRESHOLD,
} from '@/utils/lessonEdit'
import type { EditClassification, LessonUpdateRequest } from '@/types'

interface LessonEditFormValues {
  slug: string
  title: string
  concept_md: string
  production_md: string
  examples_md: string
  display_order: number
}

interface PendingSubmit {
  values: LessonEditFormValues
  classification: EditClassification
}

interface CascadeResults {
  count: number
}

// Re-exported for tests / consumers — the `>` semantic mirrors spec §7.2.
export { SUBSTANTIVE_EDIT_THRESHOLD }

export default function AdminLessonEditor() {
  const params = useParams<{ lessonId: string }>()
  const location = useLocation() as { state?: { deckId?: string } }
  const deckIdFromState = location.state?.deckId
  const lessonId = params.lessonId

  const {
    lesson,
    activeQuizItems,
    loading,
    error,
    updateLesson,
    publishLesson,
    archiveLesson,
  } = useAdminLessonEditor(deckIdFromState, lessonId)

  const [pending, setPending] = useState<PendingSubmit | null>(null)
  const [cascadeResults, setCascadeResults] = useState<CascadeResults | null>(
    null,
  )
  const [conflictRetry, setConflictRetry] = useState(false)

  const form = useForm<LessonEditFormValues>({
    values: lesson
      ? {
          slug: lesson.slug,
          title: lesson.title,
          concept_md: lesson.concept_md,
          production_md: lesson.production_md,
          examples_md: lesson.examples_md,
          display_order: lesson.display_order,
        }
      : undefined,
  })

  const onSubmit = async (values: LessonEditFormValues) => {
    if (!lesson) return
    const classification = classifyLessonEdit(
      {
        concept_md: lesson.concept_md,
        production_md: lesson.production_md,
        examples_md: lesson.examples_md,
      },
      {
        concept_md: values.concept_md,
        production_md: values.production_md,
        examples_md: values.examples_md,
      },
    )

    if (classification === 'substantive') {
      setPending({ values, classification })
      return
    }
    await applyPatch(values, classification)
  }

  const applyPatch = async (
    values: LessonEditFormValues,
    classification: EditClassification,
  ) => {
    if (!lesson) return
    const payload: LessonUpdateRequest = {
      edit_classification: classification,
      slug: values.slug,
      title: values.title,
      concept_md: values.concept_md,
      production_md: values.production_md,
      examples_md: values.examples_md,
      display_order: values.display_order,
    }
    try {
      const response = await updateLesson(payload)
      const eventName =
        response.version_type_applied === 'substantive'
          ? 'admin_lesson_substantively_edited'
          : 'admin_lesson_updated_minor'
      capture(eventName, {
        lesson_id: response.lesson.id,
        deck_id: response.lesson.deck_id,
        version: response.lesson.version,
        quiz_items_retired_count: response.quiz_items_retired_count,
        internal: true,
      })
      setPending(null)
      if (response.version_type_applied === 'substantive') {
        setCascadeResults({ count: response.quiz_items_retired_count })
      }
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response
        ?.status
      // BE re-validated and disagreed — re-fire the modal with the corrected
      // classification per spec §7.1. The PATCH is re-submitted with the
      // BE-computed classification on the same `edit_classification` field.
      if (status === 409 && !conflictRetry) {
        setConflictRetry(true)
        setPending({
          values,
          classification: classification === 'minor' ? 'substantive' : 'minor',
        })
      } else {
        setPending(null)
      }
    }
  }

  const onPublish = async () => {
    if (!lesson) return
    const next = await publishLesson()
    capture('admin_lesson_published', {
      lesson_id: next.id,
      deck_id: next.deck_id,
      version: next.version,
      version_type: next.version_type,
      generated_by_model: next.generated_by_model,
      internal: true,
    })
  }

  const onArchive = async () => {
    if (!lesson) return
    const wasPublished = lesson.published_at !== null
    const next = await archiveLesson()
    capture('admin_lesson_archived', {
      lesson_id: next.id,
      deck_id: next.deck_id,
      was_published: wasPublished,
      internal: true,
    })
  }

  if (loading && !lesson) {
    return (
      <div className="flex items-center justify-center py-12 text-text-muted">
        <Loader2 size={20} className="animate-spin" />
      </div>
    )
  }
  if (error || !lesson) {
    return (
      <div>
        <p className="text-sm text-danger" role="alert">
          {error ?? 'Lesson not found.'}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link
          to={deckIdFromState ? `/admin/decks/${deckIdFromState}` : '/admin/decks'}
          className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft size={14} /> Back to deck
        </Link>
        <div className="flex gap-2">
          <Link
            to={`/admin/lessons/${lesson.id}/quiz-items`}
            state={{ deckId: deckIdFromState }}
            className="px-3 py-1.5 bg-bg-surface text-text-primary text-sm font-medium rounded-lg border border-contrast/[0.08] hover:bg-contrast/[0.04] transition-colors"
            data-testid="admin-lesson-editor-quiz-items-link"
          >
            Quiz items ({activeQuizItems.length})
          </Link>
          {!lesson.published_at ? (
            <button
              type="button"
              onClick={onPublish}
              className="px-3 py-1.5 bg-success text-bg-base text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
              data-testid="admin-lesson-editor-publish"
            >
              Publish
            </button>
          ) : null}
          {!lesson.archived_at ? (
            <button
              type="button"
              onClick={onArchive}
              className="px-3 py-1.5 bg-bg-surface text-text-primary text-sm font-medium rounded-lg border border-contrast/[0.08] hover:bg-contrast/[0.04] transition-colors"
              data-testid="admin-lesson-editor-archive"
            >
              Archive
            </button>
          ) : null}
        </div>
      </div>

      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="bg-bg-surface/60 border border-contrast/[0.06] rounded-xl p-4 space-y-4"
        data-testid="admin-lesson-editor-form"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <label className="space-y-1">
            <span className="text-sm font-medium text-text-primary">Slug</span>
            <input
              {...form.register('slug')}
              className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm text-text-primary"
            />
          </label>
          <label className="space-y-1">
            <span className="text-sm font-medium text-text-primary">Title</span>
            <input
              {...form.register('title')}
              className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm text-text-primary"
            />
          </label>
        </div>

        <MarkdownEditor
          id="concept_md"
          label="Concept"
          value={form.watch('concept_md') ?? ''}
          onChange={(v) => form.setValue('concept_md', v)}
          required
          testId="admin-lesson-editor-concept"
        />
        <MarkdownEditor
          id="production_md"
          label="Production"
          value={form.watch('production_md') ?? ''}
          onChange={(v) => form.setValue('production_md', v)}
          required
          testId="admin-lesson-editor-production"
        />
        <MarkdownEditor
          id="examples_md"
          label="Examples"
          value={form.watch('examples_md') ?? ''}
          onChange={(v) => form.setValue('examples_md', v)}
          required
          testId="admin-lesson-editor-examples"
        />

        <button
          type="submit"
          className="px-4 py-2 bg-accent-primary text-bg-base text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
          data-testid="admin-lesson-editor-save"
        >
          Save changes
        </button>
      </form>

      <ConfirmCascadeModal
        open={pending !== null}
        activeQuizItemCount={activeQuizItems.length}
        onCancel={() => {
          setPending(null)
          setConflictRetry(false)
        }}
        onConfirm={() => {
          if (pending) void applyPatch(pending.values, pending.classification)
        }}
      />
      <ConfirmCascadeModal
        open={cascadeResults !== null}
        activeQuizItemCount={0}
        retiredCount={cascadeResults?.count ?? 0}
        onCancel={() => setCascadeResults(null)}
        onConfirm={() => setCascadeResults(null)}
      />
    </div>
  )
}
