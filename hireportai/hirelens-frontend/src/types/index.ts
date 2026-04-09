// All TypeScript interfaces for SkillForge

export interface ATSScoreBreakdown {
  keyword_match: number
  skills_coverage: number
  formatting_compliance: number
  bullet_strength: number
}

export interface SkillGap {
  skill: string
  category: 'Technical' | 'Soft' | 'Certification' | 'Tool'
  importance: 'critical' | 'recommended' | 'nice-to-have'
}

export interface BulletAnalysis {
  original: string
  score: number
  issues: string[]
  rewritten: string
}

export interface FormattingIssue {
  issue: string
  severity: 'critical' | 'warning' | 'info'
  fix: string
}

export interface KeywordChartData {
  keyword: string
  resume_count: number
  jd_count: number
  matched: boolean
}

export interface SkillOverlapData {
  subject: string
  resume: number
  jd: number
}

export interface AnalysisResponse {
  ats_score: number
  grade: string
  score_breakdown: ATSScoreBreakdown
  matched_keywords: string[]
  missing_keywords: string[]
  skill_gaps: SkillGap[]
  bullet_analysis: BulletAnalysis[]
  formatting_issues: FormattingIssue[]
  job_fit_explanation: string
  top_strengths: string[]
  top_gaps: string[]
  keyword_chart_data: KeywordChartData[]
  skills_overlap_data: SkillOverlapData[]
  resume_text?: string
}

export interface RewriteEntry {
  org: string
  location: string
  date: string
  title: string
  bullets: string[]
  details: string[]
}

export interface RewriteSection {
  title: string
  content: string
  entries: RewriteEntry[]
}

export interface RewriteHeader {
  name: string
  contact: string
}

export interface RewriteResponse {
  header: RewriteHeader
  sections: RewriteSection[]
  full_text: string
  template_type: string
}

export interface CoverLetterResponse {
  cover_letter: string
  tone: string
}

export interface InterviewQuestion {
  question: string
  star_framework: string
}

export interface InterviewPrepResponse {
  questions: InterviewQuestion[]
}

export type ApplicationStatus = 'Applied' | 'Interview' | 'Offer' | 'Rejected'

export interface TrackerApplication {
  id: string
  company: string
  role: string
  date_applied: string
  ats_score: number
  status: ApplicationStatus
  created_at: string
}

// ─── Study / Cards ────────────────────────────────────────────────────────────

export interface Category {
  id: string
  name: string
  icon: string
  color: string           // Tailwind gradient classes, e.g. "from-purple-500 to-indigo-600"
  display_order: number
  source: 'foundation' | 'premium'
  card_count: number
  studied_count: number   // cards with reps > 0 for the current user (0 until dashboard endpoint)
  locked: boolean         // true when source !== 'foundation' and user is on free plan
}

export interface CategoriesResponse {
  categories: Category[]
}

export interface Card {
  id: string
  category_id: string
  category_name: string
  question: string
  answer: string
  difficulty: 'easy' | 'medium' | 'hard'
  tags: string[]
  created_at: string
  updated_at: string
}

export type FsrsRating = 1 | 2 | 3 | 4

export interface ReviewRequest {
  card_id: string
  rating: FsrsRating
  session_id: string
  time_spent_ms?: number
}

export interface ReviewResponse {
  card_id: string
  fsrs_state: 'new' | 'learning' | 'review' | 'relearning'
  stability: number
  difficulty: number
  due_date: string
  reps: number
  lapses: number
  scheduled_days: number
}

/** Card as returned by GET /api/v1/study/daily */
export interface DailyCard {
  card_id: string
  question: string
  answer: string
  difficulty: 'easy' | 'medium' | 'hard'
  tags: string[]
  category_id: string
  category_name: string
  fsrs_state: 'new' | 'learning' | 'review' | 'relearning'
  due_date: string | null
  reps: number
  lapses: number
}

export interface DailyQueueResponse {
  cards: DailyCard[]
  total_due: number
  session_id: string
}

// ─── Onboarding (ATS gap → cards bridge) ─────────────────────────────────────

export interface RecommendedCategory {
  category_id: string
  name: string
  icon: string
  color: string
  matched_card_count: number
  similarity_score: number | null
}

export interface GapMapping {
  gap: string
  match_type: 'tag' | 'semantic' | 'none'
  matching_categories: RecommendedCategory[]
}

export interface OnboardingRecommendationsResponse {
  scan_id: string | null
  results: GapMapping[]
}

// ─── Analysis ─────────────────────────────────────────────────────────────────

export interface AnalysisState {
  isLoading: boolean
  error: string | null
  result: AnalysisResponse | null
  resumeFile: File | null
  jobDescription: string
}

export type AnalysisAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_RESULT'; payload: AnalysisResponse }
  | { type: 'SET_RESUME_FILE'; payload: File | null }
  | { type: 'SET_JD'; payload: string }
  | { type: 'RESET' }

