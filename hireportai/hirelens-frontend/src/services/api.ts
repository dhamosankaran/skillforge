import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import toast from 'react-hot-toast'
import type {
  AdminCard,
  AdminCardCreateRequest,
  AdminCardListResponse,
  AdminCardUpdateRequest,
  AdminContentQualityResponse,
  AdminDeckStatusFilter,
  AdminLessonStatusFilter,
  AdminQuizItemStatusFilter,
  AnalysisResponse,
  LoopProgressResponse,
  ScoreHistoryResponse,
  Card,
  CardDraft,
  CardImportResponse,
  CategoriesResponse,
  CoverLetterResponse,
  DailyQueueResponse,
  Deck,
  DeckCreateRequest,
  DeckUpdateRequest,
  DeckWithLessons,
  EmailPreference,
  EmailPreferenceUpdate,
  GamificationStats,
  InterviewPrepResponse,
  Lesson,
  LessonCreateRequest,
  LessonUpdateRequest,
  LessonUpdateResponse,
  LessonWithQuizzes,
  MissionCreateRequest,
  MissionDailyResponse,
  MissionDayCompleteResponse,
  MissionDetailResponse,
  MissionResponse,
  OnboardingRecommendationsResponse,
  QuizItem,
  QuizItemCreateRequest,
  QuizItemUpdateRequest,
  QuizReviewRequest,
  QuizReviewResponse,
  RankedDecksResponse,
  DashboardResponse,
  ReviewRequest,
  ReviewResponse,
  RewriteResponse,
  RewriteSection,
  ThumbsRequest,
  ThumbsResponse,
  TrackerApplication,
} from '@/types'
import {
  STORAGE_KEY_ACCESS,
  STORAGE_KEY_REFRESH,
  type AuthUser,
  type Persona,
} from '@/context/AuthContext'

const STORAGE_KEY_USER = 'skillforge_user'
const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000, // 2 min for analysis
})

// ─── Request interceptor: inject Bearer token ─────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(STORAGE_KEY_ACCESS)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ─── Refresh state (module-level, not per-render) ─────────────────────────
let isRefreshing = false
let pendingQueue: Array<{
  resolve: (token: string) => void
  reject: (err: unknown) => void
}> = []

function processQueue(error: unknown, token: string | null = null) {
  pendingQueue.forEach((p) => {
    if (error) p.reject(error)
    else p.resolve(token!)
  })
  pendingQueue = []
}

function clearAuthAndRedirect() {
  localStorage.removeItem(STORAGE_KEY_ACCESS)
  localStorage.removeItem(STORAGE_KEY_REFRESH)
  localStorage.removeItem(STORAGE_KEY_USER)
  window.location.href = '/'
}

// ─── Response interceptor: silent refresh on 401, toast other errors ──────
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ error?: unknown; detail?: unknown }>) => {
    const original = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean
    }

    if (error.response?.status === 401 && original && !original._retry) {
      if (isRefreshing) {
        // Another refresh is already in flight — queue this request.
        return new Promise<string>((resolve, reject) => {
          pendingQueue.push({ resolve, reject })
        }).then((newToken) => {
          original.headers['Authorization'] = `Bearer ${newToken}`
          return api(original)
        })
      }

      original._retry = true
      isRefreshing = true

      const refreshToken = localStorage.getItem(STORAGE_KEY_REFRESH)
      if (!refreshToken) {
        processQueue(error)
        isRefreshing = false
        clearAuthAndRedirect()
        return Promise.reject(error)
      }

      try {
        const { data } = await axios.post<{ access_token: string }>(
          `${BASE_URL}/api/v1/auth/refresh`,
          { refresh_token: refreshToken }
        )
        const newToken = data.access_token
        localStorage.setItem(STORAGE_KEY_ACCESS, newToken)
        processQueue(null, newToken)
        isRefreshing = false
        original.headers['Authorization'] = `Bearer ${newToken}`
        return api(original)
      } catch (refreshErr) {
        processQueue(refreshErr)
        isRefreshing = false
        clearAuthAndRedirect()
        return Promise.reject(refreshErr)
      }
    }

    // Non-401 (or already-retried 401) — show toast.
    if (error.response?.status !== 401) {
      const status = error.response?.status
      const data = error.response?.data
      const detail = data?.detail

      // Spec #50 / #42: 402 with a structured `detail.trigger` payload is
      // component-owned UX (PaywallModal / WallInlineNudge via
      // QuizPanel.extractWallPayload). The interceptor stays silent so the
      // wall surface can render without a cryptic toast leaking through.
      const isWallPayload =
        status === 402 &&
        typeof detail === 'object' &&
        detail !== null &&
        typeof (detail as { trigger?: unknown }).trigger === 'string'

      if (!isWallPayload) {
        // Object-coercion guard: `detail` may be a FastAPI-style error dict
        // (e.g. validation errors). Passing one to toast.error renders
        // "[object Object]". Only toast strings; fall back to error.message
        // or a safe default when `error`/`detail` are objects.
        const rawError = typeof data?.error === 'string' ? data.error : undefined
        const rawDetail = typeof detail === 'string' ? detail : undefined
        const message =
          rawError || rawDetail || error.message || 'An unexpected error occurred'
        toast.error(message)
      }
    }
    return Promise.reject(error)
  }
)

// ─── Feature API calls ─────────────────────────────────────────────────────

export async function analyzeResume(
  file: File,
  jobDescription: string
): Promise<AnalysisResponse> {
  const formData = new FormData()
  formData.append('resume_file', file)
  formData.append('job_description', jobDescription)

  const response = await api.post<AnalysisResponse>('/api/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

/** Spec #59 — fetch a previously-persisted scan by id. Used by Results.tsx
 *  to hydrate when the user lands on /prep/results?scan_id=... on a
 *  fresh session (in-memory AnalysisContext is empty). 404 for unknown
 *  or non-owner scans; 410 for legacy scans where analysis_payload is NULL. */
export async function fetchScanById(scanId: string): Promise<AnalysisResponse> {
  const response = await api.get<AnalysisResponse>(
    `/api/v1/analyze/${encodeURIComponent(scanId)}`,
  )
  return response.data
}

export async function rewriteResume(
  resumeText: string,
  jdText: string,
  templateType?: string,
  major?: string
): Promise<RewriteResponse> {
  const response = await api.post<RewriteResponse>('/api/rewrite', {
    resume_text: resumeText,
    job_description: jdText,
    template_type: templateType || null,
    major: major || null,
  })
  return response.data
}

export interface RewriteSectionResponse {
  section_id: string
  section: RewriteSection
}

export async function rewriteSection(
  sectionId: string,
  sectionTitle: string,
  sectionText: string,
  jdText: string,
  missingKeywords?: string[]
): Promise<RewriteSectionResponse> {
  const response = await api.post<RewriteSectionResponse>('/api/v1/rewrite/section', {
    section_id: sectionId,
    section_title: sectionTitle,
    section_text: sectionText,
    jd_text: jdText,
    missing_keywords: missingKeywords ?? null,
  })
  return response.data
}

export interface ResumeTemplate {
  id: string
  name: string
  description: string
}

export async function getRewriteTemplates(): Promise<ResumeTemplate[]> {
  const response = await api.get<ResumeTemplate[]>('/api/rewrite/templates')
  return response.data
}

export async function generateCoverLetter(
  resumeText: string,
  jdText: string,
  tone: string
): Promise<CoverLetterResponse> {
  const response = await api.post<CoverLetterResponse>('/api/cover-letter', {
    resume_text: resumeText,
    job_description: jdText,
    tone,
  })
  return response.data
}

export async function generateInterviewPrep(
  resumeText: string,
  jdText: string,
  options?: { forceRegenerate?: boolean }
): Promise<InterviewPrepResponse> {
  const body: Record<string, unknown> = {
    resume_text: resumeText,
    job_description: jdText,
  }
  if (options?.forceRegenerate) body.force_regenerate = true
  const response = await api.post<InterviewPrepResponse>('/api/interview-prep', body)
  return response.data
}

export async function getApplications(): Promise<TrackerApplication[]> {
  const response = await api.get<TrackerApplication[]>('/api/v1/tracker')
  return response.data
}

export async function fetchUserApplications(): Promise<TrackerApplication[]> {
  const response = await api.get<TrackerApplication[]>('/api/v1/tracker')
  return response.data
}

export async function createApplication(
  data: Omit<TrackerApplication, 'id' | 'created_at'>
): Promise<TrackerApplication> {
  const response = await api.post<TrackerApplication>('/api/v1/tracker', data)
  return response.data
}

export async function updateApplication(
  id: string,
  data: Partial<Omit<TrackerApplication, 'id' | 'created_at'>>
): Promise<TrackerApplication> {
  const response = await api.patch<TrackerApplication>(`/api/v1/tracker/${id}`, data)
  return response.data
}

export async function deleteApplication(id: string): Promise<void> {
  await api.delete(`/api/v1/tracker/${id}`)
}

// ─── Study / Cards ────────────────────────────────────────────────────────────

/**
 * Fetch all categories visible to the authenticated user with per-user
 * progress counts.
 *
 * Currently calls GET /api/v1/cards which plan-gates the response
 * (free users only receive foundation categories). When the dashboard
 * endpoint (GET /api/v1/study/dashboard) is deployed, swap the URL here
 * to receive all categories with locked flags and studied_count data.
 */
export async function fetchCategories(): Promise<CategoriesResponse> {
  const response = await api.get<CategoriesResponse>('/api/v1/cards')
  return response.data
}

export async function fetchDailyQueue(): Promise<DailyQueueResponse> {
  const response = await api.get<DailyQueueResponse>('/api/v1/study/daily')
  return response.data
}

// Phase 6 slice 6.7 — Lens-ranked decks consumer (spec #08 §5.1).
// BE route shipped in slice 6.6 (`5011518`). Optional query params per
// spec #07 §12 D-14 defaults (`lookback_days=30`, `max_scans=5`).
export interface FetchRankedDecksOptions {
  lookback_days?: number
  max_scans?: number
}

export async function fetchRankedDecks(
  opts: FetchRankedDecksOptions = {},
): Promise<RankedDecksResponse> {
  const response = await api.get<RankedDecksResponse>(
    '/api/v1/learn/ranked-decks',
    { params: opts },
  )
  return response.data
}

// Phase 6 slice 6.8 — User-self FSRS dashboard consumer (spec #09 §6.2 + §12 D-3 / D-14).
export interface FetchFsrsDashboardOptions {
  retention_window_days?: number
}

export async function fetchFsrsDashboard(
  opts: FetchFsrsDashboardOptions = {},
): Promise<DashboardResponse> {
  const response = await api.get<DashboardResponse>(
    '/api/v1/learn/dashboard',
    { params: opts },
  )
  return response.data
}

export async function fetchCard(id: string): Promise<Card> {
  const response = await api.get<Card>(`/api/v1/cards/${id}`)
  return response.data
}

export interface CategoryCardsResponse {
  category: {
    id: string
    name: string
    icon: string
    color: string
    display_order: number
    source: 'foundation' | 'premium'
  }
  cards: Card[]
  total: number
}

export async function fetchCardsByCategory(
  categoryId: string,
): Promise<CategoryCardsResponse> {
  const response = await api.get<CategoryCardsResponse>(
    `/api/v1/cards/category/${categoryId}`,
  )
  return response.data
}

export async function submitReview(req: ReviewRequest): Promise<ReviewResponse> {
  const response = await api.post<ReviewResponse>('/api/v1/study/review', req)
  return response.data
}

// ─── Phase 6 — Lessons / Decks (slice 6.3) ───────────────────────────────────

export async function fetchLesson(lessonId: string): Promise<LessonWithQuizzes> {
  const response = await api.get<LessonWithQuizzes>(`/api/v1/lessons/${lessonId}`)
  return response.data
}

// Slice 6.0 §6.4 — Postgres dual-write of `lesson_viewed`. Best-effort
// fire-and-forget (D-7); errors are swallowed silently so analytics never
// surfaces a UI error. PostHog `capture('lesson_viewed', ...)` continues to
// fire from `pages/Lesson.tsx` alongside this call.
export async function recordLessonView(
  lessonId: string,
  body: { deck_id: string; version: number; session_id: string },
): Promise<void> {
  try {
    await api.post(
      `/api/v1/lessons/${encodeURIComponent(lessonId)}/view-event`,
      body,
    )
  } catch {
    // best-effort: see spec §6.4 + D-7
  }
}

// Slice 6.13.5b — user-thumbs submit. Surfaces non-2xx as exceptions so
// callers (`useThumbs.mutate`) can revert optimistic state. Lesson-level
// only v1 per spec #12 §12 D-7.
export async function submitThumbs(
  lessonId: string,
  body: ThumbsRequest,
): Promise<ThumbsResponse> {
  const response = await api.post<ThumbsResponse>(
    `/api/v1/lessons/${encodeURIComponent(lessonId)}/thumbs`,
    body,
  )
  return response.data
}

export async function fetchDeck(deckId: string): Promise<Deck> {
  const response = await api.get<Deck>(`/api/v1/decks/${deckId}`)
  return response.data
}

export async function fetchDeckLessons(deckId: string): Promise<DeckWithLessons> {
  const response = await api.get<DeckWithLessons>(`/api/v1/decks/${deckId}/lessons`)
  return response.data
}

export async function submitQuizReview(req: QuizReviewRequest): Promise<QuizReviewResponse> {
  const response = await api.post<QuizReviewResponse>('/api/v1/quiz-items/review', req)
  return response.data
}

// ─── Mission Mode ────────────────────────────────────────────────────────────

export async function createMission(req: MissionCreateRequest): Promise<MissionResponse> {
  const response = await api.post<MissionResponse>('/api/v1/missions/create', req)
  return response.data
}

export async function fetchActiveMission(): Promise<MissionDetailResponse> {
  const response = await api.get<MissionDetailResponse>('/api/v1/missions/active')
  return response.data
}

export async function fetchMissionDaily(): Promise<MissionDailyResponse> {
  const response = await api.get<MissionDailyResponse>('/api/v1/missions/daily')
  return response.data
}

export async function completeMissionDay(): Promise<MissionDayCompleteResponse> {
  const response = await api.post<MissionDayCompleteResponse>('/api/v1/missions/complete-day')
  return response.data
}

// ─── Gamification — XP, streaks, badges ──────────────────────────────────────

/** Fetch the caller's gamification stats: streak, XP, badges. */
export async function fetchGamificationStats(): Promise<GamificationStats> {
  const response = await api.get<GamificationStats>(
    '/api/v1/gamification/stats',
  )
  return response.data
}

// ─── Home dashboard — state-aware widgets (P5-S18c, spec #40) ────────────────

import type { HomeStateResponse } from '@/types/homeState'

export async function fetchHomeState(): Promise<HomeStateResponse> {
  const response = await api.get<HomeStateResponse>('/api/v1/home/state')
  return response.data
}

// ─── Email Preferences ──────────────────────────────────────────────────────

export async function fetchEmailPreferences(): Promise<EmailPreference> {
  const response = await api.get<EmailPreference>('/api/v1/email-preferences')
  return response.data
}

export async function updateEmailPreferences(
  data: EmailPreferenceUpdate,
): Promise<EmailPreference> {
  const response = await api.put<EmailPreference>('/api/v1/email-preferences', data)
  return response.data
}

// ─── Experience Generator ─────────────────────────────────────────────────────

export interface ExperienceRequest {
  topic?: string
}

export interface ExperienceResponse {
  experience_text: string
  summary: string
  cards_studied: number
}

export async function generateExperience(
  req: ExperienceRequest = {},
): Promise<ExperienceResponse> {
  const response = await api.post<ExperienceResponse>(
    '/api/v1/study/experience',
    req,
  )
  return response.data
}

// ─── Card Feedback ────────────────────────────────────────────────────────────

export interface CardFeedbackRequest {
  vote: 'up' | 'down'
  comment?: string
}

export interface CardFeedbackResponse {
  id: string
  user_id: string
  card_id: string
  vote: string
  comment: string | null
  created_at: string
}

export async function submitCardFeedback(
  cardId: string,
  req: CardFeedbackRequest,
): Promise<CardFeedbackResponse> {
  const response = await api.post<CardFeedbackResponse>(
    `/api/v1/cards/${cardId}/feedback`,
    req,
  )
  return response.data
}

// ─── Persona picker ───────────────────────────────────────────────────────────

export interface PersonaUpdateRequest {
  persona: Persona
  interview_target_date?: string | null
  interview_target_company?: string | null
}

export async function updatePersona(req: PersonaUpdateRequest): Promise<AuthUser> {
  const response = await api.patch<AuthUser>('/api/v1/users/me/persona', req)
  return response.data
}

/**
 * Stamp `users.home_first_visit_seen_at` on first HomeDashboard mount. B-016.
 * Idempotent on the server — a repeat call is a no-op and returns the
 * existing stamp. Returns the full user dict so the caller can flip the
 * greeting copy for the current session without a re-fetch.
 */
export async function markHomeFirstVisit(): Promise<AuthUser> {
  const response = await api.post<AuthUser>('/api/v1/users/me/home-first-visit')
  return response.data
}

// ─── Onboarding — ATS gap → card bridge ───────────────────────────────────────

/**
 * Fetch recommended card categories for a list of ATS skill gaps.
 *
 * Sends `gaps` as repeated query params (`?gaps=a&gaps=b`) to match the
 * FastAPI `list[str] = Query(...)` contract. Axios's default array
 * serializer uses `gaps[]=a`, which FastAPI will NOT parse as a list,
 * so we override `paramsSerializer` inline.
 */
// ─── Payments — Stripe Checkout ──────────────────────────────────────────────

export interface PricingResponse {
  currency: string
  price: number
  price_display: string
  stripe_price_id: string
}

/** Fetch geo-based pricing for the current user's IP. */
export async function fetchPricing(): Promise<PricingResponse> {
  const response = await api.get<PricingResponse>('/api/v1/payments/pricing')
  return response.data
}

export interface CheckoutSessionResponse {
  url: string
}

/** Create a Stripe Checkout Session for Pro and return the redirect URL. */
export async function createCheckoutSession(currency?: string): Promise<CheckoutSessionResponse> {
  const response = await api.post<CheckoutSessionResponse>(
    '/api/v1/payments/checkout',
    currency ? { currency } : {},
  )
  return response.data
}

export interface BillingPortalResponse {
  url: string
}

/** Create a Stripe billing portal session (Pro-only) and return the URL. */
export async function createBillingPortalSession(): Promise<BillingPortalResponse> {
  const response = await api.post<BillingPortalResponse>('/api/v1/payments/portal')
  return response.data
}

// ─── Paywall dismissal (spec #42) ─────────────────────────────────────────────

export interface PaywallDismissResponse {
  logged: boolean
  dismissal_id: string
  dismissals_in_window: number
}

/** Log a paywall dismissal for the given trigger. LD-8 60s idempotency BE-side. */
export async function dismissPaywall(
  trigger: string,
  actionCountAtDismissal?: number | null,
): Promise<PaywallDismissResponse> {
  const response = await api.post<PaywallDismissResponse>(
    '/api/v1/payments/paywall-dismiss',
    {
      trigger,
      action_count_at_dismissal: actionCountAtDismissal ?? null,
    },
  )
  return response.data
}

export interface ShouldShowPaywallResponse {
  show: boolean
  attempts_until_next: number
}

/**
 * Ask the backend whether to render the full paywall modal or the silent
 * inline nudge for (user, trigger). Strategy A: FE tracks the grace counter
 * and passes it as `attempts_since_dismiss`.
 */
export async function shouldShowPaywall(
  trigger: string,
  attemptsSinceDismiss: number = 0,
): Promise<ShouldShowPaywallResponse> {
  const response = await api.get<ShouldShowPaywallResponse>(
    '/api/v1/payments/should-show-paywall',
    {
      params: {
        trigger,
        attempts_since_dismiss: attemptsSinceDismiss,
      },
    },
  )
  return response.data
}

// ─── Usage snapshot (spec #56 §4.3 + spec #58 §5) ─────────────────────────────

export interface UsageResponse {
  /** Actual subscription plan — never the admin role. */
  plan: 'free' | 'pro' | 'enterprise'
  /** Role flag, orthogonal to plan. Admin with plan=free has is_admin=true. */
  is_admin: boolean
  // spec #56 — scans
  scans_used: number
  /** -1 sentinel = unlimited (Pro / Enterprise / admin). */
  scans_remaining: number
  /** -1 sentinel = unlimited (Pro / Enterprise / admin). */
  max_scans: number
  // spec #58 — rewrites (shared bucket: /rewrite + /rewrite/section)
  rewrites_used: number
  rewrites_remaining: number
  rewrites_max: number
  // spec #58 — cover letters (separate bucket)
  cover_letters_used: number
  cover_letters_remaining: number
  cover_letters_max: number
  // spec #49 §3.4 — interview_prep monthly cap (free = 3/month).
  interview_preps_used: number
  interview_preps_remaining: number
  interview_preps_max: number
}

/** Lifetime usage snapshot for the current user (spec #56 §4.3 + spec #58 §5). */
export async function fetchUsage(): Promise<UsageResponse> {
  const response = await api.get<UsageResponse>('/api/v1/payments/usage')
  return response.data
}

export interface ChecklistStep {
  id: string
  title: string
  description: string
  link_target: string
  complete: boolean
}

export interface ChecklistResponse {
  steps: ChecklistStep[]
  all_complete: boolean
  completed_at: string | null
}

/** Interview-Prepper onboarding checklist (Spec #41). */
export async function fetchOnboardingChecklist(): Promise<ChecklistResponse> {
  const response = await api.get<ChecklistResponse>('/api/v1/onboarding/checklist')
  return response.data
}

export async function fetchOnboardingRecommendations(
  gaps: string[],
  scanId?: string,
): Promise<OnboardingRecommendationsResponse> {
  const response = await api.get<OnboardingRecommendationsResponse>(
    '/api/v1/onboarding/recommendations',
    {
      params: { gaps, ...(scanId ? { scan_id: scanId } : {}) },
      paramsSerializer: (params) => {
        const parts: string[] = []
        for (const [key, value] of Object.entries(params)) {
          if (Array.isArray(value)) {
            for (const v of value) {
              parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(v))}`)
            }
          } else if (value != null) {
            parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
          }
        }
        return parts.join('&')
      },
    },
  )
  return response.data
}

// ─── Admin Card CRUD ────────────────────────────────────────────────────────

export async function fetchAdminCards(params?: {
  page?: number
  per_page?: number
  category_id?: string
  difficulty?: string
  q?: string
}): Promise<AdminCardListResponse> {
  const response = await api.get<AdminCardListResponse>('/api/v1/admin/cards', { params })
  return response.data
}

export async function createAdminCard(data: AdminCardCreateRequest): Promise<AdminCard> {
  const response = await api.post<AdminCard>('/api/v1/admin/cards', data)
  return response.data
}

export async function updateAdminCard(id: string, data: AdminCardUpdateRequest): Promise<AdminCard> {
  const response = await api.put<AdminCard>(`/api/v1/admin/cards/${id}`, data)
  return response.data
}

export async function deleteAdminCard(id: string): Promise<void> {
  await api.delete(`/api/v1/admin/cards/${id}`)
}

export async function generateCardDraft(topic: string, difficulty: string): Promise<CardDraft> {
  const response = await api.post<CardDraft>('/api/v1/admin/cards/generate', { topic, difficulty })
  return response.data
}

export async function importCardsCSV(file: File, partial: boolean = false): Promise<CardImportResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post<CardImportResponse>(
    `/api/v1/admin/cards/import?partial=${partial}`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return response.data
}

// ─── Admin Analytics (spec #38 E-018b slice 2/4) ────────────────────────────

export interface AdminAnalyticsMetricValue {
  current: number
  d7_ago: number
  d30_ago: number
  delta_7d_pct: number
  delta_30d_pct: number
}

export interface AdminAnalyticsMetricsResponse {
  registered_users: AdminAnalyticsMetricValue
  paying_pro_users: AdminAnalyticsMetricValue
  dau_mau_ratio: AdminAnalyticsMetricValue
  avg_streak_length: AdminAnalyticsMetricValue
  ats_to_pro_conversion: AdminAnalyticsMetricValue
  monthly_churn: AdminAnalyticsMetricValue
  generated_at: string
  from_cache: boolean
}

export interface AdminAnalyticsRouteLatency {
  route: string
  p50_ms: number
  p95_ms: number
  p99_ms: number
  request_count: number
}

export interface AdminAnalyticsPerformanceResponse {
  llm_spend_estimate_usd: number
  llm_spend_breakdown: Record<string, number>
  api_latency: AdminAnalyticsRouteLatency[]
  api_latency_available: boolean
  error_rate_24h_pct: number | null
  error_rate_available: boolean
  stripe_webhook_success_24h_pct: number | null
  stripe_webhook_available: boolean
  generated_at: string
  from_cache: boolean
}

export async function fetchAdminAnalyticsMetrics(
  params?: { from?: string; to?: string },
): Promise<AdminAnalyticsMetricsResponse> {
  const response = await api.get<AdminAnalyticsMetricsResponse>(
    '/api/v1/admin/analytics/metrics',
    { params },
  )
  return response.data
}

export async function fetchAdminAnalyticsPerformance(
  params?: { from?: string; to?: string },
): Promise<AdminAnalyticsPerformanceResponse> {
  const response = await api.get<AdminAnalyticsPerformanceResponse>(
    '/api/v1/admin/analytics/performance',
    { params },
  )
  return response.data
}

// ─── Admin Content Quality (Phase 6 slice 6.11 — B-084) ─────────────────────

export async function fetchAdminContentQuality(params?: {
  window_days?: number
  include_archived?: boolean
}): Promise<AdminContentQualityResponse> {
  const response = await api.get<AdminContentQualityResponse>(
    '/api/v1/admin/content-quality',
    { params },
  )
  return response.data
}

// ─── Admin Authoring CRUD (Phase 6 slice 6.4b — B-065) ──────────────────────
// 13 helpers mirror the BE write routes shipped at d6bda3b. Each goes through
// the shared axios instance for Bearer-token injection + 401 silent-refresh.

export async function adminCreateDeck(data: DeckCreateRequest): Promise<Deck> {
  const response = await api.post<Deck>('/api/v1/admin/decks', data)
  return response.data
}

export async function adminUpdateDeck(
  deckId: string,
  data: DeckUpdateRequest,
): Promise<Deck> {
  const response = await api.patch<Deck>(`/api/v1/admin/decks/${deckId}`, data)
  return response.data
}

export async function adminArchiveDeck(deckId: string): Promise<Deck> {
  const response = await api.post<Deck>(`/api/v1/admin/decks/${deckId}/archive`)
  return response.data
}

export async function adminListDecks(
  status: AdminDeckStatusFilter = 'active',
): Promise<Deck[]> {
  const response = await api.get<Deck[]>('/api/v1/admin/decks', {
    params: { status },
  })
  return response.data
}

export async function adminCreateLesson(
  deckId: string,
  data: LessonCreateRequest,
): Promise<Lesson> {
  const response = await api.post<Lesson>(
    `/api/v1/admin/decks/${deckId}/lessons`,
    data,
  )
  return response.data
}

// `updateLesson` 409 envelope (EditClassificationConflictError) is surfaced
// to callers via the structured `error.response.data.detail` payload — the
// AdminLessonEditor reads it to fire the post-hoc cascade modal. We do NOT
// wrap or rebrand the 409 here; callers handle it at the catch site.
export async function adminUpdateLesson(
  lessonId: string,
  data: LessonUpdateRequest,
): Promise<LessonUpdateResponse> {
  const response = await api.patch<LessonUpdateResponse>(
    `/api/v1/admin/lessons/${lessonId}`,
    data,
  )
  return response.data
}

export async function adminPublishLesson(lessonId: string): Promise<Lesson> {
  const response = await api.post<Lesson>(
    `/api/v1/admin/lessons/${lessonId}/publish`,
  )
  return response.data
}

export async function adminArchiveLesson(lessonId: string): Promise<Lesson> {
  const response = await api.post<Lesson>(
    `/api/v1/admin/lessons/${lessonId}/archive`,
  )
  return response.data
}

export async function adminListLessons(
  deckId: string,
  status: AdminLessonStatusFilter = 'active',
): Promise<Lesson[]> {
  const response = await api.get<Lesson[]>(
    `/api/v1/admin/decks/${deckId}/lessons`,
    { params: { status } },
  )
  return response.data
}

export async function adminCreateQuizItem(
  lessonId: string,
  data: QuizItemCreateRequest,
): Promise<QuizItem> {
  const response = await api.post<QuizItem>(
    `/api/v1/admin/lessons/${lessonId}/quiz-items`,
    data,
  )
  return response.data
}

export async function adminUpdateQuizItem(
  quizItemId: string,
  data: QuizItemUpdateRequest,
): Promise<QuizItem> {
  const response = await api.patch<QuizItem>(
    `/api/v1/admin/quiz-items/${quizItemId}`,
    data,
  )
  return response.data
}

export async function adminRetireQuizItem(
  quizItemId: string,
  supersededById: string | null = null,
): Promise<QuizItem> {
  const response = await api.post<QuizItem>(
    `/api/v1/admin/quiz-items/${quizItemId}/retire`,
    { superseded_by_id: supersededById },
  )
  return response.data
}

export async function adminListQuizItems(
  lessonId: string,
  status: AdminQuizItemStatusFilter = 'active',
): Promise<QuizItem[]> {
  const response = await api.get<QuizItem[]>(
    `/api/v1/admin/lessons/${lessonId}/quiz-items`,
    { params: { status } },
  )
  return response.data
}

// ─── Spec #63 — ATS re-scan loop ──────────────────────────────────────────────

export async function fetchScoreHistory(
  trackerApplicationId: string,
): Promise<ScoreHistoryResponse> {
  const response = await api.get<ScoreHistoryResponse>(
    `/api/v1/tracker/${encodeURIComponent(trackerApplicationId)}/scores`,
  )
  return response.data
}

// ─── Spec #66 — AppShell loop-progress strip ─────────────────────────────────

export async function fetchLoopProgress(
  trackerApplicationId: string,
): Promise<LoopProgressResponse> {
  const response = await api.get<LoopProgressResponse>(
    `/api/v1/learn/loop-progress`,
    { params: { tracker_id: trackerApplicationId } },
  )
  return response.data
}

export async function triggerRescan(
  trackerApplicationId: string,
  resumeText: string,
): Promise<AnalysisResponse> {
  const response = await api.post<AnalysisResponse>(
    '/api/v1/analyze/rescan',
    {
      tracker_application_id: trackerApplicationId,
      resume_text: resumeText,
    },
  )
  return response.data
}

export default api
