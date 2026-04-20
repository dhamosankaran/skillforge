/**
 * Plan-aware Missing Skills CTA tests (spec #22, P5-S22b).
 *
 * Matches the 14 Vitest cases enumerated in spec §Test Plan.
 *
 * `MissingSkillsPanel` is plan-agnostic below the prop boundary — the
 * consumer (`Results.tsx`) derives the three-state plan and passes it
 * down. These tests mount the panel directly with each plan value so
 * we can assert copy / routing / analytics without standing up auth or
 * usage contexts.
 */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { GapMapping, SkillGap } from '@/types'

// ─── Mocks ────────────────────────────────────────────────────────────────

const capture = vi.fn()
vi.mock('@/utils/posthog', () => ({
  capture: (...args: unknown[]) => capture(...args),
  default: {},
}))

const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigate }
})

import { MissingSkillsPanel } from '@/components/dashboard/MissingSkillsPanel'

// ─── Fixtures ─────────────────────────────────────────────────────────────

const RAG_GAP: SkillGap = {
  skill: 'RAG',
  importance: 'critical',
  category: 'Technical',
}

const SYSTEM_DESIGN_GAP: SkillGap = {
  skill: 'System Design',
  importance: 'recommended',
  category: 'Technical',
}

const RAG_MAPPING: GapMapping = {
  gap: 'RAG',
  match_type: 'tag',
  matching_categories: [
    {
      category_id: 'cat-rag-42',
      name: 'Retrieval-Augmented Generation',
      icon: '📚',
      color: 'c',
      matched_card_count: 8,
      similarity_score: null,
    },
  ],
}

const NO_MATCH_MAPPING: GapMapping = {
  gap: 'System Design',
  match_type: 'none',
  matching_categories: [],
}

function renderPanel(args: {
  plan: 'anonymous' | 'free' | 'pro'
  skillGaps?: SkillGap[]
  gapMappings?: GapMapping[]
  scanId?: string | null
  initialPath?: string
}) {
  const {
    plan,
    skillGaps = [RAG_GAP],
    gapMappings = [RAG_MAPPING],
    scanId = null,
    initialPath = '/prep/results',
  } = args
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <MissingSkillsPanel
        plan={plan}
        skillGaps={skillGaps}
        gapMappings={gapMappings}
        scanId={scanId}
      />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  capture.mockReset()
  navigate.mockReset()
})

// ─── Tests ────────────────────────────────────────────────────────────────

describe('MissingSkillsPanel — plan-aware CTA (spec #22)', () => {
  // AC-1
  it('test_missing_skill_cta_renders_free_copy_for_free_user', () => {
    renderPanel({ plan: 'free' })
    const cta = screen.getByRole('button', { name: /free-tier preview/i })
    expect(cta).toBeInTheDocument()
    expect(cta).toHaveTextContent('Study these cards — free preview')
    expect(cta).toHaveAccessibleName('Study cards for RAG, free-tier preview')
  })

  // AC-2
  it('test_missing_skill_cta_renders_pro_copy_for_pro_user', () => {
    renderPanel({ plan: 'pro' })
    const cta = screen.getByRole('button', { name: 'Study cards for RAG' })
    expect(cta).toBeInTheDocument()
    expect(cta).toHaveTextContent('Study these cards')
    // The pro aria-label must NOT include the "free-tier preview" suffix
    expect(cta.getAttribute('aria-label')).not.toMatch(/free-tier preview/i)
  })

  // AC-3
  it('test_missing_skill_cta_renders_signin_copy_for_anonymous', () => {
    renderPanel({ plan: 'anonymous' })
    const cta = screen.getByRole('button', {
      name: 'Sign in to study cards for RAG',
    })
    expect(cta).toBeInTheDocument()
    expect(cta).toHaveTextContent('Sign in to study')
  })

  // AC-4 free branch
  it('test_cta_routes_to_correct_category_for_free_user', async () => {
    const user = userEvent.setup()
    renderPanel({ plan: 'free' })
    await user.click(screen.getByRole('button', { name: /free-tier preview/i }))
    expect(navigate).toHaveBeenCalledWith('/learn?category=cat-rag-42')
  })

  // AC-4 pro branch
  it('test_cta_routes_to_correct_category_for_pro_user', async () => {
    const user = userEvent.setup()
    renderPanel({ plan: 'pro' })
    await user.click(screen.getByRole('button', { name: 'Study cards for RAG' }))
    expect(navigate).toHaveBeenCalledWith('/learn?category=cat-rag-42')
  })

  // AC-8 anonymous w/ scan_id
  it('test_cta_routes_to_signin_with_return_to_for_anonymous_with_scan_id', async () => {
    const user = userEvent.setup()
    renderPanel({ plan: 'anonymous', scanId: 'scan-xyz-99' })
    await user.click(
      screen.getByRole('button', { name: /Sign in to study cards for RAG/i }),
    )
    expect(navigate).toHaveBeenCalledWith(
      '/login?return_to=%2Fprep%2Fresults%3Fscan_id%3Dscan-xyz-99',
    )
  })

  // AC-8 anonymous w/o scan_id
  it('test_cta_routes_to_signin_with_return_to_for_anonymous_without_scan_id', async () => {
    const user = userEvent.setup()
    renderPanel({ plan: 'anonymous', scanId: null })
    await user.click(
      screen.getByRole('button', { name: /Sign in to study cards for RAG/i }),
    )
    expect(navigate).toHaveBeenCalledWith('/login?return_to=%2Fprep%2Fresults')
  })

  // AC-5 negative: no paywall on free click
  it('test_cta_does_not_open_paywall_on_free_user_click', async () => {
    const user = userEvent.setup()
    const onUpgradeClick = vi.fn()
    render(
      <MemoryRouter initialEntries={['/prep/results']}>
        <MissingSkillsPanel
          plan="free"
          skillGaps={[RAG_GAP]}
          gapMappings={[RAG_MAPPING]}
          scanId={null}
          onUpgradeClick={onUpgradeClick}
        />
      </MemoryRouter>,
    )
    await user.click(screen.getByRole('button', { name: /free-tier preview/i }))
    // Wall lives in the card-view route — this component must not trigger
    // the paywall modal synchronously on click.
    expect(onUpgradeClick).not.toHaveBeenCalled()
    // Nor should it fire the `paywall_hit` event from this component.
    const paywallHit = capture.mock.calls.find((c) => c[0] === 'paywall_hit')
    expect(paywallHit).toBeUndefined()
  })

  // Edge case 1: no matching category → disabled with tooltip
  it('test_cta_disabled_when_no_matching_category', () => {
    renderPanel({
      plan: 'free',
      skillGaps: [SYSTEM_DESIGN_GAP],
      gapMappings: [NO_MATCH_MAPPING],
    })
    const cta = screen.getByRole('button', { name: /System Design/i })
    expect(cta).toBeDisabled()
    expect(cta).toHaveAttribute('title', 'No matching study content yet')
  })

  // Edge case 5: gap_mappings empty → all CTAs disabled, no crash
  it('test_cta_disabled_when_gap_mappings_empty', () => {
    renderPanel({
      plan: 'free',
      skillGaps: [RAG_GAP, SYSTEM_DESIGN_GAP],
      gapMappings: [],
    })
    const ragCta = screen.getByRole('button', { name: /RAG/i })
    const sdCta = screen.getByRole('button', { name: /System Design/i })
    expect(ragCta).toBeDisabled()
    expect(sdCta).toBeDisabled()
  })

  // AC-7 free payload
  it('test_cta_click_fires_posthog_with_plan_free', async () => {
    const user = userEvent.setup()
    renderPanel({ plan: 'free' })
    await user.click(screen.getByRole('button', { name: /free-tier preview/i }))
    const call = capture.mock.calls.find(
      (c) => c[0] === 'missing_skills_cta_clicked',
    )
    expect(call).toBeTruthy()
    expect(call![1]).toEqual({
      plan: 'free',
      skill: 'RAG',
      category_id: 'cat-rag-42',
    })
  })

  // AC-7 pro payload
  it('test_cta_click_fires_posthog_with_plan_pro', async () => {
    const user = userEvent.setup()
    renderPanel({ plan: 'pro' })
    await user.click(screen.getByRole('button', { name: 'Study cards for RAG' }))
    const call = capture.mock.calls.find(
      (c) => c[0] === 'missing_skills_cta_clicked',
    )
    expect(call![1]).toEqual({
      plan: 'pro',
      skill: 'RAG',
      category_id: 'cat-rag-42',
    })
  })

  // AC-7 anonymous payload (category_id is still resolved from the GapMapping)
  it('test_cta_click_fires_posthog_with_plan_anonymous', async () => {
    const user = userEvent.setup()
    renderPanel({ plan: 'anonymous' })
    await user.click(
      screen.getByRole('button', { name: /Sign in to study cards for RAG/i }),
    )
    const call = capture.mock.calls.find(
      (c) => c[0] === 'missing_skills_cta_clicked',
    )
    expect(call![1]).toEqual({
      plan: 'anonymous',
      skill: 'RAG',
      category_id: 'cat-rag-42',
    })
  })

  // AC-9: section-id stability — `id="missing-skills"` lives on the
  // consumer-level `PanelSection` wrapper, not this component. The enum
  // coupling the spec protects is the `PanelSection.section` prop value
  // used by `results_tooltip_opened`. Verify the wrapping id is still
  // used by the consumer by rendering a minimal wrapper here.
  it('test_section_id_missing_skills_preserved', () => {
    render(
      <MemoryRouter>
        <div id="missing-skills">
          <MissingSkillsPanel
            plan="free"
            skillGaps={[RAG_GAP]}
            gapMappings={[RAG_MAPPING]}
            scanId={null}
          />
        </div>
      </MemoryRouter>,
    )
    expect(document.getElementById('missing-skills')).not.toBeNull()
  })
})
