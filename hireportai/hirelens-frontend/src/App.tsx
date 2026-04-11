import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
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

/** "/" shows landing page for guests; redirects logged-in users to /analyze. */
function HomeRoute() {
  const { user, isLoading } = useAuth()
  if (isLoading) return null
  if (user) return <Navigate to="/analyze" replace />
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

          {/* Protected routes — require sign-in */}
          <Route path="/analyze"   element={<ProtectedRoute><Analyze /></ProtectedRoute>} />
          <Route path="/results"   element={<ProtectedRoute><Results /></ProtectedRoute>} />
          <Route path="/rewrite"   element={<ProtectedRoute><Rewrite /></ProtectedRoute>} />
          <Route path="/tracker"   element={<ProtectedRoute><Tracker /></ProtectedRoute>} />
          <Route path="/interview" element={<ProtectedRoute><Interview /></ProtectedRoute>} />
          <Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />
          <Route path="/study"               element={<ProtectedRoute><StudyDashboard /></ProtectedRoute>} />
          <Route path="/study/daily"         element={<ProtectedRoute><DailyReview /></ProtectedRoute>} />
          <Route path="/study/category/:id"  element={<ProtectedRoute><CategoryDetail /></ProtectedRoute>} />
          <Route path="/study/card/:id"      element={<ProtectedRoute><CardViewer /></ProtectedRoute>} />
          <Route path="/mission"             element={<ProtectedRoute><MissionMode /></ProtectedRoute>} />
          <Route path="/profile"             element={<ProtectedRoute><Profile /></ProtectedRoute>} />
          <Route path="/admin"               element={<ProtectedRoute><AdminPanel /></ProtectedRoute>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </Suspense>
      </AnimatePresence>
    </div>
  )
}
