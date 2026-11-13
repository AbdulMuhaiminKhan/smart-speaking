import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { AuthProvider, RequireAuth } from './auth/AuthContext'
import { I18nProvider, useI18n } from './i18n'
import { ErrorBoundary } from './components/ErrorBoundary'
import { Layout } from './components/Layout'
import { LoginPage, RegisterPage } from './pages/AuthPages'
import { DashboardPage } from './pages/DashboardPage'
import { LivePage } from './pages/LivePage'
import { SessionPage } from './pages/SessionPage'
import { SessionsPage } from './pages/SessionsPage'
import { SettingsPage } from './pages/SettingsPage'
import { UploadPage } from './pages/UploadPage'

function NotFound() {
  const { t } = useI18n()
  return (
    <div className="py-16 text-center">
      <p className="text-lg font-medium">{t('notfound.title')}</p>
      <Link to="/" className="mt-2 inline-block text-brand-600">
        {t('notfound.link')}
      </Link>
    </div>
  )
}

export default function App() {
  return (
    <I18nProvider>
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="login" element={<LoginPage />} />
            <Route path="register" element={<RegisterPage />} />
            <Route
              element={
                <RequireAuth>
                  <Layout />
                </RequireAuth>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="upload" element={<UploadPage />} />
              <Route path="live" element={<LivePage />} />
              <Route path="sessions" element={<SessionsPage />} />
              <Route path="sessions/:id" element={<SessionPage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
    </I18nProvider>
  )
}
