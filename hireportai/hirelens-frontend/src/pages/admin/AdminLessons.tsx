// Phase 6 slice 6.4a placeholder — the real lesson-authoring entry
// (`/admin/lessons/:lesson_id` editor) ships in slice 6.4b (B-065).
// AC-3 requires this placeholder copy verbatim.

export default function AdminLessons() {
  return (
    <div
      data-testid="admin-lessons-placeholder"
      className="bg-bg-surface/60 border border-contrast/[0.06] rounded-xl p-12 text-center"
    >
      <h2 className="font-display text-lg font-semibold text-text-primary mb-2">
        Lesson authoring
      </h2>
      <p className="text-text-secondary text-sm">
        Pick a deck to author lessons.
      </p>
    </div>
  )
}
