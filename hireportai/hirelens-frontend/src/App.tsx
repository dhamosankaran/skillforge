import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate, useLocation, useParams } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import { Navbar } from '@/components/layout/Navbar'
import { useAuth } from '@/context/AuthContext'
import PersonaPicker from '@/components/onboarding/PersonaPicker'
import LandingPage from '@/pages/LandingPage'
import LoginPage from '@/pages/LoginPage'
import Analyze from '@/pages/Analyze'
import Results from '@/pages/Results'
import Rewrite from '@/pages/Rewrite'
import Tracker from '@/pages/Tracker'
import Pricing from '@/pages/Pricing'
import Interview from '@/pages/Interview'
import StudyDashboard from '@/pages/StudyDashboard'
import CategoryDetail from '@/pages/CategoryDetail'
import CardViewer from '@/pages/CardViewer'
import DailyReview from '@/pages/DailyReview'
import Onboarding from '@/pages/Onboarding'
import HomeDashboardPlaceholder from '@/pages/HomeDashboardPlaceholder'

// Lazy-loaded pages — not on the critical path (Spec #25)
const Profile = lazy(() => import('@/pages/Profile'))
const MissionMode = lazy(() => import('@/pages/MissionMode'))
const AdminPanel = lazy(() => import('@/pages/AdminPanel'))

function LazyFallback() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Loader2 size={24} className="animate-spin text-text-muted" />
    </div>
  )
}

/** Redirects unauthenticated users to /. Shows PersonaPicker if onboarding not done. */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return null
  if (!user) return <Navigate to="/" replace />
  if (!user.onboarding_completed) return <PersonaPicker mode="onboarding" />
  return <>{children}</>
}

/** Redirect helper that substitutes dynamic segments into the target. `<Navigate to="/foo/:id">` would
 * redirect to the literal string "/foo/:id" — React Router does not thread params through Navigate. */
function RedirectWithParam({ build }: { build: (params: Record<string, string>) => string }) {
  const params = useParams()
  return <Navigate to={build(params as Record<string, string>)} replace />
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
  const isLanding = location.pathname === '/'

  return (
    <div className="min-h-screen bg-bg-base text-text-primary font-body">
      {!isLanding && <Navbar />}
      <AnimatePresence mode="wait">
        <Suspense fallback={<LazyFallback />}>
        <Routes location={location} key={location.pathname}>
          {/* Public routes */}
          <Route path="/" element={<HomeRoute />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/pricing" element={<Pricing />} />

          {/* Persona-aware home (placeholder — P5-S18 ships real HomeDashboard) */}
          <Route path="/home" element={<ProtectedRoute><HomeDashboardPlaceholder /></ProtectedRoute>} />

          {/* Onboarding (sits outside the two namespaces by design) */}
          <Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />

          {/* /learn/* — study engine */}
          <Route path="/learn"              element={<ProtectedRoute><StudyDashboard /></ProtectedRoute>} />
          <Route path="/learn/daily"        element={<ProtectedRoute><DailyReview /></ProtectedRoute>} />
          <Route path="/learn/category/:id" element={<ProtectedRoute><CategoryDetail /></ProtectedRoute>} />
          <Route path="/learn/card/:id"     element={<ProtectedRoute><CardViewer /></ProtectedRoute>} />
          <Route path="/learn/mission"      element={<ProtectedRoute><MissionMode /></ProtectedRoute>} />

          {/* /prep/* — interview prep */}
          <Route path="/prep/analyze"   element={<ProtectedRoute><Analyze /></ProtectedRoute>} />
          <Route path="/prep/results"   element={<ProtectedRoute><Results /></ProtectedRoute>} />
          <Route path="/prep/rewrite"   element={<ProtectedRoute><Rewrite /></ProtectedRoute>} />
          <Route path="/prep/interview" element={<ProtectedRoute><Interview /></ProtectedRoute>} />
          <Route path="/prep/tracker"   element={<ProtectedRoute><Tracker /></ProtectedRoute>} />

          {/* Profile + admin — unchanged */}
          <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
          <Route path="/admin"   element={<ProtectedRoute><AdminPanel /></ProtectedRoute>} />

          {/* Transitional redirects — drop in Phase 6 once the old paths stop receiving hits. */}
          <Route path="/analyze"            element={<Navigate to="/prep/analyze" replace />} />
          <Route path="/results"            element={<Navigate to="/prep/results" replace />} />
          <Route path="/rewrite"            element={<Navigate to="/prep/rewrite" replace />} />
          <Route path="/interview"          element={<Navigate to="/prep/interview" replace />} />
          <Route path="/tracker"            element={<Navigate to="/prep/tracker" replace />} />
          <Route path="/study"              element={<Navigate to="/learn" replace />} />
          <Route path="/study/daily"        element={<Navigate to="/learn/daily" replace />} />
          <Route path="/study/category/:id" element={<RedirectWithParam build={(p) => `/learn/category/${p.id}`} />} />
          <Route path="/study/card/:id"     element={<RedirectWithParam build={(p) => `/learn/card/${p.id}`} />} />
          <Route path="/mission"            element={<Navigate to="/learn/mission" replace />} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </Suspense>
      </AnimatePresence>
    </div>
  )
}
