import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { Navbar } from '@/components/layout/Navbar'
import { useAuth } from '@/context/AuthContext'
import LandingPage from '@/pages/LandingPage'
import Analyze from '@/pages/Analyze'
import Results from '@/pages/Results'
import Rewrite from '@/pages/Rewrite'
import Tracker from '@/pages/Tracker'
import Pricing from '@/pages/Pricing'
import Interview from '@/pages/Interview'
import StudyDashboard from '@/pages/StudyDashboard'
import CardViewer from '@/pages/CardViewer'
import DailyReview from '@/pages/DailyReview'

/** Redirects unauthenticated users to /. Renders nothing while auth hydrates. */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return null
  if (!user) return <Navigate to="/" replace />
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
        <Routes location={location} key={location.pathname}>
          {/* Public routes */}
          <Route path="/" element={<HomeRoute />} />
          <Route path="/pricing" element={<Pricing />} />

          {/* Protected routes — require sign-in */}
          <Route path="/analyze"   element={<ProtectedRoute><Analyze /></ProtectedRoute>} />
          <Route path="/results"   element={<ProtectedRoute><Results /></ProtectedRoute>} />
          <Route path="/rewrite"   element={<ProtectedRoute><Rewrite /></ProtectedRoute>} />
          <Route path="/tracker"   element={<ProtectedRoute><Tracker /></ProtectedRoute>} />
          <Route path="/interview" element={<ProtectedRoute><Interview /></ProtectedRoute>} />
          <Route path="/study"            element={<ProtectedRoute><StudyDashboard /></ProtectedRoute>} />
          <Route path="/study/daily"     element={<ProtectedRoute><DailyReview /></ProtectedRoute>} />
          <Route path="/study/card/:id"  element={<ProtectedRoute><CardViewer /></ProtectedRoute>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AnimatePresence>
    </div>
  )
}
