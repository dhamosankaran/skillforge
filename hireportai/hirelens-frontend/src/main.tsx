import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { GoogleOAuthProvider } from '@react-oauth/google'
import * as Sentry from '@sentry/react'
import { AuthProvider } from '@/context/AuthContext'
import { AnalysisProvider } from '@/context/AnalysisContext'
import { UsageProvider } from '@/context/UsageContext'
import { GamificationProvider } from '@/context/GamificationContext'
import { UpgradeModal } from '@/components/ui/UpgradeModal'
import App from '@/App'
// Eager-import to run PostHog init side-effect before the first render,
// so capture() calls during initial route mount are not dropped.
import '@/utils/posthog'
import '@/index.css'
import '@/styles/design-tokens.css'

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''
const sentryDsn = import.meta.env.VITE_SENTRY_DSN || ''

if (sentryDsn) {
  Sentry.init({
    dsn: sentryDsn,
    integrations: [Sentry.browserTracingIntegration()],
    tracesSampleRate: 0.1,
  })
}

function SentryFallback() {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      background: '#060810',
      color: '#f0f6ff',
      fontFamily: 'system-ui, sans-serif',
      gap: '16px',
    }}>
      <h1 style={{ fontSize: '24px', fontWeight: 600 }}>Something went wrong</h1>
      <p style={{ color: '#8b95a5', fontSize: '14px' }}>
        An unexpected error occurred. Please try reloading the page.
      </p>
      <button
        onClick={() => window.location.reload()}
        style={{
          padding: '10px 24px',
          borderRadius: '10px',
          border: '1px solid rgba(255,255,255,0.1)',
          background: '#141a24',
          color: '#f0f6ff',
          cursor: 'pointer',
          fontSize: '14px',
        }}
      >
        Reload page
      </button>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Sentry.ErrorBoundary fallback={<SentryFallback />}>
    <GoogleOAuthProvider clientId={googleClientId}>
      <BrowserRouter>
        <AuthProvider>
          <UsageProvider>
            <GamificationProvider>
            <AnalysisProvider>
              <App />
              <UpgradeModal />
          <Toaster
            position="bottom-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#141a24',
                color: '#f0f6ff',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '14px',
                fontSize: '13px',
                fontFamily: 'var(--sf-font-body)',
                boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
              },
              success: {
                iconTheme: { primary: '#00ffc8', secondary: '#060810' },
              },
              error: {
                iconTheme: { primary: '#f85149', secondary: '#060810' },
              },
            }}
              />
            </AnalysisProvider>
            </GamificationProvider>
          </UsageProvider>
        </AuthProvider>
      </BrowserRouter>
    </GoogleOAuthProvider>
    </Sentry.ErrorBoundary>
  </React.StrictMode>
)
