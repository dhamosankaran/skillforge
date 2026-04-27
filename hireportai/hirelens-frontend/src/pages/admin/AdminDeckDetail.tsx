import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { ArrowLeft, Plus, Loader2 } from 'lucide-react'
import { capture } from '@/utils/posthog'
import { useAdminDeckDetail } from '@/hooks/useAdminDeckDetail'
import { adminCreateLesson } from '@/services/api'
import {
  ConfirmPersonaNarrowingModal,
  computeRemovedPersonas,
} from '@/components/admin/ConfirmPersonaNarrowingModal'
import type {
  AdminLessonStatusFilter,
  DeckUpdateRequest,
  LessonCreateRequest,
  PersonaVisibility,
} from '@/types'

const LESSON_STATUS_OPTIONS: AdminLessonStatusFilter[] = [
  'active',
  'drafts',
  'published',
  'archived',
  'all',
]

export default function AdminDeckDetail() {
  const params = useParams<{ deckId: string }>()
  const deckId = params.deckId
  const {
    deck,
    lessons,
    loading,
    error,
    lessonStatus,
    setLessonStatus,
    refetch,
    updateDeck,
    archiveDeck,
  } = useAdminDeckDetail(deckId)

  const [pendingPatch, setPendingPatch] = useState<DeckUpdateRequest | null>(
    null,
  )
  const [showCreateLesson, setShowCreateLesson] = useState(false)

  const deckForm = useForm<DeckUpdateRequest>({ values: deck ?? undefined })
  const lessonForm = useForm<LessonCreateRequest>({
    defaultValues: {
      slug: '',
      title: '',
      concept_md: '',
      production_md: '',
      examples_md: '',
      display_order: 0,
    },
  })

  const submitDeckPatch = async (data: DeckUpdateRequest) => {
    if (!deck) return
    const removed = data.persona_visibility
      ? computeRemovedPersonas(deck.persona_visibility, data.persona_visibility)
      : []
    if (removed.length > 0) {
      setPendingPatch(data)
      return
    }
    await applyDeckPatch(data)
  }

  const applyDeckPatch = async (data: DeckUpdateRequest) => {
    if (!deck) return
    const before = deck.persona_visibility
    const next = await updateDeck(data)
    capture('admin_deck_updated', {
      deck_id: next.id,
      fields_changed: Object.keys(data).filter(
        (k) => (data as Record<string, unknown>)[k] !== undefined,
      ),
      persona_visibility_narrowed:
        data.persona_visibility !== undefined &&
        computeRemovedPersonas(before, data.persona_visibility).length > 0,
      internal: true,
    })
    if (
      data.persona_visibility !== undefined &&
      computeRemovedPersonas(before, data.persona_visibility).length > 0
    ) {
      capture('admin_deck_persona_narrowed', {
        deck_id: next.id,
        removed_personas: computeRemovedPersonas(before, data.persona_visibility),
        before_count: before === 'both' ? 2 : 1,
        after_count: data.persona_visibility === 'both' ? 2 : 1,
        internal: true,
      })
    }
    setPendingPatch(null)
  }

  const onArchive = async () => {
    if (!deck) return
    const next = await archiveDeck()
    capture('admin_deck_archived', {
      deck_id: next.id,
      slug: next.slug,
      internal: true,
    })
  }

  const onCreateLesson = async (data: LessonCreateRequest) => {
    if (!deckId) return
    const lesson = await adminCreateLesson(deckId, data)
    capture('admin_lesson_created', {
      lesson_id: lesson.id,
      deck_id: lesson.deck_id,
      slug: lesson.slug,
      internal: true,
    })
    lessonForm.reset()
    setShowCreateLesson(false)
    await refetch()
  }

  if (loading && !deck) {
    return (
      <div className="flex items-center justify-center py-12 text-text-muted">
        <Loader2 size={20} className="animate-spin" />
      </div>
    )
  }
  if (error || !deck) {
    return (
      <div>
        <p className="text-sm text-danger" role="alert">
          {error ?? 'Deck not found.'}
        </p>
        <Link
          to="/admin/decks"
          className="inline-flex items-center gap-1 mt-2 text-sm text-accent-primary"
        >
          <ArrowLeft size={14} /> Back to decks
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link
          to="/admin/decks"
          className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft size={14} /> Back to decks
        </Link>
        {!deck.archived_at ? (
          <button
            type="button"
            onClick={onArchive}
            className="px-3 py-1.5 bg-bg-surface text-text-primary text-sm font-medium rounded-lg border border-contrast/[0.08] hover:bg-contrast/[0.04] transition-colors"
            data-testid="admin-deck-detail-archive"
          >
            Archive deck
          </button>
        ) : (
          <span className="text-xs text-text-muted">Archived</span>
        )}
      </div>

      <form
        onSubmit={deckForm.handleSubmit(submitDeckPatch)}
        className="bg-bg-surface/60 border border-contrast/[0.06] rounded-xl p-4 space-y-3"
        data-testid="admin-deck-detail-form"
      >
        <h2 className="font-display text-lg font-semibold text-text-primary">
          {deck.title}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <label className="space-y-1">
            <span className="text-sm font-medium text-text-primary">Title</span>
            <input
              {...deckForm.register('title')}
              className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm text-text-primary"
            />
          </label>
          <label className="space-y-1">
            <span className="text-sm font-medium text-text-primary">
              Persona visibility
            </span>
            <select
              {...deckForm.register('persona_visibility')}
              className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm text-text-primary"
              data-testid="admin-deck-detail-persona"
            >
              {(['both', 'climber', 'interview_prepper'] as PersonaVisibility[]).map(
                (p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ),
              )}
            </select>
          </label>
        </div>
        <label className="space-y-1 block">
          <span className="text-sm font-medium text-text-primary">
            Description
          </span>
          <textarea
            {...deckForm.register('description')}
            rows={3}
            className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm text-text-primary"
          />
        </label>
        <button
          type="submit"
          className="px-4 py-2 bg-accent-primary text-bg-base text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
          data-testid="admin-deck-detail-save"
        >
          Save changes
        </button>
      </form>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-lg font-semibold text-text-primary">
            Lessons
          </h3>
          <button
            type="button"
            onClick={() => setShowCreateLesson((s) => !s)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-accent-primary text-bg-base text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
            data-testid="admin-deck-detail-toggle-lesson-create"
          >
            <Plus size={14} />
            {showCreateLesson ? 'Cancel' : 'New lesson'}
          </button>
        </div>

        <div
          role="tablist"
          aria-label="Lesson status filter"
          className="flex flex-wrap gap-1 p-0.5 bg-bg-surface/60 border border-contrast/[0.06] rounded-md w-fit"
        >
          {LESSON_STATUS_OPTIONS.map((opt) => (
            <button
              key={opt}
              type="button"
              role="tab"
              aria-selected={lessonStatus === opt}
              onClick={() => setLessonStatus(opt)}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                lessonStatus === opt
                  ? 'bg-accent-primary text-bg-base'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
              data-testid={`admin-deck-detail-lesson-filter-${opt}`}
            >
              {opt}
            </button>
          ))}
        </div>

        {showCreateLesson ? (
          <form
            onSubmit={lessonForm.handleSubmit(onCreateLesson)}
            className="bg-bg-surface/60 border border-contrast/[0.06] rounded-xl p-4 space-y-3"
            data-testid="admin-deck-detail-lesson-create-form"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label className="space-y-1">
                <span className="text-sm font-medium text-text-primary">
                  Slug *
                </span>
                <input
                  {...lessonForm.register('slug', { required: true })}
                  className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm text-text-primary"
                />
              </label>
              <label className="space-y-1">
                <span className="text-sm font-medium text-text-primary">
                  Title *
                </span>
                <input
                  {...lessonForm.register('title', { required: true })}
                  className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm text-text-primary"
                />
              </label>
            </div>
            <label className="space-y-1 block">
              <span className="text-sm font-medium text-text-primary">
                Concept (Markdown) *
              </span>
              <textarea
                {...lessonForm.register('concept_md', { required: true })}
                rows={4}
                className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm font-mono text-text-primary"
              />
            </label>
            <label className="space-y-1 block">
              <span className="text-sm font-medium text-text-primary">
                Production (Markdown) *
              </span>
              <textarea
                {...lessonForm.register('production_md', { required: true })}
                rows={4}
                className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm font-mono text-text-primary"
              />
            </label>
            <label className="space-y-1 block">
              <span className="text-sm font-medium text-text-primary">
                Examples (Markdown) *
              </span>
              <textarea
                {...lessonForm.register('examples_md', { required: true })}
                rows={4}
                className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm font-mono text-text-primary"
              />
            </label>
            <button
              type="submit"
              className="px-4 py-2 bg-accent-primary text-bg-base text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
              data-testid="admin-deck-detail-lesson-submit"
            >
              Create lesson
            </button>
          </form>
        ) : null}

        {lessons.length === 0 ? (
          <p className="text-sm text-text-muted">
            No lessons for this filter.
          </p>
        ) : (
          <ul
            className="divide-y divide-contrast/[0.06] border border-contrast/[0.06] rounded-xl overflow-hidden bg-bg-surface/60"
            data-testid="admin-deck-detail-lessons"
          >
            {lessons.map((lesson) => (
              <li
                key={lesson.id}
                className="p-3 flex items-center justify-between"
              >
                <Link
                  to={`/admin/lessons/${lesson.id}`}
                  state={{ deckId: deck.id }}
                  className="min-w-0 truncate font-medium text-text-primary hover:text-accent-primary"
                >
                  {lesson.title}
                </Link>
                <span className="text-xs text-text-muted">
                  v{lesson.version} ·{' '}
                  {lesson.archived_at
                    ? 'archived'
                    : lesson.published_at
                      ? 'published'
                      : 'draft'}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <ConfirmPersonaNarrowingModal
        open={pendingPatch !== null}
        onCancel={() => setPendingPatch(null)}
        onConfirm={() => pendingPatch && void applyDeckPatch(pendingPatch)}
        removedPersonas={
          pendingPatch?.persona_visibility && deck
            ? computeRemovedPersonas(
                deck.persona_visibility,
                pendingPatch.persona_visibility,
              )
            : []
        }
      />
    </div>
  )
}
