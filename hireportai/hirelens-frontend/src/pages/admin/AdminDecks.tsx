// Phase 6 slice 6.4a placeholder — the real deck-authoring page ships
// in slice 6.4b (B-065). Kept as a thin placeholder so the sidebar's
// /admin/decks link resolves to a route mount today.

export default function AdminDecks() {
  return (
    <div
      data-testid="admin-decks-placeholder"
      className="bg-bg-surface/60 border border-contrast/[0.06] rounded-xl p-12 text-center"
    >
      <h2 className="font-display text-lg font-semibold text-text-primary mb-2">
        Deck authoring
      </h2>
      <p className="text-text-secondary text-sm">
        Coming in slice 6.4b.
      </p>
    </div>
  )
}
