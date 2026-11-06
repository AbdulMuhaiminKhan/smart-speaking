import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { LivePage } from './pages/LivePage'
import { SessionPage } from './pages/SessionPage'
import { SessionsPage } from './pages/SessionsPage'
import { UploadPage } from './pages/UploadPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<UploadPage />} />
          <Route path="live" element={<LivePage />} />
          <Route path="sessions" element={<SessionsPage />} />
          <Route path="sessions/:id" element={<SessionPage />} />
          <Route path="*" element={<p>Page not found.</p>} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
