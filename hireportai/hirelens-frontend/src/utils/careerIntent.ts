// Spec #67 — Career-Climber role-intent constants + quarter helper.
// CAREER_ROLES mirrors `app/schemas/career_intent.ALLOWED_ROLES` (BE/§5.3 D-11).
// QUARTER_LIMIT_FUTURE = 7 per D-4 (current + 7 future = ~2 years).

export const CAREER_ROLES = [
  'staff',
  'senior_staff',
  'principal',
  'distinguished',
  'em',
  'sr_em',
  'director',
] as const

export type CareerRole = (typeof CAREER_ROLES)[number]

export const CAREER_ROLE_LABELS: Record<CareerRole, string> = {
  staff: 'Staff Engineer',
  senior_staff: 'Senior Staff',
  principal: 'Principal Engineer',
  distinguished: 'Distinguished Engineer',
  em: 'Engineering Manager',
  sr_em: 'Senior EM',
  director: 'Director',
}

const QUARTER_MONTH_LABELS: Record<1 | 2 | 3 | 4, string> = {
  1: 'Jan-Mar',
  2: 'Apr-Jun',
  3: 'Jul-Sep',
  4: 'Oct-Dec',
}

export interface QuarterOption {
  value: string  // canonical 'YYYY-QN'
  label: string  // friendly 'YYYY QN (Mon-Mon)'
}

/** Return the canonical 'YYYY-QN' string for the given Date. */
export function currentQuarter(now: Date): string {
  const year = now.getUTCFullYear()
  const quarter = Math.floor(now.getUTCMonth() / 3) + 1
  return `${year}-Q${quarter}`
}

/** Spec §8.3 / D-4 — current quarter + 7 future quarters as dropdown options. */
export function quarterOptions(now: Date, futureCount = 7): QuarterOption[] {
  let year = now.getUTCFullYear()
  let q = (Math.floor(now.getUTCMonth() / 3) + 1) as 1 | 2 | 3 | 4
  const out: QuarterOption[] = []
  for (let i = 0; i <= futureCount; i++) {
    out.push({
      value: `${year}-Q${q}`,
      label: `${year} Q${q} (${QUARTER_MONTH_LABELS[q]})`,
    })
    q = (q === 4 ? 1 : q + 1) as 1 | 2 | 3 | 4
    if (q === 1) year += 1
  }
  return out
}

export function quarterLabel(value: string): string {
  const m = /^(\d{4})-Q([1-4])$/.exec(value)
  if (!m) return value
  const q = Number(m[2]) as 1 | 2 | 3 | 4
  return `${m[1]} Q${q} (${QUARTER_MONTH_LABELS[q]})`
}
