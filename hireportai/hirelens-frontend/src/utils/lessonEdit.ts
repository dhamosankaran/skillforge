/**
 * Advisory edit classifier for admin lesson PATCH preview UX.
 *
 * Algorithm: Levenshtein edit distance / max(len(before), len(after))
 * BE counterpart: difflib.SequenceMatcher.ratio() (Ratcliff/Obershelp matching-blocks)
 *
 * The two algorithms can disagree on edge cases:
 *   - Transpositions: Levenshtein over-classifies as substantive
 *     (e.g., "abc" → "bca" is Levenshtein-3 / ratio 1.0 vs SequenceMatcher ~0.33)
 *   - Boundary inserts: Levenshtein under-classifies vs SequenceMatcher
 *     (long appended text dilutes Levenshtein ratio more than SequenceMatcher)
 *
 * Common cases (typo fixes, paragraph rewrites, content additions) agree.
 *
 * BE re-validates authoritatively per spec §7.1 and returns
 * EditClassificationConflictError (409) if FE classification was wrong.
 * FE handles 409 by re-PATCHing with the corrected `edit_classification` value
 * and firing the appropriate confirm modal post-hoc.
 *
 * Threshold 0.15 mirrors SUBSTANTIVE_EDIT_THRESHOLD in
 * app/services/admin_errors.py. Keep in sync — if either side changes,
 * file a §12 amendment.
 */

import type { EditClassification } from '@/types'

export const SUBSTANTIVE_EDIT_THRESHOLD = 0.15

function levenshtein(a: string, b: string): number {
  if (a === b) return 0
  if (a.length === 0) return b.length
  if (b.length === 0) return a.length

  let prev = new Array<number>(b.length + 1)
  let curr = new Array<number>(b.length + 1)
  for (let j = 0; j <= b.length; j++) prev[j] = j

  for (let i = 1; i <= a.length; i++) {
    curr[0] = i
    for (let j = 1; j <= b.length; j++) {
      const cost = a.charCodeAt(i - 1) === b.charCodeAt(j - 1) ? 0 : 1
      curr[j] = Math.min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
    }
    ;[prev, curr] = [curr, prev]
  }
  return prev[b.length]
}

function ratioOf(before: string, after: string): number {
  if (before === after) return 0
  const denom = Math.max(before.length, after.length, 1)
  return levenshtein(before, after) / denom
}

/** Single-field classifier — `'substantive'` iff ratio strictly exceeds threshold. */
export function classifyEdit(before: string, after: string): EditClassification {
  return ratioOf(before, after) > SUBSTANTIVE_EDIT_THRESHOLD ? 'substantive' : 'minor'
}

interface LessonEditableFields {
  concept_md: string
  production_md: string
  examples_md: string
}

/**
 * Lesson-level classifier — `'substantive'` iff ANY of the three Markdown
 * fields exceeds the threshold (mirrors spec §7.1 max-of-three semantic).
 */
export function classifyLessonEdit(
  before: LessonEditableFields,
  after: LessonEditableFields,
): EditClassification {
  const conceptRatio = ratioOf(before.concept_md, after.concept_md)
  const productionRatio = ratioOf(before.production_md, after.production_md)
  const examplesRatio = ratioOf(before.examples_md, after.examples_md)
  const max = Math.max(conceptRatio, productionRatio, examplesRatio)
  return max > SUBSTANTIVE_EDIT_THRESHOLD ? 'substantive' : 'minor'
}
