/**
 * Lesson — page mounted at /learn/lesson/:id (slice 6.3 D-8).
 *
 * Persona-gated via App.tsx's <ProtectedRoute>. Eager-loaded inside
 * the existing /learn/* block (D-10). Fires `lesson_viewed` once on
 * successful load (idempotent via useRef, mirrors the
 * `home_dashboard_viewed` precedent).
 */
import { useEffect, useMemo, useRef } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useUsage } from '@/context/UsageContext'
import { useLesson } from '@/hooks/useLesson'
import { LessonRenderer } from '@/components/lesson/LessonRenderer'
import { recordLessonView } from '@/services/api'
import { capture } from '@/utils/posthog'

function generateSessionId(): string {
  // crypto.randomUUID is available in modern browsers + happy-dom.
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `sess-${Math.random().toString(36).slice(2)}-${Date.now()}`
}

export default function LessonPage() {
  const { id } = useParams<{ id: string }>()
  const { lesson, isLoading, error } = useLesson(id)
  const { user } = useAuth()
  const { usage } = useUsage()
  const sessionId = useMemo(generateSessionId, [])
  const hasFiredViewed = useRef(false)

  useEffect(() => {
    if (lesson && !hasFiredViewed.current) {
      hasFiredViewed.current = true
      capture('lesson_viewed', {
        lesson_id: lesson.lesson.id,
        deck_id: lesson.deck_id,
        deck_slug: lesson.deck_slug,
        version: lesson.lesson.version,
        persona: user?.persona ?? null,
        plan: usage.plan,
      })
      // Slice 6.0 D-10 — Postgres dual-write of lesson_viewed.
      recordLessonView(lesson.lesson.id, {
        deck_id: lesson.deck_id,
        version: lesson.lesson.version,
        session_id: sessionId,
      }).catch(() => {
        // best-effort: see spec §6.4 + D-7
      })
    }
  }, [lesson, user?.persona, usage.plan, sessionId])

  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center min-h-[60vh]"
        role="status"
        aria-label="Loading lesson"
      >
        <Loader2 size={24} className="animate-spin text-text-muted" />
      </div>
    )
  }

  if (error === 'not_found' || !lesson) {
    return (
      <div className="max-w-xl mx-auto px-4 py-12 text-center">
        <h1 className="text-h2 font-display text-text-primary mb-2">
          Lesson not found
        </h1>
        <p className="text-text-muted mb-6">
          We couldn't find that lesson. It may have been retired or never
          existed.
        </p>
        <Link
          to="/learn"
          className="inline-block px-4 py-2 rounded border border-border-accent text-text-primary hover:bg-bg-elevated"
        >
          Back to Learn
        </Link>
      </div>
    )
  }

  if (error === 'network') {
    return (
      <div className="max-w-xl mx-auto px-4 py-12 text-center">
        <h1 className="text-h2 font-display text-text-primary mb-2">
          We couldn't load this lesson
        </h1>
        <p className="text-text-muted mb-6">
          Check your connection and try again.
        </p>
        <Link
          to="/learn"
          className="inline-block px-4 py-2 rounded border border-border-accent text-text-primary hover:bg-bg-elevated"
        >
          Back to Learn
        </Link>
      </div>
    )
  }

  return <LessonRenderer lesson={lesson} sessionId={sessionId} />
}
