import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { AppLayout } from './components/AppLayout'
import { Login } from './pages/Login'
import { ManagerDashboard } from './pages/manager/Dashboard'
import { ManagerProducts } from './pages/manager/Products'
import { Onboarding } from './pages/Onboarding'
import { StockCount } from './pages/StockCount'
import { WasteLog } from './pages/WasteLog'

function Gate({ children }: { children: React.ReactNode }) {
  const { session, profile, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-neutral-400">
        Laden...
      </div>
    )
  }
  if (!session) return <Login />
  if (!profile) return <Onboarding />
  return <AppLayout>{children}</AppLayout>
}

function ManagerRoute({ children }: { children: React.ReactNode }) {
  const { profile } = useAuth()
  if (profile?.role !== 'manager') return <Navigate to="/" replace />
  return children
}

function AppRoutes() {
  return (
    <Gate>
      <Routes>
        <Route path="/" element={<StockCount />} />
        <Route path="/derving" element={<WasteLog />} />
        <Route
          path="/manager"
          element={
            <ManagerRoute>
              <ManagerDashboard />
            </ManagerRoute>
          }
        />
        <Route
          path="/manager/producten"
          element={
            <ManagerRoute>
              <ManagerProducts />
            </ManagerRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Gate>
  )
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </Router>
  )
}

export default App
