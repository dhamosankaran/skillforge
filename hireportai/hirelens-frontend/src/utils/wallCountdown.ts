/**
 * Daily-review wall countdown helpers.
 *
 * Lifted from `QuizPanel.tsx` in spec #63 / B-059 so the new
 * `DailyReviewWalledView` (pre-flight gate on `/learn/daily`) can render
 * the same `Resets in Xh Ym` / `Resets at H:MM AM/PM` copy that the
 * submit-time `PaywallModal` already shows. Behavior is byte-identical
 * to the prior private helpers — this is a code-org move only.
 */

/** Hours from now until `resetsAtIso`, rounded toward zero. Used for the
 * `daily_card_wall_hit { resets_at_hours_from_now }` analytics prop. */
export function hoursUntil(resetsAtIso: string): number {
  const diffMs = new Date(resetsAtIso).getTime() - Date.now()
  return Math.trunc(diffMs / 3_600_000)
}

/** Relative ("Resets in Xh Ym") for ≤12h remaining; absolute
 * ("Resets at H:MM AM/PM") otherwise. Spec #50 §UI/UX recommendation. */
export function formatResetsAt(resetsAtIso: string): string {
  const diffMs = new Date(resetsAtIso).getTime() - Date.now()
  const totalMin = Math.max(0, Math.round(diffMs / 60_000))
  if (totalMin <= 12 * 60) {
    const h = Math.floor(totalMin / 60)
    const m = totalMin % 60
    return `Resets in ${h}h ${m}m`
  }
  const localTime = new Date(resetsAtIso).toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
  })
  return `Resets at ${localTime}`
}
