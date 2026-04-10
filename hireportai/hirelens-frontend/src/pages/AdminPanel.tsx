import { useState, useEffect, useCallback, useRef } from 'react'
import { Navigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus, Pencil, Trash2, Upload, Sparkles, X, Search, ChevronLeft,
  ChevronRight, Loader2, FileText, Check, AlertTriangle,
} from 'lucide-react'
import { PageWrapper } from '@/components/layout/PageWrapper'
import { GlowButton } from '@/components/ui/GlowButton'
import { useAuth } from '@/context/AuthContext'
import {
  fetchAdminCards,
  fetchCategories,
  createAdminCard,
  updateAdminCard,
  deleteAdminCard,
  generateCardDraft,
  importCardsCSV,
} from '@/services/api'
import toast from 'react-hot-toast'
import type {
  AdminCard,
  AdminCardCreateRequest,
  CardDraft,
  CardImportResponse,
  Category,
} from '@/types'

type Tab = 'cards' | 'create' | 'import' | 'generate'

const DIFF_COLORS = {
  easy: 'text-green-400 bg-green-400/10',
  medium: 'text-yellow-400 bg-yellow-400/10',
  hard: 'text-red-400 bg-red-400/10',
} as const

const INPUT =
  'w-full px-3 py-2.5 bg-bg-elevated border border-contrast/[0.06] rounded-lg text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-primary/30 transition-colors'
const LABEL = 'block text-xs text-text-muted mb-1.5'

export default function AdminPanel() {
  const { user, isLoading: authLoading } = useAuth()

  if (authLoading) return null
  if (!user || user.role !== 'admin') return <Navigate to="/analyze" replace />

  return <AdminDashboard />
}

function AdminDashboard() {
  const [tab, setTab] = useState<Tab>('cards')
  const [categories, setCategories] = useState<Category[]>([])
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    fetchCategories()
      .then((r) => setCategories(r.categories))
      .catch(() => {})
  }, [])

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), [])

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: 'cards', label: 'All Cards', icon: <FileText size={14} /> },
    { key: 'create', label: 'Create', icon: <Plus size={14} /> },
    { key: 'generate', label: 'AI Generate', icon: <Sparkles size={14} /> },
    { key: 'import', label: 'CSV Import', icon: <Upload size={14} /> },
  ]

  return (
    <PageWrapper className="min-h-screen bg-bg-base">
      <div className="max-w-7xl mx-auto px-4 py-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="font-display text-3xl font-bold text-text-primary">
            Admin <span className="text-accent-primary">Panel</span>
          </h1>
          <p className="text-text-secondary text-sm mt-1">
            Manage flashcards — create, edit, delete, generate with AI, or bulk import.
          </p>
        </motion.div>

        {/* Tab bar */}
        <div className="flex gap-1 mb-6 p-1 bg-bg-surface/60 border border-contrast/[0.06] rounded-xl w-fit">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                tab === t.key
                  ? 'bg-accent-primary text-bg-base'
                  : 'text-text-secondary hover:text-text-primary hover:bg-contrast/[0.04]'
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <AnimatePresence mode="wait">
          {tab === 'cards' && (
            <motion.div key="cards" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
              <CardTable categories={categories} refreshKey={refreshKey} onRefresh={refresh} />
            </motion.div>
          )}
          {tab === 'create' && (
            <motion.div key="create" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
              <CreateCardForm categories={categories} onCreated={() => { refresh(); setTab('cards') }} />
            </motion.div>
          )}
          {tab === 'generate' && (
            <motion.div key="generate" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
              <AIGeneratePanel categories={categories} onCreated={() => { refresh(); setTab('cards') }} />
            </motion.div>
          )}
          {tab === 'import' && (
            <motion.div key="import" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
              <CSVImportPanel onImported={refresh} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PageWrapper>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   CARD TABLE
   ═══════════════════════════════════════════════════════════════════════════ */

function CardTable({
  categories,
  refreshKey,
  onRefresh,
}: {
  categories: Category[]
  refreshKey: number
  onRefresh: () => void
}) {
  const [cards, setCards] = useState<AdminCard[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterCat, setFilterCat] = useState('')
  const [filterDiff, setFilterDiff] = useState('')
  const [editingCard, setEditingCard] = useState<AdminCard | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const loadCards = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchAdminCards({
        page,
        per_page: 20,
        q: search || undefined,
        category_id: filterCat || undefined,
        difficulty: filterDiff || undefined,
      })
      setCards(res.cards)
      setTotal(res.total)
      setPages(res.pages)
    } catch {
      // toast is handled by interceptor
    } finally {
      setLoading(false)
    }
  }, [page, search, filterCat, filterDiff])

  useEffect(() => { loadCards() }, [loadCards, refreshKey])

  const handleDelete = async (id: string) => {
    setDeletingId(id)
    try {
      await deleteAdminCard(id)
      toast.success('Card deleted')
      onRefresh()
    } catch {
      // handled by interceptor
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <>
      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            placeholder="Search questions..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            className={`${INPUT} pl-9`}
          />
        </div>
        <select
          value={filterCat}
          onChange={(e) => { setFilterCat(e.target.value); setPage(1) }}
          className={`${INPUT} w-auto min-w-[160px]`}
        >
          <option value="">All Categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
          ))}
        </select>
        <select
          value={filterDiff}
          onChange={(e) => { setFilterDiff(e.target.value); setPage(1) }}
          className={`${INPUT} w-auto min-w-[120px]`}
        >
          <option value="">All Difficulties</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>
      </div>

      {/* Count */}
      <p className="text-xs text-text-muted mb-3">{total} card{total !== 1 ? 's' : ''} total</p>

      {/* Table */}
      <div className="bg-bg-surface/60 border border-contrast/[0.06] rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="animate-spin text-accent-primary" size={28} />
          </div>
        ) : cards.length === 0 ? (
          <div className="text-center py-16 text-text-muted">No cards found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-contrast/[0.06] text-text-muted text-xs uppercase tracking-wider">
                  <th className="text-left px-4 py-3 font-medium">Question</th>
                  <th className="text-left px-4 py-3 font-medium hidden lg:table-cell">Category</th>
                  <th className="text-left px-4 py-3 font-medium">Difficulty</th>
                  <th className="text-left px-4 py-3 font-medium hidden md:table-cell">Tags</th>
                  <th className="text-right px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {cards.map((card) => (
                  <tr key={card.id} className="border-b border-contrast/[0.04] hover:bg-contrast/[0.02] transition-colors">
                    <td className="px-4 py-3 text-text-primary max-w-xs truncate">{card.question}</td>
                    <td className="px-4 py-3 text-text-secondary hidden lg:table-cell">{card.category_name}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${DIFF_COLORS[card.difficulty]}`}>
                        {card.difficulty}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <div className="flex gap-1 flex-wrap">
                        {card.tags.slice(0, 3).map((t) => (
                          <span key={t} className="px-1.5 py-0.5 bg-contrast/[0.04] rounded text-xs text-text-muted">{t}</span>
                        ))}
                        {card.tags.length > 3 && <span className="text-xs text-text-muted">+{card.tags.length - 3}</span>}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-1.5">
                        <button
                          onClick={() => setEditingCard(card)}
                          className="p-1.5 rounded-lg hover:bg-contrast/[0.06] text-text-muted hover:text-accent-primary transition-colors"
                          title="Edit"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => handleDelete(card.id)}
                          disabled={deletingId === card.id}
                          className="p-1.5 rounded-lg hover:bg-red-500/10 text-text-muted hover:text-red-400 transition-colors disabled:opacity-40"
                          title="Delete"
                        >
                          {deletingId === card.id ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-center gap-3 mt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-2 rounded-lg hover:bg-contrast/[0.04] text-text-muted disabled:opacity-30 transition-colors"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="text-sm text-text-secondary">
            Page {page} of {pages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(pages, p + 1))}
            disabled={page === pages}
            className="p-2 rounded-lg hover:bg-contrast/[0.04] text-text-muted disabled:opacity-30 transition-colors"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      )}

      {/* Edit modal */}
      <AnimatePresence>
        {editingCard && (
          <EditCardModal
            card={editingCard}
            categories={categories}
            onClose={() => setEditingCard(null)}
            onSaved={() => { setEditingCard(null); onRefresh() }}
          />
        )}
      </AnimatePresence>
    </>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   EDIT MODAL
   ═══════════════════════════════════════════════════════════════════════════ */

function EditCardModal({
  card,
  categories,
  onClose,
  onSaved,
}: {
  card: AdminCard
  categories: Category[]
  onClose: () => void
  onSaved: () => void
}) {
  const [form, setForm] = useState<CardFormState>({
    question: card.question,
    answer: card.answer,
    difficulty: card.difficulty,
    category_id: card.category_id,
    tags: card.tags.join(', '),
  })
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await updateAdminCard(card.id, {
        question: form.question,
        answer: form.answer,
        difficulty: form.difficulty as 'easy' | 'medium' | 'hard',
        category_id: form.category_id,
        tags: form.tags.split(',').map((t) => t.trim()).filter(Boolean),
      })
      toast.success('Card updated')
      onSaved()
    } catch {
      // handled by interceptor
    } finally {
      setSaving(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 10 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg bg-bg-surface border border-contrast/[0.08] rounded-2xl p-6 max-h-[90vh] overflow-y-auto"
      >
        <div className="flex justify-between items-center mb-5">
          <h2 className="font-display text-lg font-semibold text-text-primary">Edit Card</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-contrast/[0.06] text-text-muted transition-colors">
            <X size={16} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <CardFormFields form={form} setForm={setForm} categories={categories} />
          <div className="flex justify-end gap-2 pt-2">
            <GlowButton type="button" variant="ghost" size="sm" onClick={onClose}>Cancel</GlowButton>
            <GlowButton type="submit" size="sm" isLoading={saving}>Save Changes</GlowButton>
          </div>
        </form>
      </motion.div>
    </motion.div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   SHARED FORM FIELDS
   ═══════════════════════════════════════════════════════════════════════════ */

interface CardFormState {
  question: string
  answer: string
  difficulty: string
  category_id: string
  tags: string
}

function CardFormFields({
  form,
  setForm,
  categories,
}: {
  form: CardFormState
  setForm: React.Dispatch<React.SetStateAction<CardFormState>>
  categories: Category[]
}) {
  return (
    <>
      <div>
        <label className={LABEL}>Category</label>
        <select
          value={form.category_id}
          onChange={(e) => setForm((p) => ({ ...p, category_id: e.target.value }))}
          className={INPUT}
          required
        >
          <option value="">Select category...</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
          ))}
        </select>
      </div>
      <div>
        <label className={LABEL}>Question</label>
        <textarea
          value={form.question}
          onChange={(e) => setForm((p) => ({ ...p, question: e.target.value }))}
          className={`${INPUT} min-h-[80px] resize-y`}
          placeholder="What is...?"
          required
        />
      </div>
      <div>
        <label className={LABEL}>Answer</label>
        <textarea
          value={form.answer}
          onChange={(e) => setForm((p) => ({ ...p, answer: e.target.value }))}
          className={`${INPUT} min-h-[100px] resize-y`}
          placeholder="The answer is..."
          required
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={LABEL}>Difficulty</label>
          <select
            value={form.difficulty}
            onChange={(e) => setForm((p) => ({ ...p, difficulty: e.target.value }))}
            className={INPUT}
            required
          >
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>
        <div>
          <label className={LABEL}>Tags (comma-separated)</label>
          <input
            type="text"
            value={form.tags}
            onChange={(e) => setForm((p) => ({ ...p, tags: e.target.value }))}
            className={INPUT}
            placeholder="sql, joins"
          />
        </div>
      </div>
    </>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   CREATE CARD FORM
   ═══════════════════════════════════════════════════════════════════════════ */

function CreateCardForm({
  categories,
  onCreated,
}: {
  categories: Category[]
  onCreated: () => void
}) {
  const [form, setForm] = useState<CardFormState>({
    question: '',
    answer: '',
    difficulty: 'medium',
    category_id: '',
    tags: '',
  })
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.category_id) { toast.error('Select a category'); return }
    setSaving(true)
    try {
      const payload: AdminCardCreateRequest = {
        category_id: form.category_id,
        question: form.question,
        answer: form.answer,
        difficulty: form.difficulty as 'easy' | 'medium' | 'hard',
        tags: form.tags.split(',').map((t) => t.trim()).filter(Boolean),
      }
      await createAdminCard(payload)
      toast.success('Card created')
      onCreated()
    } catch {
      // handled by interceptor
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-lg">
      <h2 className="font-display text-lg font-semibold text-text-primary mb-4">Create New Card</h2>
      <form onSubmit={handleSubmit} className="space-y-4 bg-bg-surface/60 border border-contrast/[0.06] rounded-xl p-6">
        <CardFormFields form={form} setForm={setForm} categories={categories} />
        <div className="flex justify-end pt-2">
          <GlowButton type="submit" size="sm" isLoading={saving}>
            <Plus size={14} />
            Create Card
          </GlowButton>
        </div>
      </form>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   AI GENERATE PANEL
   ═══════════════════════════════════════════════════════════════════════════ */

function AIGeneratePanel({
  categories,
  onCreated,
}: {
  categories: Category[]
  onCreated: () => void
}) {
  const [topic, setTopic] = useState('')
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard'>('medium')
  const [generating, setGenerating] = useState(false)
  const [draft, setDraft] = useState<CardDraft | null>(null)
  const [categoryId, setCategoryId] = useState('')
  const [saving, setSaving] = useState(false)

  // Editable draft state
  const [editedDraft, setEditedDraft] = useState<CardFormState>({
    question: '',
    answer: '',
    difficulty: 'medium' as string,
    category_id: '',
    tags: '',
  })

  const handleGenerate = async () => {
    if (!topic.trim()) { toast.error('Enter a topic'); return }
    setGenerating(true)
    setDraft(null)
    try {
      const result = await generateCardDraft(topic, difficulty)
      setDraft(result)
      setEditedDraft({
        question: result.question,
        answer: result.answer,
        difficulty: result.difficulty,
        category_id: categoryId,
        tags: result.tags.join(', '),
      })
    } catch {
      // handled by interceptor
    } finally {
      setGenerating(false)
    }
  }

  const handleSaveDraft = async () => {
    if (!editedDraft.category_id) { toast.error('Select a category before saving'); return }
    setSaving(true)
    try {
      await createAdminCard({
        category_id: editedDraft.category_id,
        question: editedDraft.question,
        answer: editedDraft.answer,
        difficulty: editedDraft.difficulty as 'easy' | 'medium' | 'hard',
        tags: editedDraft.tags.split(',').map((t) => t.trim()).filter(Boolean),
      })
      toast.success('Card saved')
      setDraft(null)
      setTopic('')
      onCreated()
    } catch {
      // handled by interceptor
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="font-display text-lg font-semibold text-text-primary mb-1">
        AI Card Generator
      </h2>
      <p className="text-text-secondary text-sm mb-5">
        Enter a topic and difficulty. AI generates a draft you can review and edit before saving.
      </p>

      {/* Input row */}
      <div className="bg-bg-surface/60 border border-contrast/[0.06] rounded-xl p-6 space-y-4 mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="sm:col-span-2">
            <label className={LABEL}>Topic</label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className={INPUT}
              placeholder="e.g. Binary search trees"
            />
          </div>
          <div>
            <label className={LABEL}>Difficulty</label>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value as 'easy' | 'medium' | 'hard')}
              className={INPUT}
            >
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
        </div>
        <div>
          <label className={LABEL}>Category (for saving)</label>
          <select
            value={categoryId}
            onChange={(e) => {
              setCategoryId(e.target.value)
              setEditedDraft((p) => ({ ...p, category_id: e.target.value }))
            }}
            className={INPUT}
          >
            <option value="">Select category...</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
            ))}
          </select>
        </div>
        <div className="flex justify-end">
          <GlowButton onClick={handleGenerate} size="sm" isLoading={generating}>
            <Sparkles size={14} />
            Generate Draft
          </GlowButton>
        </div>
      </div>

      {/* Draft preview/edit */}
      <AnimatePresence>
        {draft && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="bg-bg-surface/60 border border-accent-primary/20 rounded-xl p-6 space-y-4"
          >
            <div className="flex items-center gap-2 mb-1">
              <Sparkles size={14} className="text-accent-primary" />
              <h3 className="font-display font-semibold text-text-primary text-sm">Generated Draft</h3>
              <span className="text-xs text-text-muted">- edit before saving</span>
            </div>

            <CardFormFields form={editedDraft} setForm={setEditedDraft} categories={categories} />

            <div className="flex justify-end gap-2 pt-2">
              <GlowButton
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setDraft(null)}
              >
                Discard
              </GlowButton>
              <GlowButton size="sm" isLoading={saving} onClick={handleSaveDraft}>
                <Check size={14} />
                Save Card
              </GlowButton>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   CSV IMPORT
   ═══════════════════════════════════════════════════════════════════════════ */

function CSVImportPanel({ onImported }: { onImported: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [partial, setPartial] = useState(false)
  const [importing, setImporting] = useState(false)
  const [result, setResult] = useState<CardImportResponse | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = (f: File | undefined) => {
    if (f && f.name.endsWith('.csv')) {
      setFile(f)
      setResult(null)
    } else if (f) {
      toast.error('Please upload a .csv file')
    }
  }

  const handleImport = async () => {
    if (!file) return
    setImporting(true)
    setResult(null)
    try {
      const res = await importCardsCSV(file, partial)
      setResult(res)
      if (res.created_count > 0) {
        toast.success(`${res.created_count} card${res.created_count > 1 ? 's' : ''} imported`)
        onImported()
      }
    } catch (err: unknown) {
      // For 400 errors with structured body, try to extract the import result
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: CardImportResponse } } }
        const detail = axiosErr.response?.data?.detail
        if (detail && typeof detail === 'object' && 'errors' in detail) {
          setResult(detail as CardImportResponse)
        }
      }
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="max-w-lg">
      <h2 className="font-display text-lg font-semibold text-text-primary mb-1">Bulk CSV Import</h2>
      <p className="text-text-secondary text-sm mb-5">
        Upload a CSV file with columns: <code className="text-accent-primary text-xs">category_id, question, answer, difficulty, tags</code>
      </p>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]) }}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all duration-200 ${
          dragOver
            ? 'border-accent-primary/40 bg-accent-primary/5'
            : file
              ? 'border-accent-primary/20 bg-bg-surface/60'
              : 'border-contrast/[0.08] bg-bg-surface/40 hover:border-contrast/[0.12]'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
        {file ? (
          <div className="flex items-center justify-center gap-2 text-accent-primary">
            <FileText size={20} />
            <span className="text-sm font-medium">{file.name}</span>
            <button
              onClick={(e) => { e.stopPropagation(); setFile(null); setResult(null) }}
              className="p-1 rounded hover:bg-contrast/[0.06]"
            >
              <X size={14} />
            </button>
          </div>
        ) : (
          <>
            <Upload size={28} className="mx-auto text-text-muted mb-2" />
            <p className="text-text-secondary text-sm">
              Drag & drop a CSV file here, or click to browse
            </p>
            <p className="text-text-muted text-xs mt-1">Max 5 MB, 500 rows</p>
          </>
        )}
      </div>

      {/* Partial toggle + import button */}
      <div className="flex items-center justify-between mt-4">
        <label className="flex items-center gap-2 text-sm text-text-secondary cursor-pointer">
          <input
            type="checkbox"
            checked={partial}
            onChange={(e) => setPartial(e.target.checked)}
            className="rounded border-contrast/[0.1] bg-bg-elevated accent-accent-primary"
          />
          Partial import (skip invalid rows)
        </label>
        <GlowButton onClick={handleImport} size="sm" isLoading={importing} disabled={!file}>
          <Upload size={14} />
          Import
        </GlowButton>
      </div>

      {/* Result */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-4 bg-bg-surface/60 border border-contrast/[0.06] rounded-xl p-4"
          >
            <div className="flex items-center gap-4 text-sm">
              <span className="flex items-center gap-1.5 text-green-400">
                <Check size={14} /> {result.created_count} created
              </span>
              {result.skipped_count > 0 && (
                <span className="flex items-center gap-1.5 text-yellow-400">
                  <AlertTriangle size={14} /> {result.skipped_count} skipped
                </span>
              )}
            </div>
            {result.errors.length > 0 && (
              <div className="mt-3 space-y-1 max-h-40 overflow-y-auto">
                {result.errors.map((err, i) => (
                  <p key={i} className="text-xs text-red-400">
                    Row {err.row}: {err.error}
                  </p>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
