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
import { ThemeProvider, applyInitialTheme } from '@/context/ThemeContext'
import { UpgradeModal } from '@/components/ui/UpgradeModal'
import App from '@/App'
// Eager-import to run PostHog init side-effect before the first render,
// so capture() calls during initial route mount are not dropped.
import '@/utils/posthog'
import '@/index.css'
import '@/styles/design-tokens.css'

// Apply the persisted theme's CSS variables synchronously BEFORE React renders
// so the first paint already has the correct colours (no flash).
applyInitialTheme()

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''
const sentryDsn = import.meta.env.VITE_SENTRY_DSN || ''

if (sentryDsn) {
  Sentry.init({
    dsn: sentryDsn,
    integrations: [Sentry.browserTracingIntegration()],
    tracesSampleRate: 0.1,
  })
}

function SentryFallback({
  error,
  componentStack,
}: {
  error: unknown
  componentStack?: string | null
}) {
  const isDev = import.meta.env.DEV
  const message =
    error instanceof Error ? `${error.name}: ${error.message}` : String(error)
  const stack = error instanceof Error ? error.stack : null
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      background: 'var(--bg-base)',
      color: 'var(--text-primary)',
      fontFamily: 'system-ui, sans-serif',
      gap: '16px',
      padding: '32px',
    }}>
      <h1 style={{ fontSize: '24px', fontWeight: 600 }}>Something went wrong</h1>
      <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
        An unexpected error occurred. Please try reloading the page.
      </p>
      {isDev && (
        <details
          open
          style={{
            maxWidth: '900px',
            width: '100%',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: '10px',
            padding: '16px',
            fontFamily: 'var(--sf-font-mono, ui-monospace), monospace',
            fontSize: '12px',
            color: 'var(--text-primary)',
          }}
        >
          <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
            {message}
          </summary>
          {stack && (
            <pre style={{ marginTop: '12px', overflow: 'auto', whiteSpace: 'pre-wrap' }}>{stack}</pre>
          )}
          {componentStack && (
            <pre style={{ marginTop: '12px', overflow: 'auto', whiteSpace: 'pre-wrap', color: 'var(--text-secondary)' }}>{componentStack}</pre>
          )}
        </details>
      )}
      <button
        onClick={() => window.location.reload()}
        style={{
          padding: '10px 24px',
          borderRadius: '10px',
          border: '1px solid var(--border)',
          background: 'var(--bg-elevated)',
          color: 'var(--text-primary)',
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
    <Sentry.ErrorBoundary
      fallback={({ error, componentStack }) => (
        <SentryFallback error={error} componentStack={componentStack} />
      )}
    >
    <GoogleOAuthProvider clientId={googleClientId}>
      <BrowserRouter>
        <ThemeProvider>
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
                background: 'var(--bg-elevated)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border)',
                borderRadius: '14px',
                fontSize: '13px',
                fontFamily: 'var(--sf-font-body)',
                boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
              },
              success: {
                iconTheme: { primary: 'var(--success)', secondary: 'var(--bg-base)' },
              },
              error: {
                iconTheme: { primary: 'var(--danger)', secondary: 'var(--bg-base)' },
              },
            }}
              />
            </AnalysisProvider>
            </GamificationProvider>
          </UsageProvider>
        </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </GoogleOAuthProvider>
    </Sentry.ErrorBoundary>
  </React.StrictMode>
)
