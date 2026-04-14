import React from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'

export const RequireAuth: React.FC = () => {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return <div style={{ padding: 24 }}>Loading…</div>
  }

  if (status !== 'authenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}

