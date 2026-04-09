import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { GoogleOAuthProvider } from '@react-oauth/google'
import { AuthProvider } from '@/context/AuthContext'
import { AnalysisProvider } from '@/context/AnalysisContext'
import { UsageProvider } from '@/context/UsageContext'
import { UpgradeModal } from '@/components/ui/UpgradeModal'
import App from '@/App'
import '@/index.css'
import '@/styles/design-tokens.css'

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId={googleClientId}>
      <BrowserRouter>
        <AuthProvider>
          <UsageProvider>
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
          </UsageProvider>
        </AuthProvider>
      </BrowserRouter>
    </GoogleOAuthProvider>
  </React.StrictMode>
)
