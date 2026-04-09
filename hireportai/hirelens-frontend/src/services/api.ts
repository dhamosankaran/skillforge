import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import toast from 'react-hot-toast'
import type {
  AnalysisResponse,
  Card,
  CategoriesResponse,
  CoverLetterResponse,
  InterviewPrepResponse,
  ReviewRequest,
  ReviewResponse,
  RewriteResponse,
  TrackerApplication,
} from '@/types'
import {
  STORAGE_KEY_ACCESS,
  STORAGE_KEY_REFRESH,
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

export async function fetchCard(id: string): Promise<Card> {
  const response = await api.get<Card>(`/api/v1/cards/${id}`)
  return response.data
}

export async function submitReview(req: ReviewRequest): Promise<ReviewResponse> {
  const response = await api.post<ReviewResponse>('/api/v1/study/review', req)
  return response.data
}

export default api
