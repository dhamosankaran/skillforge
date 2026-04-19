import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import toast from 'react-hot-toast'
import type {
  AdminCard,
  AdminCardCreateRequest,
  AdminCardListResponse,
  AdminCardUpdateRequest,
  AnalysisResponse,
  Card,
  CardDraft,
  CardImportResponse,
  CategoriesResponse,
  CoverLetterResponse,
  DailyQueueResponse,
  EmailPreference,
  EmailPreferenceUpdate,
  GamificationStats,
  InterviewPrepResponse,
  MissionCreateRequest,
  MissionDailyResponse,
  MissionDayCompleteResponse,
  MissionDetailResponse,
  MissionResponse,
  OnboardingRecommendationsResponse,
  ReviewRequest,
  ReviewResponse,
  RewriteResponse,
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
  async (error: AxiosError<{ error?: string; detail?: string }>) => {
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
      const message =
        error.response?.data?.error ||
        error.response?.data?.detail ||
        error.message ||
        'An unexpected error occurred'
      toast.error(message)
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
  jdText: string
): Promise<InterviewPrepResponse> {
  const response = await api.post<InterviewPrepResponse>('/api/interview-prep', {
    resume_text: resumeText,
    job_description: jdText,
  })
  return response.data
}

export async function getApplications(): Promise<TrackerApplication[]> {
  const response = await api.get<TrackerApplication[]>('/api/tracker')
  return response.data
}

export async function createApplication(
  data: Omit<TrackerApplication, 'id' | 'created_at'>
): Promise<TrackerApplication> {
  const response = await api.post<TrackerApplication>('/api/tracker', data)
  return response.data
}

export async function updateApplication(
  id: string,
  data: Partial<Omit<TrackerApplication, 'id' | 'created_at'>>
): Promise<TrackerApplication> {
  const response = await api.patch<TrackerApplication>(`/api/tracker/${id}`, data)
  return response.data
}

export async function deleteApplication(id: string): Promise<void> {
  await api.delete(`/api/tracker/${id}`)
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

export default api
