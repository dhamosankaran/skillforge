/**
 * Cover Letter Viewer tests — spec #52 AC-6 + slice 2 FE migration.
 *
 * Locks the structured-render contract (LD-2 shape, no ReactMarkdown) and
 * the copy/TXT flow's use of `full_text` rather than a reassembled string.
 */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { CoverLetterViewer } from '@/components/rewrite/CoverLetterViewer'
import type { CoverLetterResponse } from '@/types'

const SAMPLE: CoverLetterResponse = {
  date: 'April 21, 2026',
  recipient: { name: 'Hiring Manager', company: 'Acme Robotics' },
  greeting: 'Dear Hiring Manager,',
  body_paragraphs: [
    'HOOK: I am writing to apply for the Staff Software Engineer role at Acme Robotics.',
    'FIT: In my most recent role I led a 40% reduction in P50 latency by redesigning our async pipeline.',
    'CLOSE: I would welcome the chance to discuss how my experience maps to your roadmap.',
  ],
  signoff: 'Sincerely,',
  signature: 'Jordan Doe',
  tone: 'professional',
  full_text:
    'April 21, 2026\n\n' +
    'Hiring Manager\nAcme Robotics\n\n' +
    'Dear Hiring Manager,\n\n' +
    'HOOK: ...\n\nFIT: ...\n\nCLOSE: ...\n\n' +
    'Sincerely,\nJordan Doe',
}

describe('CoverLetterViewer — structured rendering (spec #52 AC-6)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the 8 canonical blocks as distinct DOM nodes', () => {
    render(<CoverLetterViewer coverLetter={SAMPLE} isLoading={false} onGenerate={() => {}} />)

    expect(screen.getByTestId('cl-date')).toHaveTextContent('April 21, 2026')
    expect(screen.getByTestId('cl-recipient')).toHaveTextContent('Hiring Manager')
    expect(screen.getByTestId('cl-recipient')).toHaveTextContent('Acme Robotics')
    expect(screen.getByTestId('cl-greeting')).toHaveTextContent('Dear Hiring Manager,')
    expect(screen.getByTestId('cl-body-0')).toHaveTextContent(/HOOK:/)
    expect(screen.getByTestId('cl-body-1')).toHaveTextContent(/FIT:/)
    expect(screen.getByTestId('cl-body-2')).toHaveTextContent(/CLOSE:/)
    expect(screen.getByTestId('cl-signoff')).toHaveTextContent('Sincerely,')
    expect(screen.getByTestId('cl-signature')).toHaveTextContent('Jordan Doe')
  })

  it('renders each body paragraph in its own <p> element', () => {
    render(<CoverLetterViewer coverLetter={SAMPLE} isLoading={false} onGenerate={() => {}} />)
    const paragraphs = [0, 1, 2].map((i) => screen.getByTestId(`cl-body-${i}`))
    for (const node of paragraphs) {
      expect(node.tagName).toBe('P')
    }
  })

  it('does not use ReactMarkdown (AC-6): no markdown-produced artifacts in the render tree', () => {
    const { container } = render(
      <CoverLetterViewer coverLetter={SAMPLE} isLoading={false} onGenerate={() => {}} />
    )
    // ReactMarkdown would wrap body text in rehype-generated elements
    // with specific prop patterns. The structured path renders the 8
    // blocks via plain <div>/<p> tagged with our data-testid scheme —
    // a markdown root would violate that invariant.
    expect(container.querySelector('[data-markdown-root]')).toBeNull()
    // Ensure no stray ## headers leak through as rendered <h2> with the
    // markdown-sourced ## prefix retained.
    const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6')
    for (const h of headings) {
      expect(h.textContent?.startsWith('##')).not.toBe(true)
    }
  })

  it('copy button writes full_text to the clipboard (LD-7)', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })

    render(<CoverLetterViewer coverLetter={SAMPLE} isLoading={false} onGenerate={() => {}} />)
    await userEvent.click(screen.getByLabelText('Copy cover letter'))

    expect(writeText).toHaveBeenCalledTimes(1)
    expect(writeText).toHaveBeenCalledWith(SAMPLE.full_text)
  })
})
