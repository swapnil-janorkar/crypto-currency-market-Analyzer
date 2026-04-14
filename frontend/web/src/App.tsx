import { Navigate, Route, Routes } from 'react-router-dom'
import { ThemeProvider } from './app/Theme'
import { AppShell } from './app/AppShell'
import { RequireAuth } from './auth/RequireAuth'
import { LoginPage } from './pages/LoginPage'
import { CoinPage } from './pages/CoinPage'
import { OverviewPage } from './pages/OverviewPage'
import { PulsePage } from './pages/PulsePage'

function App() {
  return (
    <ThemeProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<RequireAuth />}>
          <Route element={<AppShell />}>
            <Route index element={<OverviewPage />} />
            <Route path="coin" element={<CoinPage />} />
            <Route path="pulse" element={<PulsePage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ThemeProvider>
  )
}

export default App
