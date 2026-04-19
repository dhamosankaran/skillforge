/**
 * Browser-side SHA-256 helper used to derive a short JD-hash prefix for
 * analytics correlation with the backend `interview_question_sets` cache key.
 *
 * Normalization mirrors `app/utils/text_hash.py::_normalize_jd` (collapse
 * whitespace runs → strip → casefold) so the same JD produces the same prefix
 * client-side and server-side. We only emit the first 8 hex chars — enough to
 * group cache events without leaking the JD itself.
 */
export function normalizeJd(text: string): string {
  return text.split(/\s+/).filter(Boolean).join(' ').toLowerCase()
}

export async function jdHashPrefix(text: string): Promise<string> {
  const subtle = globalThis.crypto?.subtle
  if (!subtle) return ''
  const data = new TextEncoder().encode(normalizeJd(text))
  const buf = await subtle.digest('SHA-256', data)
  const bytes = Array.from(new Uint8Array(buf)).slice(0, 4)
  return bytes.map((b) => b.toString(16).padStart(2, '0')).join('')
}
