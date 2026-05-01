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

export interface CoverLetterRecipient {
  name: string
  company: string
}

export interface CoverLetterResponse {
  date: string
  recipient: CoverLetterRecipient
  greeting: string
  body_paragraphs: string[]
  signoff: string
  signature: string
  tone: string
  full_text: string
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
  /** Spec #57 — optional per-application interview date (ISO YYYY-MM-DD). */
  interview_date?: string | null
  created_at: string
}

// ─── Spec #63 — ATS re-scan loop ──────────────────────────────────────────────

export interface ScoreHistoryEntry {
  id: string
  scan_id: string | null
  overall_score: number
  keyword_match_score: number
  skills_coverage_score: number
  formatting_compliance_score: number
  bullet_strength_score: number
  /** ISO8601 (timezone-aware). */
  scanned_at: string
}

export interface ScoreDelta {
  overall_delta: number
  keyword_match_delta: number
  skills_coverage_delta: number
  formatting_compliance_delta: number
  bullet_strength_delta: number
  days_between: number
}

export interface ScoreHistoryResponse {
  tracker_application_id: string
  /** Chronological, oldest-first. */
  history: ScoreHistoryEntry[]
  /** Pre-computed delta between latest two rows; null when history.length < 2. */
  delta: ScoreDelta | null
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

/**
 * Spec #63 / B-059 — pre-flight wall state echoed on the daily-queue
 * response. Read-side mirror of the same Redis counter
 * `study_service._check_daily_wall` writes on submit. `cards_limit === -1`
 * is the unlimited sentinel (Pro / Enterprise / admin); for free users
 * `can_review` flips to false once `cards_consumed >= cards_limit`.
 *
 * Optional in the type so existing mocks / older FE builds don't break
 * during the BE → FE deploy ordering window. `DailyReview.tsx` falls
 * back to a permissive default when the field is missing.
 */
export interface DailyStatus {
  cards_consumed: number
  cards_limit: number
  can_review: boolean
  resets_at: string  // ISO8601
}

export interface DailyQueueResponse {
  cards: DailyCard[]
  total_due: number
  session_id: string
  /**
   * B-019. True when the caller has already reviewed today's quota (UTC
   * window, matching the daily_complete XP bonus). TodaysReviewWidget
   * flips to its done-state on this flag independently of `total_due`,
   * which always counts the queue length (overdue + fresh-fill) so the
   * DailyReview page can still render a queue even after completion.
   * Optional in the type so existing mocks / older FE builds don't break
   * during the BE → FE deploy ordering window.
   */
  completed_today?: boolean
  daily_status?: DailyStatus
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

// ─── Phase 6 — Lessons / Decks / QuizItems (slice 6.3) ───────────────────────
// Field-for-field mirrors of the BE Pydantic schemas in
// app/schemas/{deck,lesson,quiz_item}.py.

export type PersonaVisibility = 'climber' | 'interview_prepper' | 'both'
export type DeckTier = 'foundation' | 'premium'
export type LessonVersionType = 'initial' | 'minor_edit' | 'substantive_edit'
export type QuestionType = 'mcq' | 'free_text' | 'code_completion'
export type QuizDifficulty = 'easy' | 'medium' | 'hard'

export interface Deck {
  id: string
  slug: string
  title: string
  description: string
  display_order: number
  icon: string | null
  persona_visibility: PersonaVisibility
  tier: DeckTier
  created_at: string
  updated_at: string
  archived_at: string | null
}

export interface Lesson {
  id: string
  deck_id: string
  slug: string
  title: string
  concept_md: string
  production_md: string
  examples_md: string
  display_order: number
  version: number
  version_type: LessonVersionType
  published_at: string | null
  generated_by_model: string | null
  source_content_id: string | null
  quality_score: number | null
  created_at: string
  updated_at: string
  archived_at: string | null
}

export interface QuizItem {
  id: string
  lesson_id: string
  question: string
  answer: string
  question_type: QuestionType
  distractors: string[] | null
  difficulty: QuizDifficulty
  display_order: number
  version: number
  superseded_by_id: string | null
  retired_at: string | null
  generated_by_model: string | null
  created_at: string
  updated_at: string
}

export interface LessonWithQuizzes {
  lesson: Lesson
  quiz_items: QuizItem[]
  deck_id: string
  deck_slug: string
  deck_title: string
}

export interface DeckWithLessons {
  deck: Deck
  lessons: Lesson[]
}

// ─── Phase 6 — Lens-ranked decks (slice 6.6 / spec #07 §5) ───────────────────
// Field-for-field mirrors of app/schemas/ranker.py. v1 always returns
// `lessons: null` per spec #07 §12 D-5; the field is forward-compat for
// a hypothetical slice 6.6b lesson surface.

export interface ScoreBreakdown {
  gap_match: number
  fsrs_due: number
  avg_quality: number
  display_order_rank: number
}

export interface RankedDeck {
  deck: Deck
  score: number
  rank: number
  matched_gaps: string[]
  score_breakdown: ScoreBreakdown
}

export interface RankedDecksResponse {
  user_id: string
  persona: string | null
  cold_start: boolean
  lookback_days: number
  recent_gap_count: number
  ranked_at: string
  decks: RankedDeck[]
  lessons: null
}

// Mirrors app/schemas/quiz_item.py::QuizReviewRequest (slice 6.2).
// Re-declared here so the FE consumer in slice 6.3 doesn't reach into
// study-engine types. Rating: Again=1, Hard=2, Good=3, Easy=4.
export interface QuizReviewRequest {
  quiz_item_id: string
  rating: 1 | 2 | 3 | 4
  session_id: string
  time_spent_ms?: number
}

// Mirrors app/schemas/quiz_item.py::QuizReviewResponse (slice 6.2).
export interface QuizReviewResponse {
  quiz_item_id: string
  fsrs_state: 'learning' | 'review' | 'relearning'
  stability: number
  difficulty: number
  due_date: string
  reps: number
  lapses: number
  scheduled_days: number
}

// ─── Phase 6 slice 6.4b — Admin authoring write shapes ───────────────────────
// Field-for-field mirrors of the BE Pydantic write schemas in
// app/schemas/{deck,lesson,quiz_item}.py shipped at commit d6bda3b.

export type EditClassification = 'minor' | 'substantive'

export type AdminDeckStatusFilter = 'active' | 'archived' | 'all'
export type AdminLessonStatusFilter =
  | 'active'
  | 'drafts'
  | 'published'
  | 'archived'
  | 'all'
export type AdminQuizItemStatusFilter = 'active' | 'retired' | 'all'

export interface DeckCreateRequest {
  slug: string
  title: string
  description: string
  display_order?: number
  icon?: string | null
  persona_visibility?: PersonaVisibility
  tier?: DeckTier
}

export interface DeckUpdateRequest {
  slug?: string
  title?: string
  description?: string
  display_order?: number
  icon?: string | null
  persona_visibility?: PersonaVisibility
  tier?: DeckTier
}

export interface LessonCreateRequest {
  slug: string
  title: string
  concept_md: string
  production_md: string
  examples_md: string
  display_order?: number
}

export interface LessonUpdateRequest {
  edit_classification: EditClassification
  slug?: string
  title?: string
  concept_md?: string
  production_md?: string
  examples_md?: string
  display_order?: number
}

// Mirrors app/schemas/lesson.py::LessonUpdateResponse — extends Lesson read
// shape with cascade-outcome fields surfaced for FE confirm-modal results.
export interface LessonUpdateResponse {
  lesson: Lesson
  version_type_applied: EditClassification
  quiz_items_retired_count: number
  quiz_items_retired_ids: string[]
}

export interface QuizItemCreateRequest {
  question: string
  answer: string
  question_type?: QuestionType
  distractors?: string[] | null
  difficulty?: QuizDifficulty
  display_order?: number
}

export interface QuizItemUpdateRequest {
  edit_classification: EditClassification
  question?: string
  answer?: string
  question_type?: QuestionType
  distractors?: string[] | null
  difficulty?: QuizDifficulty
  display_order?: number
}

// ─── Phase 6 — User-self FSRS dashboard (slice 6.8 / spec #09 §5) ───────────
// Field-for-field mirrors of app/schemas/dashboard.py. Single envelope per
// §12 D-3; cold-start = is_cold_start true + zeroed/empty section payloads.

export interface CardsDueByState {
  new: number
  learning: number
  review: number
  relearning: number
}

export interface CardsDueSection {
  due_today: number
  due_next_7_days: number
  due_breakdown_by_state: CardsDueByState
  total_quiz_items_in_progress: number
}

export interface DailyRetentionPoint {
  date: string // ISO date YYYY-MM-DD (user-local per §12 D-6)
  sample_size: number
  recall_rate: number | null // null when sample_size === 0
}

export interface RetentionSection {
  sample_size: number
  overall_recall_rate: number
  overall_lapse_rate: number
  daily_retention: DailyRetentionPoint[]
}

export interface DeckMastery {
  deck_id: string
  deck_slug: string
  deck_title: string
  total_quiz_items_visible: number
  quiz_items_with_progress: number
  quiz_items_mastered: number
  mastery_pct: number // [0, 1]
}

export interface DeckMasterySection {
  decks: DeckMastery[]
}

export interface StreakSection {
  current_streak: number
  longest_streak: number
  last_active_date: string | null // ISO date YYYY-MM-DD
  freezes_available: number
  total_xp: number
}

export interface RecentReview {
  quiz_item_id: string
  lesson_id: string
  lesson_title: string
  deck_slug: string
  rating: number // 1..4 (py-fsrs Rating)
  fsrs_state_after: string // 'new' | 'learning' | 'review' | 'relearning'
  reviewed_at: string // ISO datetime
}

export interface ReviewHistorySection {
  window_days: number
  total_in_window: number
  recent_reviews: RecentReview[]
}

export interface DashboardResponse {
  user_id: string
  persona: string | null
  plan: string | null
  is_cold_start: boolean
  retention_window_days: number
  generated_at: string // ISO datetime
  cards_due: CardsDueSection
  retention: RetentionSection
  deck_mastery: DeckMasterySection
  streak: StreakSection
  review_history: ReviewHistorySection
}

