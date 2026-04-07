import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { Navbar } from '@/components/layout/Navbar'
import Landing from '@/pages/Landing'
import Analyze from '@/pages/Analyze'
import Results from '@/pages/Results'
import Rewrite from '@/pages/Rewrite'
import Tracker from '@/pages/Tracker'
import Pricing from '@/pages/Pricing'
import Interview from '@/pages/Interview'

export default function App() {
  const location = useLocation()
  const isLanding = location.pathname === '/'

  return (
    <div className="min-h-screen bg-bg-base text-text-primary font-body">
      {!isLanding && <Navbar />}
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<Landing />} />
          <Route path="/analyze" element={<Analyze />} />
          <Route path="/results" element={<Results />} />
          <Route path="/rewrite" element={<Rewrite />} />
          <Route path="/tracker" element={<Tracker />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/interview" element={<Interview />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AnimatePresence>
    </div>
  )
}
