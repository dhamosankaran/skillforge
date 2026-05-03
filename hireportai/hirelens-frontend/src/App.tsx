import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { DeprecatedRedirect } from '@/components/DeprecatedRedirect'
import { PersonaGate } from '@/components/PersonaGate'
import { AdminGate } from '@/components/auth/AdminGate'
import { useAuth } from '@/context/AuthContext'
import PersonaPicker from '@/pages/PersonaPicker'
import FirstAction from '@/pages/FirstAction'
import LandingPage from '@/pages/LandingPage'
import LoginPage from '@/pages/LoginPage'
import Analyze from '@/pages/Analyze'
import Results from '@/pages/Results'
import Rewrite from '@/pages/Rewrite'
import Tracker from '@/pages/Tracker'
import Pricing from '@/pages/Pricing'
import Interview from '@/pages/Interview'
import Learn from '@/pages/Learn'
import Dashboard from '@/pages/Dashboard'
import CategoryDetail from '@/pages/CategoryDetail'
import CardViewer from '@/pages/CardViewer'
import DailyReview from '@/pages/DailyReview'
import Lesson from '@/pages/Lesson'
import Onboarding from '@/pages/Onboarding'
import HomeDashboard from '@/pages/HomeDashboard'

// Lazy-loaded pages — not on the critical path (Spec #25)
const Profile = lazy(() => import('@/pages/Profile'))
const MissionMode = lazy(() => import('@/pages/MissionMode'))
const AdminLayout = lazy(() => import('@/components/admin/AdminLayout'))
const AdminCards = lazy(() => import('@/pages/admin/AdminCards'))
const AdminDecks = lazy(() => import('@/pages/admin/AdminDecks'))
const AdminDeckDetail = lazy(() => import('@/pages/admin/AdminDeckDetail'))
const AdminLessons = lazy(() => import('@/pages/admin/AdminLessons'))
const AdminLessonEditor = lazy(() => import('@/pages/admin/AdminLessonEditor'))
const AdminQuizItems = lazy(() => import('@/pages/admin/AdminQuizItems'))
const AdminAnalytics = lazy(() => import('@/pages/AdminAnalytics'))
const AdminContentQuality = lazy(() => import('@/pages/admin/AdminContentQuality'))

function LazyFallback() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Loader2 size={24} className="animate-spin text-text-muted" />
    </div>
  )
}

/** Redirects unauthenticated users to /. PersonaGate handles persona-null routing. */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return null
  if (!user) return <Navigate to="/" replace />
  return <PersonaGate>{children}</PersonaGate>
}

/** "/" shows landing page for guests; redirects logged-in users to /home. */
function HomeRoute() {
  const { user, isLoading } = useAuth()
  if (isLoading) return null
  if (user) return <Navigate to="/home" replace />
  return <LandingPage />
}

export default function App() {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-bg-base text-text-primary font-body">
      <AppShell>
        <AnimatePresence mode="wait">
          <Suspense fallback={<LazyFallback />}>
          <Routes location={location} key={location.pathname}>
          {/* Public routes */}
          <Route path="/" element={<HomeRoute />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/pricing" element={<Pricing />} />

          {/* Persona-aware home (real dashboard — P5-S18) */}
          <Route path="/home" element={<ProtectedRoute><HomeDashboard /></ProtectedRoute>} />

          {/* Onboarding (sits outside the two namespaces by design) */}
          <Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />
          <Route path="/onboarding/persona" element={<ProtectedRoute><PersonaPicker /></ProtectedRoute>} />
          <Route path="/first-action" element={<ProtectedRoute><FirstAction /></ProtectedRoute>} />

          {/* /learn/* — study engine */}
          <Route path="/learn"              element={<ProtectedRoute><Learn /></ProtectedRoute>} />
          <Route path="/learn/dashboard"    element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/learn/daily"        element={<ProtectedRoute><DailyReview /></ProtectedRoute>} />
          <Route path="/learn/category/:id" element={<ProtectedRoute><CategoryDetail /></ProtectedRoute>} />
          <Route path="/learn/card/:id"     element={<ProtectedRoute><CardViewer /></ProtectedRoute>} />
          <Route path="/learn/lesson/:id"   element={<ProtectedRoute><Lesson /></ProtectedRoute>} />
          <Route path="/learn/mission"      element={<ProtectedRoute><MissionMode /></ProtectedRoute>} />

          {/* /prep/* — interview prep */}
          <Route path="/prep"           element={<ProtectedRoute><Navigate to="/prep/analyze" replace /></ProtectedRoute>} />
          <Route path="/prep/analyze"   element={<ProtectedRoute><Analyze /></ProtectedRoute>} />
          <Route path="/prep/results"   element={<ProtectedRoute><Results /></ProtectedRoute>} />
          <Route path="/prep/rewrite"   element={<ProtectedRoute><Rewrite /></ProtectedRoute>} />
          <Route path="/prep/interview" element={<ProtectedRoute><Interview /></ProtectedRoute>} />
          <Route path="/prep/tracker"   element={<ProtectedRoute><Tracker /></ProtectedRoute>} />

          {/* Profile */}
          <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />

          {/* Admin — multi-route shell (Phase 6 slice 6.4a). /admin redirects to /admin/cards.
              Slice 6.4b adds editor routes for decks/lessons/quiz_items. */}
          <Route path="/admin" element={<ProtectedRoute><AdminGate><AdminLayout /></AdminGate></ProtectedRoute>}>
            <Route index                                  element={<Navigate to="/admin/cards" replace />} />
            <Route path="cards"                           element={<AdminCards />} />
            <Route path="decks"                           element={<AdminDecks />} />
            <Route path="decks/:deckId"                   element={<AdminDeckDetail />} />
            <Route path="lessons"                         element={<AdminLessons />} />
            <Route path="lessons/:lessonId"               element={<AdminLessonEditor />} />
            <Route path="lessons/:lessonId/quiz-items"    element={<AdminQuizItems />} />
            <Route path="analytics"                       element={<AdminAnalytics />} />
            <Route path="content-quality"                 element={<AdminContentQuality />} />
          </Route>

          {/* Transitional redirects — drop in Phase 6 once `deprecated_route_hit` (B-008) shows zero hits over 30 days. */}
          <Route path="/analyze"            element={<DeprecatedRedirect to="/prep/analyze" />} />
          <Route path="/results"            element={<DeprecatedRedirect to="/prep/results" />} />
          <Route path="/rewrite"            element={<DeprecatedRedirect to="/prep/rewrite" />} />
          <Route path="/interview"          element={<DeprecatedRedirect to="/prep/interview" />} />
          <Route path="/tracker"            element={<DeprecatedRedirect to="/prep/tracker" />} />
          <Route path="/study"              element={<DeprecatedRedirect to="/learn" />} />
          <Route path="/study/daily"        element={<DeprecatedRedirect to="/learn/daily" />} />
          <Route path="/study/category/:id" element={<DeprecatedRedirect build={(p) => `/learn/category/${p.id}`} />} />
          <Route path="/study/card/:id"     element={<DeprecatedRedirect build={(p) => `/learn/card/${p.id}`} />} />
          <Route path="/mission"            element={<DeprecatedRedirect to="/learn/mission" />} />

          <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </Suspense>
        </AnimatePresence>
      </AppShell>
    </div>
  )
}
