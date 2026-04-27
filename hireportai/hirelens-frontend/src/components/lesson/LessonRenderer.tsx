/**
 * LessonRenderer — four-section lesson card (slice 6.3 spec §8.1).
 *
 * Sections: concept_md / production_md / examples_md / quiz panel.
 * Concept is expanded by default on mobile; production / examples
 * collapse-by-default with a toggle that fires `lesson_section_expanded`.
 * The desktop layout (`md:` and up) renders all sections expanded.
 *
 * Markdown rendering via `react-markdown` + `remark-gfm`. Default
 * sanitization is sufficient for fixture-authored content (OQ-1);
 * rehype-sanitize revisited at slice 6.4 admin authoring.
 */
import { useState, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { capture } from '@/utils/posthog'
import type { LessonWithQuizzes } from '@/types'
import { QuizItemPanel } from './QuizItemPanel'

type SectionKey = 'concept' | 'production' | 'examples' | 'quiz'

interface SectionProps {
  lessonId: string
  sectionKey: SectionKey
  title: string
  defaultExpanded: boolean
  children: ReactNode
}

function Section({
  lessonId,
  sectionKey,
  title,
  defaultExpanded,
  children,
}: SectionProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const toggle = () => {
    const next = !expanded
    setExpanded(next)
    if (next) {
      capture('lesson_section_expanded', {
        lesson_id: lessonId,
        section: sectionKey,
      })
    }
  }
  return (
    <section
      className="border-b border-border-default last:border-b-0 py-4 md:py-6"
      aria-label={title}
    >
      <button
        type="button"
        onClick={toggle}
        className="md:hidden flex items-center justify-between w-full text-left"
        aria-expanded={expanded}
      >
        <h2 className="text-h3 font-display text-text-primary">{title}</h2>
        {expanded ? (
          <ChevronUp size={20} className="text-text-muted" />
        ) : (
          <ChevronDown size={20} className="text-text-muted" />
        )}
      </button>
      <h2 className="hidden md:block text-h3 font-display text-text-primary mb-3">
        {title}
      </h2>
      {(expanded || isDesktopFirstPaint()) && (
        <div className={`mt-3 md:mt-0 ${expanded ? '' : 'hidden md:block'}`}>
          {children}
        </div>
      )}
    </section>
  )
}

// Desktop renders all sections expanded regardless of mobile collapse
// state. We use a CSS-class approach (hidden md:block) so the SSR-equivalent
// initial paint matches; this helper just exists to make the JSX read cleanly.
function isDesktopFirstPaint(): boolean {
  return true
}

interface LessonRendererProps {
  lesson: LessonWithQuizzes
  sessionId: string
}

export function LessonRenderer({ lesson, sessionId }: LessonRendererProps) {
  const { lesson: body, quiz_items } = lesson
  return (
    <article className="max-w-3xl mx-auto px-4 md:px-6">
      <header className="py-6 md:py-8 border-b border-border-default">
        <p className="text-sm text-text-muted">{lesson.deck_title}</p>
        <h1 className="text-h1 font-display text-text-primary mt-1">
          {body.title}
        </h1>
      </header>

      <Section
        lessonId={body.id}
        sectionKey="concept"
        title="Concept"
        defaultExpanded={true}
      >
        <div className="prose prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {body.concept_md}
          </ReactMarkdown>
        </div>
      </Section>

      <Section
        lessonId={body.id}
        sectionKey="production"
        title="Production"
        defaultExpanded={false}
      >
        <div className="prose prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {body.production_md}
          </ReactMarkdown>
        </div>
      </Section>

      <Section
        lessonId={body.id}
        sectionKey="examples"
        title="Examples"
        defaultExpanded={false}
      >
        <div className="prose prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {body.examples_md}
          </ReactMarkdown>
        </div>
      </Section>

      <Section
        lessonId={body.id}
        sectionKey="quiz"
        title="Check your understanding"
        defaultExpanded={false}
      >
        {quiz_items.length === 0 ? (
          <p className="text-text-muted">No quiz items for this lesson yet.</p>
        ) : (
          <div className="space-y-6">
            {quiz_items.map((qi) => (
              <QuizItemPanel
                key={qi.id}
                quizItem={qi}
                sessionId={sessionId}
              />
            ))}
          </div>
        )}
      </Section>
    </article>
  )
}
