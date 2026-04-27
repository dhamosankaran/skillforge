import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { Plus, Loader2 } from 'lucide-react'
import { capture } from '@/utils/posthog'
import { useAdminDecks } from '@/hooks/useAdminDecks'
import type {
  AdminDeckStatusFilter,
  DeckCreateRequest,
  PersonaVisibility,
} from '@/types'

const STATUS_OPTIONS: AdminDeckStatusFilter[] = ['active', 'archived', 'all']

export default function AdminDecks() {
  const {
    decks,
    loading,
    error,
    status,
    setStatus,
    createDeck,
  } = useAdminDecks()
  const [showCreate, setShowCreate] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<DeckCreateRequest>({
    defaultValues: {
      slug: '',
      title: '',
      description: '',
      display_order: 0,
      persona_visibility: 'both',
      tier: 'premium',
    },
  })

  const onSubmit = async (data: DeckCreateRequest) => {
    try {
      const deck = await createDeck(data)
      capture('admin_deck_created', {
        deck_id: deck.id,
        slug: deck.slug,
        persona_visibility: deck.persona_visibility,
        tier: deck.tier,
        internal: true,
      })
      reset()
      setShowCreate(false)
    } catch (err) {
      const message = (err as { response?: { status?: number } })?.response
        ?.status === 409
        ? 'A deck with that slug already exists.'
        : 'Failed to create deck.'
      setError('slug', { type: 'server', message })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-display text-xl font-semibold text-text-primary">
            Decks
          </h2>
          <p className="text-sm text-text-secondary mt-0.5">
            Author and manage curriculum decks.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowCreate((s) => !s)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-accent-primary text-bg-base text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
          data-testid="admin-decks-toggle-create"
        >
          <Plus size={14} />
          {showCreate ? 'Cancel' : 'New deck'}
        </button>
      </div>

      <div
        role="tablist"
        aria-label="Deck status filter"
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
            data-testid={`admin-decks-filter-${opt}`}
          >
            {opt}
          </button>
        ))}
      </div>

      {showCreate ? (
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="bg-bg-surface/60 border border-contrast/[0.06] rounded-xl p-4 space-y-3"
          data-testid="admin-decks-create-form"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <label className="space-y-1">
              <span className="text-sm font-medium text-text-primary">
                Slug *
              </span>
              <input
                {...register('slug', {
                  required: 'Slug required',
                  pattern: {
                    value: /^[a-z0-9-]+$/,
                    message: 'lowercase letters, numbers, dashes only',
                  },
                })}
                className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm text-text-primary"
                placeholder="system-design-fundamentals"
              />
              {errors.slug ? (
                <span className="text-xs text-danger">{errors.slug.message}</span>
              ) : null}
            </label>
            <label className="space-y-1">
              <span className="text-sm font-medium text-text-primary">
                Title *
              </span>
              <input
                {...register('title', { required: 'Title required' })}
                className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm text-text-primary"
              />
              {errors.title ? (
                <span className="text-xs text-danger">
                  {errors.title.message}
                </span>
              ) : null}
            </label>
            <label className="space-y-1">
              <span className="text-sm font-medium text-text-primary">
                Persona visibility
              </span>
              <select
                {...register('persona_visibility')}
                className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm text-text-primary"
              >
                {(['both', 'climber', 'interview_prepper'] as PersonaVisibility[]).map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-1">
              <span className="text-sm font-medium text-text-primary">Tier</span>
              <select
                {...register('tier')}
                className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm text-text-primary"
              >
                <option value="foundation">foundation</option>
                <option value="premium">premium</option>
              </select>
            </label>
          </div>
          <label className="space-y-1 block">
            <span className="text-sm font-medium text-text-primary">
              Description *
            </span>
            <textarea
              {...register('description', { required: 'Description required' })}
              rows={3}
              className="w-full px-3 py-2 bg-bg-elevated border border-contrast/[0.08] rounded-lg text-sm text-text-primary"
            />
            {errors.description ? (
              <span className="text-xs text-danger">
                {errors.description.message}
              </span>
            ) : null}
          </label>
          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-accent-primary text-bg-base text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
            data-testid="admin-decks-submit-create"
          >
            {isSubmitting ? <Loader2 size={14} className="animate-spin" /> : null}
            Create deck
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
      ) : decks.length === 0 ? (
        <p className="text-sm text-text-muted">No decks for this filter.</p>
      ) : (
        <ul
          className="divide-y divide-contrast/[0.06] border border-contrast/[0.06] rounded-xl overflow-hidden bg-bg-surface/60"
          data-testid="admin-decks-list"
        >
          {decks.map((deck) => (
            <li key={deck.id} className="p-3 flex items-center justify-between">
              <div className="min-w-0">
                <Link
                  to={`/admin/decks/${deck.id}`}
                  className="font-medium text-text-primary hover:text-accent-primary truncate block"
                >
                  {deck.title}
                </Link>
                <span className="text-xs text-text-muted">
                  {deck.slug} · {deck.persona_visibility} · {deck.tier}
                  {deck.archived_at ? ' · archived' : ''}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
