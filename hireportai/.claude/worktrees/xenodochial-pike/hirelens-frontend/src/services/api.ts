import axios, { AxiosError } from 'axios'
import toast from 'react-hot-toast'
import type {
  AnalysisResponse,
  CoverLetterResponse,
  InterviewPrepResponse,
  RewriteResponse,
  TrackerApplication,
} from '@/types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000, // 2 min for analysis
})

// Global error interceptor
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ error?: string; detail?: string }>) => {
    const message =
      error.response?.data?.error ||
      error.response?.data?.detail ||
      error.message ||
      'An unexpected error occurred'
    toast.error(message)
    return Promise.reject(error)
  }
)

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

export default api
