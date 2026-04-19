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
  scan_id?: string
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
  cached?: boolean
  generated_at?: string
  model_used?: string
}

export type ApplicationStatus = 'Applied' | 'Interview' | 'Offer' | 'Rejected'

export interface TrackerApplication {
  id: string
  company: string
  role: string
  date_applied: string
  ats_score: number
  status: ApplicationStatus
  scan_id?: string | null
  skills_matched?: string[] | null
  skills_missing?: string[] | null
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

// ─── Mission Mode ────────────────────────────────────────────────────────────

export interface MissionDayView {
  day_number: number
  date: string
  cards_target: number
  cards_completed: number
}

export interface MissionResponse {
  id: string
  title: string
  target_date: string
  category_ids: string[]
  daily_target: number
  total_cards: number
  days_remaining: number
  status: 'active' | 'completed' | 'abandoned'
  progress_pct: number
  created_at: string
}

export interface MissionDetailResponse extends MissionResponse {
  days: MissionDayView[]
}

export interface MissionDailyCard {
  id: string
  question: string
  answer: string
  category: string
  difficulty: 'easy' | 'medium' | 'hard'
}

export interface MissionDailyResponse {
  mission_id: string
  day_number: number
  date: string
  cards_target: number
  cards_completed: number
  cards: MissionDailyCard[]
}

export interface MissionDayCompleteResponse {
  mission_id: string
  day_number: number
  cards_completed: number
  cards_target: number
  xp_awarded: number
  mission_status: string
}

export interface MissionCreateRequest {
  title: string
  target_date: string
  category_ids: string[]
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

// ─── Gamification — XP, streaks, badges (spec phase-2/10) ────────────────────

export interface BadgeView {
  badge_id: string
  name: string
  earned_at: string // ISO datetime
}

export interface GamificationStats {
  user_id: string
  current_streak: number
  longest_streak: number
  total_xp: number
  last_active_date: string | null // ISO date (YYYY-MM-DD)
  freezes_available: number
  badges: BadgeView[]
}

// ─── Email Preferences (spec phase-2/15-16) ─────────────────────────────────

export interface EmailPreference {
  user_id: string
  daily_reminder: boolean
  timezone: string
}

export interface EmailPreferenceUpdate {
  daily_reminder?: boolean
  timezone?: string
}

// ─── Admin Card CRUD ─────────────────────────────────────────────────────────

export interface AdminCard {
  id: string
  category_id: string
  category_name: string
  question: string
  answer: string
  difficulty: 'easy' | 'medium' | 'hard'
  tags: string[]
  embedding_status: 'pending' | 'ready'
  created_at: string
  updated_at: string
}

export interface AdminCardListResponse {
  cards: AdminCard[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface AdminCardCreateRequest {
  category_id: string
  question: string
  answer: string
  difficulty: 'easy' | 'medium' | 'hard'
  tags: string[]
}

export interface AdminCardUpdateRequest {
  category_id?: string
  question?: string
  answer?: string
  difficulty?: 'easy' | 'medium' | 'hard'
  tags?: string[]
}

export interface CardDraft {
  question: string
  answer: string
  difficulty: 'easy' | 'medium' | 'hard'
  tags: string[]
}

export interface CardImportResponse {
  created_count: number
  skipped_count: number
  errors: Array<{ row: number; error: string }>
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

