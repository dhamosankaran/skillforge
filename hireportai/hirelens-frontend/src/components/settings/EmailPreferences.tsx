/**
 * Email Preferences card — daily reminder toggle + timezone picker.
 *
 * Loads current prefs on mount, lets the user toggle daily_reminder
 * and choose a timezone, then saves via PUT /api/v1/email-preferences.
 */
import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Mail, Check } from 'lucide-react'
import { fetchEmailPreferences, updateEmailPreferences } from '@/services/api'
import { capture } from '@/utils/posthog'
import type { EmailPreference } from '@/types'

const COMMON_TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Berlin',
  'Europe/Paris',
  'Asia/Kolkata',
  'Asia/Shanghai',
  'Asia/Tokyo',
  'Australia/Sydney',
  'Pacific/Auckland',
]

export function EmailPreferences() {
  const [prefs, setPrefs] = useState<EmailPreference | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    capture('email_preferences_viewed')
    fetchEmailPreferences()
      .then(setPrefs)
      .catch(() => setError('Failed to load email preferences'))
      .finally(() => setLoading(false))
  }, [])

  async function handleToggle() {
    if (!prefs) return
    const newVal = !prefs.daily_reminder
    setSaving(true)
    try {
      const updated = await updateEmailPreferences({ daily_reminder: newVal })
      setPrefs(updated)
      capture('email_preferences_saved', { daily_reminder: newVal })
      flashSaved()
    } catch {
      setError('Failed to update preferences')
    } finally {
      setSaving(false)
    }
  }

  async function handleTimezoneChange(tz: string) {
    if (!prefs) return
    setSaving(true)
    try {
      const updated = await updateEmailPreferences({ timezone: tz })
      setPrefs(updated)
      capture('email_preferences_saved', { timezone: tz })
      flashSaved()
    } catch {
      setError('Failed to update timezone')
    } finally {
      setSaving(false)
    }
  }

  function flashSaved() {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  if (loading) {
    return (
      <div className="rounded-2xl border border-contrast/[0.08] bg-bg-surface/60 p-5">
        <p className="text-[11px] text-text-muted">Loading email preferences...</p>
      </div>
    )
  }

  if (error && !prefs) {
    return (
      <div className="rounded-2xl border border-contrast/[0.08] bg-bg-surface/60 p-5">
        <p className="text-[11px] text-danger">{error}</p>
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-contrast/[0.08] bg-bg-surface/60 p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Mail size={14} className="text-accent-primary" />
          <span className="text-[11px] uppercase tracking-[0.15em] text-text-secondary font-semibold">
            Email Notifications
          </span>
        </div>
        {saved && (
          <motion.span
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-1 text-[11px] text-success"
          >
            <Check size={12} /> Saved
          </motion.span>
        )}
      </div>

      {/* Toggle */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-text-primary">Daily Reminders</p>
          <p className="text-[11px] text-text-muted">
            Get notified when you have cards due
          </p>
        </div>
        <button
          onClick={handleToggle}
          disabled={saving}
          className={
            'relative w-11 h-6 rounded-full transition-colors duration-200 ' +
            (prefs?.daily_reminder
              ? 'bg-accent-primary'
              : 'bg-contrast/[0.12]')
          }
          aria-label="Toggle daily reminders"
        >
          <span
            className={
              'absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform duration-200 ' +
              (prefs?.daily_reminder ? 'translate-x-5' : 'translate-x-0')
            }
          />
        </button>
      </div>

      {/* Timezone picker (only shown when reminders are on) */}
      {prefs?.daily_reminder && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="space-y-1"
        >
          <label
            htmlFor="tz-select"
            className="text-[11px] text-text-muted"
          >
            Timezone
          </label>
          <select
            id="tz-select"
            value={prefs.timezone}
            onChange={(e) => handleTimezoneChange(e.target.value)}
            disabled={saving}
            className="w-full rounded-lg border border-contrast/[0.08] bg-bg-elevated px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-primary/50"
          >
            {COMMON_TIMEZONES.map((tz) => (
              <option key={tz} value={tz}>
                {tz.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </motion.div>
      )}
    </div>
  )
}
