import type { ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth-context'
import Layout from './Layout'
import LandlordDashboard from './pages/LandlordDashboard'
import Login from './pages/Login'
import TenantHome from './pages/TenantHome'
import type { Role } from './types'

const HOME: Record<Role, string> = {
  landlord: '/landlord',
  tenant: '/tenant',
  admin: '/admin',
}

function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <p role="status">Loading...</p>
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== role) return <Navigate to="/" replace />
  return <>{children}</>
}

function Home() {
  const { user, loading } = useAuth()
  if (loading) return <p role="status">Loading...</p>
  if (!user) return <Navigate to="/login" replace />
  return <Navigate to={HOME[user.role]} replace />
}

function AdminPlaceholder() {
  return (
    <>
      <h1>Admin</h1>
      <p>The audit log viewer has not been built yet.</p>
    </>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route
          path="/landlord"
          element={
            <RequireRole role="landlord">
              <LandlordDashboard />
            </RequireRole>
          }
        />
        <Route
          path="/tenant"
          element={
            <RequireRole role="tenant">
              <TenantHome />
            </RequireRole>
          }
        />
        <Route
          path="/admin"
          element={
            <RequireRole role="admin">
              <AdminPlaceholder />
            </RequireRole>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
